from freelancersdk.resources.projects.exceptions import \
    ProjectsNotFoundException, BidNotPlacedException
from freelancersdk.resources.projects.helpers import (
    create_search_projects_filter,
)
from freelancersdk.resources.users.exceptions import \
    SelfNotRetrievedException
from freelancersdk.session import Session
from freelancersdk.resources.projects import search_projects, place_project_bid
from freelancersdk.resources.users import get_self
from g4f.Provider import Yqcloud, Blackbox, PollinationsAI, OIVSCodeSer2, WeWordle
import datetime
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import json
import g4f
import time
import sqlite3
import signal
import requests

# Load environment variables
load_dotenv()
# Read credentials
token = os.getenv("PRODUCTION")
base_url = os.getenv("PRODUCTION_URL")
project_number = os.getenv("PROJECT_NUMBER")
memory_file = os.getenv("MEMORY_FILE")
look_back_hours = int(os.getenv("LOOK_BACK_HOURS", 1))
exhaustion_sleep_time = int(os.getenv("BID_EXHAUSTED_SLEEP_TIME", 1))
telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chatid = os.getenv("TELEGRAM_CHATID")
bid_avg_percent = os.getenv("BID_AVERAGE_DISCOUNT_PERCENT", 1)
session = Session(oauth_token=token, url=base_url)

id_flag=True
shutdown_flag=False
sleep_time = 3
search_filter = create_search_projects_filter(
        jobs=[344,1384,2623,148,2323,3111,1824]
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

def send_telegram_message(project_title, msg_type, proposal, seo_url):
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    if msg_type == "nda":
        msg_seo_url = f"https://www.freelancer.com/projects/{seo_url}/details"
        message = (
            f"🚨 <b>Project Requires NDA</b>\n\n"
            f"Project: <b>{project_title}</b>\n"
            f"<a href='{msg_seo_url}'>View Project on Freelancer</a>\n"
            f"An NDA must be signed to access this project.\n\n"
            f"Proposal: {proposal}"
        )
    if msg_type == "proposal":
        message = (
            f"✅ <b>Proposal sent</b>\n\n"
            f"Project: <b>{project_title}</b>\n"
            f"Proposal: {proposal}"
        )
    if msg_type == "gen_proposal":
        message = (
            f"🚨 <b>Proposal generation Failed</b>\n\n"
            f"Action taken: <b> sleeping for {exhaustion_sleep_time}</b>\n"
            f"<a href='{msg_seo_url}'>View Project on Freelancer</a>\n"
        )

    payload = {
        "chat_id": telegram_chatid,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True  # Optional: avoids showing link preview
    }

    response = requests.post(url, data=payload)

    if response.status_code != 200:
        print(f"❌ Failed to send message. Status: {response.status_code}, Error: {response.text}")

def interruptible_sleep(hours, check_interval=60, shut_down_flag=lambda: False):
    """
    Sleeps for `hours` hours, but checks `shut_down_flag()` every `check_interval` seconds.
    If `shut_down_flag()` returns True, exits early.
    """
    total_seconds = int(hours * 3600)
    slept = 0
    while slept < total_seconds:
        if shutdown_flag:
            raise KeyboardInterrupt("Shutdown requested")
        time.sleep(min(check_interval, total_seconds - slept))
        slept += check_interval

def handle_exit(signum, frame):
    global shutdown_flag
    print("\n🛑 Received exit signal. Shutting down...")
    shutdown_flag = True
signal.signal(signal.SIGINT, handle_exit)   # Ctrl+C
signal.signal(signal.SIGTERM, handle_exit)  # kill command
try:
    while not shutdown_flag:
        try:
            if id_flag:
                try:
                    response = get_self(session=session)
                    user_id = response.get("id")
                    username = response.get("username")
                    print("Starting FCOM Account Assistant...")
                    print(f"Username={username}")
                    print(f"UserID={user_id}")
                    print("running...")
                    id_flag=False
                except SelfNotRetrievedException as e:
                    print('Server response: {}'.format(str(e)))
                    time.sleep(sleep_time)
                    continue
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
            except ProjectsNotFoundException as e:
                print('Server response: {}'.format(str(e)))
                time.sleep(sleep_time)
                continue

            for project in response.get("projects", []):
                data = {
                    "id": project.get("id"),
                    "title": project.get("title"),
                    "status": project.get("status"),
                    "seo_url": project.get("seo_url"),
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
                    amount_usd = round(bid_avg_usd * bid_avg_percent)
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
                        send_telegram_message(str(data["title"]), "proposal", proposal, data["seo_url"])
                    except BidNotPlacedException as e:
                        if str(e) == "You have used all of your bids.":
                            try:
                                interruptible_sleep(
                                    hours=exhaustion_sleep_time,
                                    check_interval=5,
                                    shut_down_flag=lambda: shutdown_flag
                                )
                            except KeyboardInterrupt:
                                break
                            continue
                        if str(e) == "You have already bid on that project.":
                            store_project_keys(str(data['id']))
                            continue
                        if str(e) == "You must sign the NDA before you can bid on this project.":
                            send_telegram_message(str(data["title"]), "nda", proposal, data["seo_url"])
                            store_project_keys(str(data['id']))
                            continue
                else:
                    print(f"Failed to generate proposal for Project ID: {data['id']}, sleeping for {exhaustion_sleep_time} hour(s)")
                    send_telegram_message(str(data["title"]), "gen_proposal", proposal, data["seo_url"])
                    try:
                        interruptible_sleep(
                            hours=exhaustion_sleep_time,
                            check_interval=5,
                            shut_down_flag=lambda: shutdown_flag
                        )
                    except KeyboardInterrupt:
                        break
                    continue
            time.sleep(sleep_time)
        except Exception as e:
            print(f"Error processing projects: {e}")
            continue
except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
finally:
        print("👋 shutdown complete.")
