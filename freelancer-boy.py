from freelancersdk.session import Session
from freelancersdk.resources.projects import search_projects, place_project_bid
from freelancersdk.resources.users import get_self
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timezone
import g4f
from g4f.Provider import Yqcloud, Blackbox, PollinationsAI, OIVSCodeSer2, WeWordle
import time

# Load environment variables
load_dotenv()

# Read credentials
token = os.getenv("PRODUCTION")
base_url = os.getenv("PRODUCTION_URL")
project_number = os.getenv("PROJECT_NUMBER")
memory_file = os.getenv("MEMORY_FILE")
session = Session(oauth_token=token, url=base_url)

        
job_ids = [1097,2334,3111,2623,2323,1384,1051,2380,1041,
           2920,2918,2916,2068,95,113,148,1094,1824]

filters = { "jobs": job_ids }

project_detail = {
    "full_description": True,
    "job_details": True,
    "user_financial_details": True
}

# Providers and models
ai_chats = [
    {"provider": Yqcloud, "model": "gpt-4", "label": "Yqcloud - GPT-4"},
    {"provider": Blackbox, "model": "gpt-4", "label": "Blackbox - GPT-4"},
    {"provider": PollinationsAI, "model": None, "label": "PollinationsAI - DEFAULT"},
    {"provider": OIVSCodeSer2, "model": "gpt-4o-mini", "label": "OIVSCodeSer2 - gpt-4o-mini"},
    {"provider": WeWordle, "model": "gpt-4", "label": "WeWordle - GPT-4"},
]

def send_ai_request(prompt):
    for ai_chat in ai_chats:
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
        time.sleep(10)  # Avoid hitting rate limits

def load_memory():
    if not os.path.exists(memory_file):
        return set()
    with open(memory_file, "r") as f:
        return set(line.strip() for line in f if line.strip())

def update_memory(project_id):
    with open(memory_file, "a") as f:
        f.write(f"{project_id}\n")

response = get_self(session=session)

user_id_flag = True
while True:
    try:
        if user_id_flag:
            response = get_self(session=session)
            for user_info in response.get("results", []):
                user_id = user_info.get("id")
                username = user_info.get("username")
                print("Starting FCOM Account Assistant...")
                print(f"Username={username}")
                print(f"UserID={user_id}")
                print(json.dump(response, indent=2))
                user_id_flag = False

        response = search_projects(
            session=session,
            query=None,
            search_filter=filters,
            project_details=project_detail,
            limit=project_number,
            offset=0,
            active_only=True
        )
        
        for project in response.get("projects", []):
            # Extract project info
            title = project.get("title", "")
            description = project.get("description", "")

            data = {
                "id": project.get("id"),
                "title": title,
                "status": project.get("status"),
                "currency_exchange_rate": project.get("currency", {}).get("exchange_rate"),
                "description": description,
                "submit_date": datetime.fromtimestamp(project.get("submitdate", 0), tz=timezone.utc).isoformat(),
                "nonpublic": project.get("nonpublic"),
                "budget_min": project.get("budget", {}).get("minimum"),
                "budget_max": project.get("budget", {}).get("maximum"),
                "urgent": project.get("urgent"),
                "bid_count": project.get("bid_stats", {}).get("bid_count"),
                "bid_avg": project.get("bid_stats", {}).get("bid_avg"),
                "min_amount": project.get("bid_stats", {}).get("min_amount"),
                "max_amount": project.get("bid_stats", {}).get("max_amount"),
                "min_period": project.get("bid_stats", {}).get("min_period"),
                "max_period": project.get("bid_stats", {}).get("max_period"),
                "time_submitted": datetime.fromtimestamp(project.get("time_submitted", 0), tz=timezone.utc).isoformat(),
                "time_updated": datetime.fromtimestamp(project.get("time_updated", 0), tz=timezone.utc).isoformat()
            }

            budget_min = data.get("budget_min")
            budget_max = data.get("budget_max")
            bid_avg = data.get("bid_avg")
            min_bid = data.get("min_amount")
            max_bid = data.get("max_amount")
            min_duration = data.get("min_period")
            max_duration = data.get("max_period")

            print(f"budget_min: {budget_min}, budget_max: {budget_max}, bid_avg: {bid_avg}, min_bid: {min_bid}, max_bid: {max_bid}, min_duration: {min_duration}, max_duration: {max_duration}")
            break
            # Load already bidded project IDs
    #         processed_ids = load_memory()
    #         if str(data["id"]) in processed_ids:
    #             print(f"duplicate id, skipping project with id {data['id']}")
    #             continue

    #         # AI prompt
    #         prompt = f"""
    #             Write a freelance job proposal message for the project below:

    #             project = [
    #                 Title: {data['title']}

    #                 Description: {data['description']}
    #             ]

    #             The message should:
    #             - Be between 100 and 1000 characters
    #             - Sound friendly and human
    #             - Start with "Hello," then a new line, Don't use Dear [Client] or Don't use Hello [Client]
    #             - use the word "I" only when needed so it sound like it is typed by a human freelancer applying for a job
    #             - Don't list anything, write everything in paragraph form
    #             - Include a brief high-level summary of how I would approach the project
    #             - Mention possible solutions where relevant (but avoid technical detail)
    #             - Don't use exclamation marks, emojis or Best regards [Your Name]
    #             - use Thanks at the end
    #             """
            
    #         proposal = send_ai_request(prompt)
    #         if proposal:
    #             print(f"Project ID: {data['id']}")
    #             print(f"Proposal:\n{proposal}\n")
    #             response = place_project_bid(session=session, project_id=data["id"], description=proposal, amount=data["bid_avg"], bid_period=7, )
    #             update_memory(data["id"])
    #         else:
    #             print(f"Failed to generate proposal for Project ID: {data['id']}")
    #         time.sleep(5)    
        
    except Exception as e:
        print(f"Error processing projects: {e}")
        break

