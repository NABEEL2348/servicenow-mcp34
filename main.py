import json
import os
import re
import requests
from pydantic import BaseModel, Field
import streamlit as st
from dotenv import load_dotenv
import logging
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AddNumbersParams(BaseModel):
    """Parameters for adding two numbers."""
    num1: float = Field(..., description="First number")
    num2: float = Field(..., description="Second number")

class AddNumbersResponse(BaseModel):
    """Response from addition operation."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    result: Optional[float] = Field(None, description="Result of the addition")

class ServiceNowClient:
    """Client for ServiceNow API integration."""
    
    def __init__(self):
        """Initialize the ServiceNow client with credentials."""
        self.instance_url = os.getenv("SERVICENOW_INSTANCE_URL", "").rstrip('/')
        self.username = os.getenv("SERVICENOW_USERNAME")
        self.password = os.getenv("SERVICENOW_PASSWORD")
        
        if not all([self.instance_url, self.username, self.password]):
            logger.warning("ServiceNow credentials not fully configured")
    
    def get_headers(self):
        """Get headers for ServiceNow API requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def add_numbers(self, num1: float, num2: float) -> AddNumbersResponse:
        """Call ServiceNow API to add two numbers."""
        if not all([self.instance_url, self.username, self.password]):
            return AddNumbersResponse(
                success=False,
                message="ServiceNow credentials not configured",
                result=None
            )

        # Construct the API URL
        api_url = f"{self.instance_url}/api/1756572/addition_of_two_numbers/add"
        
        # Prepare the payload
        payload = {
            "num1": num1,
            "num2": num2
        }
        
        try:
            # Make the API request
            logger.info(f"Making request to: {api_url}")
            logger.info(f"Payload: {json.dumps(payload)}")
            
            response = requests.post(
                api_url,
                json=payload,
                auth=(self.username, self.password),
                headers=self.get_headers(),
                timeout=30
            )
            
            # Log response details
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")
            logger.info(f"Raw Response: {response.text}")
            
            try:
                response_data = response.json()
                logger.info(f"Parsed Response Data: {json.dumps(response_data, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                return AddNumbersResponse(
                    success=False,
                    message="Invalid JSON response from server",
                    result=None
                )
            
            if response.status_code == 200:
                # Handle nested result structure
                if "result" in response_data:
                    result_dict = response_data["result"]
                    if isinstance(result_dict, dict) and "result" in result_dict:
                        result_value = result_dict["result"]
                        logger.info(f"Extracted result value: {result_value}, Type: {type(result_value)}")
                        # Convert to float if it's a number
                        if isinstance(result_value, (int, float)):
                            return AddNumbersResponse(
                                success=True,
                                message="Addition successful",
                                result=float(result_value)
                            )
                        else:
                            logger.error(f"Result is not a number: {result_value}")
                    else:
                        logger.error(f"Invalid nested result structure: {result_dict}")
                else:
                    logger.error(f"Missing 'result' key in response: {response_data}")
                
                return AddNumbersResponse(
                    success=False,
                    message="Invalid response format from API",
                    result=None
                )
            else:
                # Handle error response
                error_msg = response_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"API Error: {error_msg}")
                return AddNumbersResponse(
                    success=False,
                    message=f"API Error: {error_msg}",
                    result=None
                )
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return AddNumbersResponse(
                success=False,
                message=f"Request failed: {str(e)}",
                result=None
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return AddNumbersResponse(
                success=False,
                message=f"Unexpected error: {str(e)}",
                result=None
            )

def process_query(query: str, client: ServiceNowClient) -> str:
    """Process user query and extract numbers for addition."""
    try:
        # Clean the query string
        query = query.strip().lower()
        
        # Extract numbers using a more robust regex pattern
        nums = re.findall(r"[-+]?\d*\.?\d+", query)
        
        # Convert to float and handle any conversion errors
        try:
            nums = [float(num) for num in nums]
        except ValueError:
            return "Error: Found invalid number format in the query"
        
        # Check if we have exactly two numbers
        if len(nums) == 0:
            return "Error: No numbers found in the query. Please provide two numbers."
        elif len(nums) == 1:
            return "Error: Only one number found. Please provide exactly two numbers."
        elif len(nums) > 2:
            return "Error: More than two numbers found. Please provide exactly two numbers."

        # Call ServiceNow API
        result = client.add_numbers(nums[0], nums[1])
        
        if result.success:
            return f"Result: {result.result}"
        else:
            return f"Error: {result.message}"
            
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return f"Error: An unexpected error occurred. Please try again with a valid query."

def main():
    """Main Streamlit application."""
    st.title("ServiceNow Number Addition Client")
    
    # Initialize client
    if "client" not in st.session_state:
        st.session_state.client = ServiceNowClient()
    
    client = st.session_state.client
    
    # ServiceNow credentials input in sidebar
    with st.sidebar:
        st.header("ServiceNow Configuration")
        
        instance_url = st.text_input(
            "Instance URL",
            value=client.instance_url,
            placeholder="https://dev341352.service-now.com"
        )
        username = st.text_input("Username", value=client.username)
        password = st.text_input("Password", value=client.password, type="password")
        
        # Update client credentials if changed
        if instance_url != client.instance_url:
            client.instance_url = instance_url
        if username != client.username:
            client.username = username
        if password != client.password:
            client.password = password
        
        # Debug information
        if st.checkbox("Show Debug Info"):
            st.write("Current Configuration:")
            st.write(f"Instance URL: {client.instance_url}")
            st.write(f"Username: {client.username}")
            st.write("Password: [HIDDEN]")
    
    # Main content area
    user_query = st.text_input(
        "Enter your query",
        placeholder="What is the sum of 8 and 12?"
    )
    
    if st.button("Process Query"):
        if user_query:
            with st.spinner("Processing query..."):
                result = process_query(user_query, client)
                st.subheader("Result")
                st.write(result)
        else:
            st.warning("Please enter a query")
    
    # Sample queries
    st.subheader("Sample Queries")
    st.markdown("""
    Try queries like:
    - What is the sum of 5 and 7?
    - Add 10 and 20
    - Calculate 15 plus 25
    """)

if __name__ == "__main__":
    main()