from freelancersdk.session import Session
from freelancersdk.resources.users import get_self
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Read the OAuth token from environment
token = os.getenv("PRODUCTION")
url = os.getenv("PRODUCTION_URL")

# Create session
session = Session(
    oauth_token=token,
    url="https://www.freelancer-sandbox.com"
)

# Access the /me endpoint
response = get_self(session)

# Get just the user account object
user_account = response
print(user_account)
