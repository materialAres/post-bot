import json
from datetime import datetime, timezone
from itertools import islice

from instaloader import ConnectionException, Profile, ProfileNotExistsException, TwoFactorAuthRequiredException
from telegram import Bot
import telegram

_TELEGRAM_CAPTION_LIMIT = 1024

def load_sent_shortcodes(filename="sent_posts.json"):
    try:
        with open(filename, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_sent_shortcodes(shortcodes, filename="sent_posts.json"):
    with open(filename, "w") as f:
        json.dump(list(shortcodes), f)


def load_sent_story_shortcodes(filename="sent_stories.json"):
    try:
        with open(filename, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_sent_story_shortcodes(shortcodes, filename="sent_stories.json"):
    with open(filename, "w") as f:
        json.dump(list(shortcodes), f)


def login(username, password, instagram_loader):
    try:
        instagram_loader.load_session_from_file(username, filename="session.txt")
        print("Session loaded successfully.")
        return instagram_loader.test_login()
    except FileNotFoundError:
        print("No session file found. Will log in with credentials.")

    if not instagram_loader.test_login():
        print("Logging in...")
        try:
            instagram_loader.login(username, password)
        except TwoFactorAuthRequiredException:
            instagram_loader.two_factor_login(input("Enter 2FA code: "))

        if instagram_loader.test_login():
            instagram_loader.save_session_to_file("session.txt")
            print("Logged in successfully.")
            return instagram_loader.test_login()

    if not instagram_loader.test_login():
        print("Not logged in. Please check your credentials.")
        return None
    
def fetch_profiles_posts(profiles_array, loader_context):
    all_posts = []
    for profile in profiles_array:
        try:
            profile = Profile.from_username(loader_context, profile)
            print(f"Found profile {profile.username} with {profile.mediacount} posts")
            posts = profile.get_posts()
        except (ProfileNotExistsException, ConnectionException) as e:
            print(f"Profile {profile} does not exist or there was a connection error: {e}")
            continue

        first_10_posts = list(islice(posts, 10))
        today_post_list = [post for post in first_10_posts if post.date_utc.date() == datetime.now(timezone.utc).date()]
        all_posts.extend(today_post_list)
    
    return all_posts

def get_profile_ids(profiles_array, loader_context):
    profile_ids = []
    for profile in profiles_array:
        try:
            profile = Profile.from_username(loader_context, profile)
            profile_ids.append(profile.userid)
        except (ProfileNotExistsException, ConnectionException) as e:
            print(f"Profile {profile} does not exist or there was a connection error: {e}")
            continue
    return profile_ids

def get_profile_stories(profile_ids, loader):
    stories = []
    try:
        profile_stories = loader.get_stories(userids=profile_ids)

        for story in profile_stories:
            for item in story.get_items():
                stories.append(item)
    except ConnectionException as e:
        print(f"Connection error while fetching stories for profile IDs {profile_ids}: {e}")
    return stories

def _truncate_caption(caption):
    if caption and len(caption) > _TELEGRAM_CAPTION_LIMIT:
        return caption[:_TELEGRAM_CAPTION_LIMIT - 3] + "..."
    return caption

def get_post_data(post):
    return {
        "image_url": post.url,
        "description": _truncate_caption(post.caption),
        "date": post.date_utc
    }

def get_story_data(story):
    return {
        "image_url": story.url,
        "description": _truncate_caption(story.caption),
        "date": story.date_utc
    }

async def send_posts_to_telegram(today_posts, bot_token, telegram_id):
    post_data = [get_post_data(post) for post in today_posts]
    if not bot_token or not telegram_id:
        print("Send Posts: Telegram bot token or chat ID is not set. Please check the env file.")
        return
    if not post_data:
        print(f"Send Posts: No posts to send for post data: {post_data}")
        return
    bot = Bot(token=bot_token)
    for data in post_data:
        try:
            await bot.send_photo(chat_id=telegram_id, photo=data["image_url"], caption=data["description"])
        except telegram.error.TelegramError as e:
            print(f"Failed to send post to Telegram: {e}")

async def send_stories_to_telegram(stories, bot_token, telegram_id):
    story_data = [get_story_data(story) for story in stories]
    if not bot_token or not telegram_id:
        print("Send Stories: Telegram bot token or chat ID is not set. Please check the env file.")
        return
    if not story_data:
        print(f"Send Stories: No stories to send for story data: {story_data}")
        return
    bot = Bot(token=bot_token)
    for data in story_data:
        try:
            await bot.send_photo(chat_id=telegram_id, photo=data["image_url"], caption=data["description"])
        except telegram.error.TelegramError as e:
            print(f"Failed to send story to Telegram: {e}")