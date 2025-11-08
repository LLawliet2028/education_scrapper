import os
from dotenv import load_dotenv
load_dotenv()

# DB
DATABASE_URL = "sqlite:///trends.db"

# YouTube API
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Reddit API
REDDIT_CLIENT_ID = "QxCygXhPhlw0ErkZeOceTw"  
REDDIT_SECRET = "z6kF6tNjzHbMUIln4ZOuUJJfXsJezg"  
REDDIT_USER_AGENT = "education_scraper by u/Character_Vehicle553"



