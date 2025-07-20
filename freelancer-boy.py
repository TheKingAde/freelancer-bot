from freelancersdk.session import Session
from freelancersdk.resources.projects import search_projects, get_project_by_id
from dotenv import load_dotenv
import os
import json  # for readable JSON output

# Load environment variables from .env
load_dotenv()

# Read the OAuth token from environment
token = os.getenv("PRODUCTION")
base_url = os.getenv("PRODUCTION_URL")

# Create session
session = Session(
    oauth_token=token,
    url=base_url
)

# List of job IDs to filter
job_ids = [
    951, 2013, 2334, 2576, 1599, 3111, 2623, 2323, 1384, 1127, 1019, 1623,
    1314, 759, 44, 1275, 1274, 1051, 1278, 1277, 335, 1042, 77, 2435, 2301,
    16, 602, 2434, 2380, 2164, 2050, 1240, 1087, 1041, 773, 2405, 2389, 1701,
    1712, 2403, 1606, 913, 2936, 2920, 2918, 2917, 2916, 2068, 584, 1977, 1323,
    208, 2382, 1239, 687, 1040, 1827, 1112, 564, 319, 219, 1492, 1472, 1634,
    39, 1077, 1075, 709, 334, 673, 36, 1383, 9, 13, 68, 95, 113, 148, 305, 323,
    613, 1031, 1092, 1093, 1094, 1393, 1824, 2165, 3112
]

# Define filters using the job IDs
filters = {
    "jobs": job_ids
}

# Define project details to fetch
project_detail = {
    "full_description": True,
    # "job_details": True
}

# Search projects with filters
response = search_projects(
    session=session,
    query=None,
    search_filter=filters,
    project_details=project_detail,
    limit=3,
    offset=0,
    active_only=True
)

# Pretty-print the JSON response
print(json.dumps(response, indent=2))
# for project in response.get("projects", []):
#     project_id = project["id"]
#     full_project = get_project_by_id(session=session, project_id=project_id, project_details=project_detail)
#     print(json.dumps(full_project, indent=3))

# id
# title
# status
# currency id
# description
# submit_date
# nonpublic
# budget maximum and minimum
# urgent
# bid_count
# bid_avg
# min_amount
# max_amount
# min_period
# max_period
# time_submitted
# time_updated

