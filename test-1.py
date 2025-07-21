import os
import requests
from dotenv import load_dotenv
import json

# Load token from .env file
load_dotenv()
token = os.getenv("PRODUCTION")

params = {
    "bids": True
}
# API endpoint
url = "https://www.freelancer.com/api/users/0.1/self/"

# Headers
headers = {
    "freelancer-oauth-v1": token
}

# Make request
response = requests.get(url, headers=headers, params=params)
data = response.json()

print(json.dumps(data, indent=2))

