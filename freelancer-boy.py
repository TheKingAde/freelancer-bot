from freelancersdk.session import Session
from freelancersdk.resources.users import users

# Use the correct base URL and token
session = Session(
    oauth_token="TXQ01QFD1eDKrvj8qziddtCiCpGLIj",
    url="https://www.freelancer-sandbox.com"  # or https://www.freelancer.com
)

# Access the /me endpoint
user = users(session)
response = user.get_self()

# Get just the user account object
user_account = response.json().get("result", {})
print(user_account)
