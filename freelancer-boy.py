from freelancersdk.session import Session
from freelancersdk.resources.projects import search_projects, place_project_bid
from freelancersdk.resources.users import get_self
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timezone, timedelta
import g4f
from g4f.Provider import Yqcloud, Blackbox, PollinationsAI, OIVSCodeSer2, WeWordle
import time
import sqlite3
import sys
from freelancersdk.resources.projects.exceptions import \
    ProjectsNotFoundException
from freelancersdk.resources.projects.helpers import (
    create_search_projects_filter,
)
from freelancersdk.exceptions import BidNotPlacedException

# Load environment variables
load_dotenv()

# Read credentials
token = os.getenv("PRODUCTION")
base_url = os.getenv("PRODUCTION_URL")
project_number = os.getenv("PROJECT_NUMBER")
memory_file = os.getenv("MEMORY_FILE")
look_back_hours = int(os.getenv("LOOK_BACK_HOURS", 1))
min_bid_amount_usd = int(os.getenv("MIN_BID_AMOUNT_USD", 15))
session = Session(oauth_token=token, url=base_url)


sleep_time = 3
search_filter = create_search_projects_filter(
        jobs=[1384,2623,148,2323,3111,1824]
    )

project_detail = {
    "full_description": True,
    "job_details": True
}

# Providers and models
ai_chats = [
    {"provider": Yqcloud, "model": "gpt-4", "label": "Yqcloud - GPT-4"},
    {"provider": Blackbox, "model": "gpt-4", "label": "Blackbox - GPT-4"},
    {"provider": PollinationsAI, "model": None, "label": "PollinationsAI - DEFAULT"},
    {"provider": OIVSCodeSer2, "model": "gpt-4o-mini", "label": "OIVSCodeSer2 - gpt-4o-mini"},
    {"provider": WeWordle, "model": "gpt-4", "label": "WeWordle - GPT-4"},
]

# Initialize database
conn = sqlite3.connect("bidded_projects.db")
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT UNIQUE
    )
""")
conn.commit()

def project_id_exists(project_id):
    c.execute("SELECT 1 FROM keys WHERE project_id = ?", (project_id,))
    return c.fetchone() is not None

def store_project_keys(project_id):
    c.execute("INSERT INTO keys (project_id) VALUES (?)", 
            (project_id,))
    conn.commit()

def send_ai_request(prompt):
    for ai_chat in ai_chats:
        time.sleep(sleep_time)
        try:
            # print(f"--- Trying {ai_chat['label']} ---")
            kwargs = {
                "provider": ai_chat["provider"],
                "messages": [{"role": "user", "content": prompt}]
            }
            if ai_chat["model"]:
                kwargs["model"] = ai_chat["model"]

            response = g4f.ChatCompletion.create(**kwargs)

            if response and isinstance(response, str) and response.strip():
                return response # Stop once a valid response is received
        except Exception as e:
            return None

response = get_self(session=session)
user_id = response.get("id")
username = response.get("username")
print("Starting FCOM Account Assistant...")
print(f"Username={username}")
print(f"UserID={user_id}")
print("running...")
while True:
    try:
        response = search_projects(
            session=session,
            query=None,
            search_filter=search_filter,
            project_details=project_detail,
            limit=project_number,
            offset=0,
            active_only=True
        )
        for project in response.get("projects", []):
            data = {
                "id": project.get("id"),
                "title": project.get("title"),
                "status": project.get("status"),
                "currency_exchange_rate": project.get("currency", {}).get("exchange_rate"),
                "description": project.get("description"),
                "submit_date": datetime.fromtimestamp(project.get("submitdate", 0), tz=timezone.utc).isoformat(),
                "nonpublic": project.get("nonpublic"),
                "budget_min": project.get("budget", {}).get("minimum"),
                "budget_max": project.get("budget", {}).get("maximum"),
                "urgent": project.get("urgent"),
                "bid_count": project.get("bid_stats", {}).get("bid_count"),
                "bid_avg": project.get("bid_stats", {}).get("bid_avg"),
                "time_submitted": datetime.fromtimestamp(project.get("time_submitted", 0), tz=timezone.utc).isoformat(),
                "time_updated": datetime.fromtimestamp(project.get("time_updated", 0), tz=timezone.utc).isoformat()
            }
            if project_id_exists(str(data["id"])):
                print(f"duplicate id, skipping project with id {data['id']}")
                continue

            time_submitted = data["time_submitted"]
            budget_min = data["budget_min"]
            budget_max = data["budget_max"]
            bid_avg = data["bid_avg"]
            bid_status = data["status"]
            currency_exchange_rate = data["currency_exchange_rate"]
            
            time_submitted_dt = datetime.fromisoformat(data["time_submitted"])
            now = datetime.now(timezone.utc)
            if now - time_submitted_dt >= timedelta(hours=look_back_hours):
                print(f"Project {data['id']} is older than {look_back_hours} hours, skipping...")
                store_project_keys(str(data['id']))
                time.sleep(sleep_time)
                continue
            if bid_status != "active":
                print(f"Project {data['id']} is not active, skipping...")
                store_project_keys(str(data['id']))
                time.sleep(sleep_time)
                continue

            # AI prompt
            prompt = f"""
                Write a freelance job proposal message for the project below:

                project = [
                    Title: {data['title']}

                    Description: {data['description']}
                ]

                The message should:
                - Be between 100 and 1000 characters
                - Sound friendly and human
                - Start with "Hello," then a new line, Don't use Dear [Client] or Don't use Hello [Client]
                - use the word "I" only when needed so it sound like it is typed by a human freelancer applying for a job
                - Don't list anything, write everything in paragraph form
                - Include a brief high-level summary of how I would approach the project
                - Mention possible solutions where relevant (but avoid technical detail)
                - Don't use exclamation marks, emojis or Best regards [Your Name]
                - use Thanks at the end
                """
            
            proposal = send_ai_request(prompt)
            if proposal:
                # budget_min_usd = budget_min * currency_exchange_rate
                # budget_max_usd = budget_max * currency_exchange_rate
                bid_avg_usd = bid_avg * currency_exchange_rate
                amount_usd = round(bid_avg_usd * 0.9)
                if amount_usd < min_bid_amount_usd:
                    print(f"Bid amount {amount_usd} is less than minimum allowed {min_bid_amount_usd}, skipping project {data['id']}")
                    amount = min_bid_amount_usd / currency_exchange_rate
                else:
                    amount = amount_usd / currency_exchange_rate
                
                bid_data = {
                    'project_id': int(data["id"]),
                    'bidder_id': user_id,
                    'amount': amount,
                    'period': 3,
                    'milestone_percentage': 100,
                    'description': proposal,
                }
                try:
                    response = place_project_bid(session=session, **bid_data)
                    store_project_keys(str(data['id']))
                except BidNotPlacedException as e:
                    # print(('Error message: %s' % e.message))
                    print(('Bid not placed. Error code: %s' % e.error_code))
                    continue
            else:
                print(f"Failed to generate proposal for Project ID: {data['id']}")
            time.sleep(sleep_time)

    except BidNotPlacedException as e:
        print(f"Bid not placed: {e}")
    except Exception as e:
        print(f"Error processing projects: {e}")
        break

