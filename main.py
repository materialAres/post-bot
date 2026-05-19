import os

import asyncio

from instaloader import Instaloader
from dotenv import load_dotenv

from utils import fetch_profiles_posts, get_profile_ids, get_profile_stories, load_sent_shortcodes, load_sent_story_shortcodes, login, save_sent_shortcodes, save_sent_story_shortcodes, send_posts_to_telegram, send_stories_to_telegram

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

# get profiles to fetch
profiles_array = [p.strip() for p in profiles.split(",") if p.strip()]

if not profiles_array:
    print("No profile to fetch, please check your env")
    exit(1)

# get the logged user if the login succeeds
logged_user = login(username=username, password=password, instagram_loader=loader, bot_token=bot_token, telegram_id=telegram_id)

if not logged_user:
    print("Login failed, aborting operation")
    exit(1)

print("Logged in, ready to fetch posts.")

# create shortcodes to avoid send duplicated posts/stories if the job runs
# more than once a day
sent_shortcodes = load_sent_shortcodes()
sent_story_shortcodes = load_sent_story_shortcodes()

# fetch posts and filter out duplicates
today_posts = fetch_profiles_posts(profiles_array=profiles_array, loader_context=loader.context)
profiles_ids = get_profile_ids(profiles_array=profiles_array, loader_context=loader.context)
profiles_stories = get_profile_stories(profile_ids=profiles_ids, loader=loader)
print(f"Fetched {len(profiles_stories)} stories for profiles {profiles_ids}")
new_posts = [p for p in today_posts if p.shortcode not in sent_shortcodes]
new_stories = [s for s in profiles_stories if s.shortcode not in sent_story_shortcodes]
print(f"Found {len(today_posts)} posts today, {len(new_posts)} not yet sent.")
print(f"Found {len(profiles_stories)} stories today, {len(new_stories)} not yet sent.")

# send posts to telegram bot
asyncio.run(send_posts_to_telegram(new_posts, bot_token, telegram_id))
asyncio.run(send_stories_to_telegram(new_stories, bot_token, telegram_id))

# save/update shortcodes
sent_shortcodes.update(p.shortcode for p in new_posts)
save_sent_shortcodes(sent_shortcodes)
sent_story_shortcodes.update(s.shortcode for s in new_stories)
save_sent_story_shortcodes(sent_story_shortcodes)
