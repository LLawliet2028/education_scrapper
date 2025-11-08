from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY

def fetch_youtube_trends():
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    req = youtube.videos().list(
        part="snippet,statistics",
        chart="mostPopular",
        regionCode="IN",
        maxResults=20
    )
    response = req.execute()

    results = []
    for item in response["items"]:
        title = item["snippet"]["title"]
        score = float(item["statistics"].get("viewCount", 0))

        results.append({
            "keyword": title,
            "score": score,
            "source": "youtube"
        })

    return results

