# retrieve posts from instagram (http call)
# process them to get image and description
# prepare telegram message
# send to bot
# delete local data when done
import os

import asyncio
from telegram import Bot

from instaloader import Instaloader
from dotenv import load_dotenv

from utils import fetch_profiles_posts, load_sent_shortcodes, login, save_sent_shortcodes, send_posts_to_telegram

# load the environment variables
load_dotenv()

# load instaloader main class
loader = Instaloader()

# instantiate variables
username = os.environ.get("INSTAGRAM_USERNAME")
password = os.environ.get("INSTAGRAM_PASSWORD")
profiles = os.environ.get("PROFILES_LIST")
bot_token = os.environ.get("BOT_TOKEN")
telegram_id = os.environ.get("TELEGRAM_ID")
profiles_array = None


if not profiles or not username or not password:
    print("One of the environment variables is not properly set. Please check the env file.")
    exit(1)

profiles_array = [p.strip() for p in profiles.split(",") if p.strip()]

if not profiles_array:
    print("No profile to fetch, please check your env")
    exit(1)

logged_user = login(username=username, password=password, instagram_loader=loader)

if not logged_user:
    print("Login failed, aborting operation")
    exit(1)

print("Logged in, ready to fetch posts.")

sent_shortcodes = load_sent_shortcodes()

today_posts = fetch_profiles_posts(profiles_array=profiles_array, loader_context=loader.context)
new_posts = [p for p in today_posts if p.shortcode not in sent_shortcodes]
print(f"Found {len(today_posts)} posts today, {len(new_posts)} not yet sent.")

asyncio.run(send_posts_to_telegram(new_posts, bot_token, telegram_id))

sent_shortcodes.update(p.shortcode for p in new_posts)
save_sent_shortcodes(sent_shortcodes)
