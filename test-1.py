import os
import requests
from dotenv import load_dotenv

# Load token from .env file
load_dotenv()
token = os.getenv("PRODUCTION")

# API endpoint
url = "https://www.freelancer.com/api/projects/0.1/currencies/"

# Headers
headers = {
    "freelancer-oauth-v1": token
}

# Make request
response = requests.get(url, headers=headers)
data = response.json()

# Check for success
currencies = data.get("result", {}).get("currencies", [])

# Prepare output
lines = []
for currency in currencies:
    line = f"{currency['id']}={currency['code']}"
    print(line)
    lines.append(line)

# Save to txt file
with open("currencies.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("\n✅ Saved to currencies.txt")
