"""
scrape_reddit.py — Step 1 of the Meal Deal Rater pipeline
==========================================================
Scrapes r/MealDealRates using Reddit's public JSON API.
No API keys, no PRAW, no registration needed.

USAGE:
    python scrape_reddit.py

OUTPUT:
    meal_deals_raw.json — array of post objects with comments
"""

import requests
import json
import time
from datetime import datetime


# ============================================================
# CONFIG — tweak these as needed
# ============================================================
SUBREDDIT = "MealDealRates"
USER_AGENT = "MealDealScraper/1.0 (student project)"
TIME_FILTER = "all"       # "hour", "day", "week", "month", "year", "all"
RATING_FILTER = "top"     # "hot", "new", "top", "rising"
SLEEP_BETWEEN_POSTS = 1.0 # seconds — be polite to Reddit's API


def get_subreddit_posts(subreddit, user_agent, time_filter="all", rating_filter="top"):
    """
    Fetch post listing from a subreddit.
    Returns the raw JSON response.
    """
    url = f"https://api.reddit.com/r/{subreddit}/{rating_filter}.json"
    params = {"t": time_filter, "limit": 100}  # 100 is Reddit's max per page
    headers = {"User-Agent": user_agent}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def get_post_details(permalink, user_agent):
    """
    Fetch full post details + comments for a single post.
    Reddit returns a 2-element array:
      [0] = the post itself
      [1] = the comments
    """
    url = f"https://api.reddit.com{permalink}.json"
    params = {"limit": 50}  # max comments to fetch
    headers = {"User-Agent": user_agent}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def extract_image_url(post_data):
    """
    Try to get an image URL from a post.
    Returns the URL string or None.
    """
    url = post_data.get("url", "")

    # Direct image links (i.redd.it, i.imgur.com, or file extensions)
    if any(url.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
        return url
    if "i.redd.it" in url:
        return url
    if "i.imgur.com" in url:
        return url

    # Reddit-hosted image (sometimes in preview)
    preview = post_data.get("preview", {})
    if preview:
        images = preview.get("images", [])
        if images:
            return images[0].get("source", {}).get("url", "").replace("&amp;", "&")

    return None


def scrape():
    """Main scraping function."""
    print(f"Fetching {RATING_FILTER} posts from r/{SUBREDDIT} (time: {TIME_FILTER})...")
    listing_data = get_subreddit_posts(SUBREDDIT, USER_AGENT, TIME_FILTER, RATING_FILTER)

    children = listing_data["data"]["children"]
    print(f"Got {len(children)} posts from listing")

    posts_data = []
    skipped = 0

    for i, child in enumerate(children):
        post_summary = child["data"]
        permalink = post_summary["permalink"]
        title = post_summary["title"]

        # Check for image before fetching comments (saves API calls)
        image_url = extract_image_url(post_summary)
        if image_url is None:
            skipped += 1
            continue

        print(f"  [{i+1}/{len(children)}] {title[:60]}...")

        try:
            time.sleep(SLEEP_BETWEEN_POSTS)
            post_details = get_post_details(permalink, USER_AGENT)

            # Post data is in [0], comments in [1]
            post_full = post_details[0]["data"]["children"][0]["data"]
            comment_children = post_details[1]["data"]["children"]

            # Re-check image URL from full post data (sometimes has more info)
            if image_url is None:
                image_url = extract_image_url(post_full)
                if image_url is None:
                    skipped += 1
                    continue

            # Extract comments
            comments = []
            for comment_child in comment_children:
                if comment_child["kind"] != "t1":
                    continue
                cd = comment_child["data"]
                if cd.get("body", "") in ["[deleted]", "[removed]"]:
                    continue

                comments.append({
                    "author": cd.get("author", "[deleted]"),
                    "body": cd.get("body", ""),
                    "score": cd.get("score", 0),
                    "created_utc": datetime.utcfromtimestamp(cd["created_utc"]).isoformat(),
                })

            # Build post object
            posts_data.append({
                "post_id": post_full["id"],
                "title": post_full["title"],
                "score": post_full.get("ups", 0),
                "num_comments": post_full.get("num_comments", 0),
                "image_url": image_url,
                "permalink": f"https://www.reddit.com{permalink}",
                "created_utc": datetime.utcfromtimestamp(post_full["created_utc"]).isoformat(),
                "comments": comments,
            })

        except Exception as e:
            print(f"    Error: {str(e)[:60]}... Skipping.")
            continue

    return posts_data, skipped


def save_to_json(data, filename="meal_deals_raw.json"):
    """Save scraped data to JSON."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved to {filename} ({len(data)} posts)")


# ==================================================================
# MAIN
# ==================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  MEAL DEAL SCRAPER — No API keys needed!")
    print("=" * 60)

    posts, skipped = scrape()

    save_to_json(posts)

    print(f"\nDone! {len(posts)} image posts scraped, {skipped} non-image posts skipped.")

    if posts:
        print(f"\n--- PREVIEW (first post) ---")
        first = posts[0]
        print(f"  Title:    {first['title'][:80]}")
        print(f"  Image:    {first['image_url'][:80]}")
        print(f"  Upvotes:  {first['score']}")
        print(f"  Comments: {len(first['comments'])}")
        if first["comments"]:
            print(f"  Top comment: {first['comments'][0]['body'][:100]}...")

    print("\nNext step: python extract_scores.py")