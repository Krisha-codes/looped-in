import feedparser
import requests

HEADERS = {"User-Agent": "LoopedIn/1.0"}

# Category -> RSS feed. Add more later by adding lines here.
FEEDS = {
    "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "us": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
    "science": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "basketball": "https://feeds.bbci.co.uk/sport/basketball/rss.xml",
}


def get_headlines(category):
    """Get the latest headlines for one news category."""
    if category not in FEEDS:
        return {"error": f"Unknown category. Choose from: {list(FEEDS)}"}

    try:
        response = requests.get(FEEDS[category], headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"Could not fetch {category} news: {e}"}

    feed = feedparser.parse(response.content)
    stories = []
    for entry in feed.entries[:8]:
        stories.append({
            "title": entry.get("title", ""),
            "summary": entry.get("summary", "")[:200],
            "url": entry.get("link", "").split("?")[0],
            "source": "BBC News",
        })
    return {"category": category, "stories": stories}


def get_hacker_news():
    """Get the top tech/CS stories from Hacker News right now."""
    base = "https://hacker-news.firebaseio.com/v0"
    try:
        ids = requests.get(f"{base}/topstories.json", timeout=10).json()[:8]
        stories = []
        for story_id in ids:
            item = requests.get(f"{base}/item/{story_id}.json", timeout=10).json()
            if not item or "title" not in item:
                continue
            stories.append({
                "title": item["title"],
                # Some posts (like "Ask HN") have no external link
                "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                "source": "Hacker News",
                "points": item.get("score", 0),
            })
        return {"stories": stories}
    except requests.RequestException as e:
        return {"error": f"Could not fetch Hacker News: {e}"}


if __name__ == "__main__":
    print(get_headlines("world"))
    print(get_hacker_news())