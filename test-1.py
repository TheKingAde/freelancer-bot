import requests

# Replace with your actual bot token and chat ID
telegram_bot_token = "8110984889:AAE3pAVnIGAnPbl0MosP1DGZfVceD4c0wWc"
telegram_chatid = "6126141848"

def send_telegram_message(project_title, seo_url):
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    msg_seo_url = f"https://www.freelancer.com/projects/{seo_url}"

    message = (
        f"🚨 <b>Project Requires NDA</b>\n\n"
        f"Project: <b>{project_title}</b>\n"
        f"<a href='{msg_seo_url}'>View Project on Freelancer</a>\n\n"
        f"An NDA must be signed to access this project."
    )

    payload = {
        "chat_id": telegram_chatid,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    response = requests.post(url, data=payload)

    if response.status_code == 200:
        print("✅ Message sent successfully.")
    else:
        print(f"❌ Failed to send message. Status: {response.status_code}, Error: {response.text}")

# 🔧 Example test
if __name__ == "__main__":
    test_project_title = "Develop Ninjatrader 8 Trading Strategy Based On Indicators Without Source Code"
    test_seo_url = "Ninjatrader/Develop-Ninjatrader-Trading-Strategy"  # Example format
    send_telegram_message(test_project_title, test_seo_url)
