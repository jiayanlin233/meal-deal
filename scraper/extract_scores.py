"""
extract_scores.py — Step 2 of the Meal Deal Rater pipeline
============================================================
Reads meal_deals_raw.json, parses "X/10" ratings from comments,
and calculates average scores. Outputs meal_deals_scored.json.

USAGE:
    python extract_scores.py

INPUT:  meal_deals_raw.json  (from scrape_reddit.py)
OUTPUT: meal_deals_scored.json
"""

import json
import re


def extract_rating(comment_text):
    """
    Try to find an "X/10" rating in a comment.

    Matches patterns like:
        7/10        → 7.0
        8.5/10      → 8.5
        3 / 10      → 3.0
        solid 9/10  → 9.0

    Returns the number (float) if found, or None if no rating.
    """
    # This regex looks for a number (possibly decimal) followed by /10
    # \b ensures we don't match things like "210/100"
    pattern = r'\b(\d+\.?\d*)\s*/\s*10\b'
    match = re.search(pattern, comment_text)

    if match:
        rating = float(match.group(1))
        # Sanity check: rating should be between 0 and 10
        if 0 <= rating <= 10:
            return rating

    return None


def process_posts(posts):
    """
    For each post, extract ratings from comments and calculate
    the average score. Also collect "notable" comments (ones with
    interesting text, not just a bare rating).
    """
    scored_posts = []

    for post in posts:
        ratings = []
        notable_comments = []

        for comment in post["comments"]:
            body = comment["body"]
            rating = extract_rating(body)

            if rating is not None:
                ratings.append(rating)

            # Collect comments that are interesting (not just "7/10")
            # A "notable" comment has more than just the rating
            cleaned = re.sub(r'\d+\.?\d*\s*/\s*10', '', body).strip()
            if len(cleaned) > 15 and len(body) < 500:
                notable_comments.append({
                    "text": body,
                    "author": comment["author"],
                    "score": comment["score"],  # Reddit upvotes on comment
                    "rating": rating,  # Their X/10 rating, if any
                })

        # Calculate average score
        avg_score = None
        if ratings:
            avg_score = round(sum(ratings) / len(ratings), 1)

        # Sort notable comments by Reddit upvotes (most popular first)
        notable_comments.sort(key=lambda c: c["score"], reverse=True)

        # Build the scored post object
        scored_post = {
            "post_id": post["post_id"],
            "title": post["title"],
            "image_url": post["image_url"],
            "permalink": post["permalink"],
            "created_utc": post["created_utc"],
            "reddit_score": post["score"],  # upvotes on the post itself
            "average_rating": avg_score,
            "num_ratings": len(ratings),
            "all_ratings": ratings,
            "top_comments": notable_comments[:5],  # keep top 5
        }
        scored_posts.append(scored_post)

    return scored_posts


def print_summary(scored_posts):
    """Print a nice summary of what we found."""
    total = len(scored_posts)
    with_ratings = sum(1 for p in scored_posts if p["average_rating"] is not None)
    all_ratings = [r for p in scored_posts for r in p["all_ratings"]]

    print(f"\n{'='*60}")
    print(f"  SCORING SUMMARY")
    print(f"{'='*60}")
    print(f"  Total posts:           {total}")
    print(f"  Posts with ratings:    {with_ratings}")
    print(f"  Posts without ratings: {total - with_ratings}")
    print(f"  Total ratings found:   {len(all_ratings)}")
    if all_ratings:
        print(f"  Overall average:       {sum(all_ratings)/len(all_ratings):.1f}/10")
        print(f"  Highest avg:           {max(p['average_rating'] for p in scored_posts if p['average_rating'])}/10")
        print(f"  Lowest avg:            {min(p['average_rating'] for p in scored_posts if p['average_rating'])}/10")

    # Show top 5 highest-rated meal deals
    rated = [p for p in scored_posts if p["average_rating"] is not None and p["num_ratings"] >= 3]
    rated.sort(key=lambda p: p["average_rating"], reverse=True)

    if rated:
        print(f"\n  TOP 5 MEAL DEALS:")
        for p in rated[:5]:
            print(f"    {p['average_rating']}/10 ({p['num_ratings']} ratings) — {p['title'][:60]}")

    # Show bottom 5
    if len(rated) >= 5:
        print(f"\n  BOTTOM 5 MEAL DEALS:")
        for p in rated[-5:]:
            print(f"    {p['average_rating']}/10 ({p['num_ratings']} ratings) — {p['title'][:60]}")


# ==================================================================
# MAIN
# ==================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  MEAL DEAL SCRAPER — Step 2: Extract Scores")
    print("=" * 60)

    # Load raw data
    try:
        with open("data/meal_deals_raw.json", "r", encoding="utf-8") as f:
            raw_posts = json.load(f)
        print(f"Loaded {len(raw_posts)} posts from data/meal_deals_raw.json")
    except FileNotFoundError:
        print("ERROR: data/meal_deals_raw.json not found!")
        print("Run scrape_reddit.py first.")
        exit(1)

    # Process
    scored = process_posts(raw_posts)

    # Save
    with open("data/meal_deals_scored.json", "w", encoding="utf-8") as f:
        json.dump(scored, f, indent=2, ensure_ascii=False)
    print(f"Saved to data/meal_deals_scored.json")

    # Summary
    print_summary(scored)
    print("\nNext step: manually label items (or run build_database.py)")