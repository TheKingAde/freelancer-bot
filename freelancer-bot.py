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
import re
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
        jobs=[1384,2996,344,2623,148,2323,3111,1824]
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

failed_ai_chats = set()
ai_chat_to_use = 0
def send_ai_request(prompt):
    global ai_chat_to_use, failed_ai_chats

    total_chats = len(ai_chats)
    attempts = 0

    while attempts < total_chats:
        current_chat = ai_chats[ai_chat_to_use]
        if ai_chat_to_use in failed_ai_chats:
            ai_chat_to_use = (ai_chat_to_use + 1) % total_chats
            attempts += 1
            continue

        time.sleep(sleep_time)
        try:
            kwargs = {
                "provider": current_chat["provider"],
                "messages": [{"role": "user", "content": prompt}]
            }
            if current_chat["model"]:
                kwargs["model"] = current_chat["model"]

            response = g4f.ChatCompletion.create(**kwargs)

            if (
                response
                and isinstance(response, str)
                and response.strip()
                and re.match(r"(?i)^hello(,|\s|\n|$)", response.strip())
            ):
                return response

            # If response is invalid, consider it a failure
            failed_ai_chats.add(ai_chat_to_use)
            ai_chat_to_use = (ai_chat_to_use + 1) % total_chats
            attempts += 1

        except Exception:
            failed_ai_chats.add(ai_chat_to_use)
            ai_chat_to_use = (ai_chat_to_use + 1) % total_chats
            attempts += 1

    # All failed, reset and start over next time
    failed_ai_chats.clear()
    return False

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
        msg_seo_url = f"https://www.freelancer.com/projects/{seo_url}/details"
        message = (
            f"✅ <b>Proposal sent</b>\n\n"
            f"Project: <b>{project_title}</b>\n"
            f"Proposal: {proposal}\n\n"
            f"<a href='{msg_seo_url}'>View Project on Freelancer</a>\n"
        )
    if msg_type == "gen_proposal":
        message = (
            f"🚨 <b>Proposal generation Failed</b>\n\n"
            f"Action taken: <b> sleeping for {exhaustion_sleep_time}</b>\n"
        )
    if msg_type == "error":
        if seo_url != "":
            msg_seo_url = f"https://www.freelancer.com/projects/{seo_url}/details"
        else:
            msg_seo_url = "https://www.freelancer.com"
        error_message_title = "An error occurred" if seo_url == "" else f"Failed to send proposal: <b>{project_title.get('error_message')}</b>"
        error_message = "Error message" if seo_url == "" else "Proposal"
        if isinstance(project_title, dict):
            title_line = f"{error_message}: <b>{project_title.get('title')} (${project_title.get('amount')})</b>\n"
        else:
            title_line = f"{error_message}: <b>{project_title}</b>\n"
        message = (
            f"🚨 <b>{error_message_title}</b>\n\n"
            f"{title_line}"
            f"<a href='{msg_seo_url}'>View Project on Freelancer</a>\n"
            f"Proposal: {proposal}"
        )
    payload = {
        "chat_id": telegram_chatid,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
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
                try:
                    interruptible_sleep(
                        hours=0.25,
                        check_interval=1,
                        shut_down_flag=lambda: shutdown_flag
                    )
                except KeyboardInterrupt:
                    break
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
                if str(e) == "You have made too many of these requests":
                    print("You have made too many of these requests")
                    try:
                        interruptible_sleep(
                            hours=0.4,
                            check_interval=1,
                            shut_down_flag=lambda: shutdown_flag
                        )
                    except KeyboardInterrupt:
                        break
                else:
                    print('Server response: {}'.format(str(e)))
                    send_telegram_message(str(e), "error", proposal="", seo_url="")
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
                if budget_max is None or budget_min is None:
                    print(f"⚠️ Project {data['id']} has missing budget info, skipping...")
                    store_project_keys(str(data['id']))
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
                if proposal != False:
                    amount = round(float(budget_max) * float(bid_avg_percent))
                    if amount < float(budget_min):
                        amount = float(budget_min)
                    bid_data = {
                        'project_id': int(data["id"]),
                        'bidder_id': user_id,
                        'amount': amount,
                        'period': 3,
                        'milestone_percentage': 100,
                        'description': proposal,
                    }
                    try:
                        try:
                            interruptible_sleep(
                                hours=0.03,
                                check_interval=1,
                                shut_down_flag=lambda: shutdown_flag
                            )
                        except KeyboardInterrupt:
                            break
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
                            proposal_data = {
                                'title': data["title"],
                                'amount': amount,
                            }
                            send_telegram_message(proposal_data, "nda", proposal, data["seo_url"])
                            store_project_keys(str(data['id']))
                            continue
                        else:
                            print('Server response: {}'.format(str(e)))
                            proposal_data = {
                                'title': data["title"],
                                'amount': amount,
                                'error_message': str(e)
                            }
                            send_telegram_message(proposal_data, "error", proposal, data["seo_url"] or "")
                            store_project_keys(str(data['id']))
                            continue
                else:
                    print(f"Failed to generate proposal for Project ID: {data['id']}, sleeping for {exhaustion_sleep_time} hour(s)")
                    proposal="N/A"
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

