"""
build_database.py — Step 3 of the Meal Deal Rater pipeline
============================================================
Merges scored posts with manual item labels (from labels.csv)
to create the final JSON database that powers the website.

USAGE:
    python build_database.py

INPUT:
    meal_deals_scored.json  (from extract_scores.py)
    labels.csv              (you create this manually — see template below)

OUTPUT:
    ../docs/data.json       (the website reads this file)

LABELS.CSV FORMAT:
    post_id,vendor,main,snack,drink
    abc123,tesco,chicken club sandwich,walkers cheese and onion,oasis citrus punch
    def456,sainsburys,blt sandwich,hula hoops original,ribena
    ...

If labels.csv doesn't exist yet, this script will:
1. Generate a template CSV with all post IDs and image URLs
2. Create the database using ONLY scored posts (no item matching)
   — this is enough for the "browse mode" of the website
"""

import json
import csv
import os


def load_scored_posts(filename="data/meal_deals_scored.json"):
    """Load the scored posts from Step 2."""
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def load_labels(filename="data/labels.csv"):
    """
    Load manual item labels from CSV.
    Returns a dict: post_id -> {vendor, main, snack, drink}
    Returns empty dict if file doesn't exist.
    """
    if not os.path.exists(filename):
        return {}

    labels = {}
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            post_id = row["post_id"].strip()
            # Skip rows where items haven't been filled in yet or had errors
            if row.get("main", "").strip() == "":
                continue
            if row.get("vendor", "").strip().upper() == "ERROR":
                continue
            labels[post_id] = {
                "vendor": row.get("vendor", "unknown").strip().lower(),
                "main": row["main"].strip().lower(),
                "snack": row["snack"].strip().lower(),
                "drink": row["drink"].strip().lower(),
            }
    return labels


def generate_label_template(scored_posts, filename="labels_template.csv"):
    """
    Generate a CSV template for you to fill in manually.
    Opens each post's image URL so you can see what items are in the photo.
    """
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["post_id", "vendor", "main", "snack", "drink", "image_url", "title"])
        for post in scored_posts:
            writer.writerow([
                post["post_id"],
                "",  # vendor — you fill this in
                "",  # main — you fill this in
                "",  # snack — you fill this in
                "",  # drink — you fill this in
                post["image_url"],
                post["title"],
            ])
    print(f"\nGenerated {filename} with {len(scored_posts)} rows.")
    print("Open this file in Excel/Google Sheets, look at each image URL,")
    print("and fill in the vendor, main, snack, drink columns.")
    print("Then save as labels.csv (remove the image_url and title columns if you like).")


def build_database(scored_posts, labels):
    """
    Build the final database JSON.

    Structure:
    {
        "generated_at": "2025-...",
        "total_deals": 42,
        "items": {                              <-- master item lists (for the slot machine dropdowns)
            "main": ["chicken club", "blt", ...],
            "snack": ["walkers cheese and onion", ...],
            "drink": ["oasis citrus punch", ...]
        },
        "deals": [                              <-- all rated meal deals
            {
                "id": "abc123",
                "vendor": "tesco",
                "items": {"main": "...", "snack": "...", "drink": "..."},
                "score": 7.3,
                "num_ratings": 12,
                "top_comments": [...],
                "image_url": "...",
                "permalink": "..."
            }
        ]
    }
    """
    from datetime import datetime

    deals = []
    all_mains = set()
    all_snacks = set()
    all_drinks = set()

    for post in scored_posts:
        # Skip posts with no ratings
        if post["average_rating"] is None:
            continue

        deal = {
            "id": post["post_id"],
            "score": post["average_rating"],
            "num_ratings": post["num_ratings"],
            "top_comments": [
                {
                    "text": c["text"],
                    "author": c["author"],
                    "rating": c["rating"],
                }
                for c in post["top_comments"]
            ],
            "image_url": post["image_url"],
            "permalink": post["permalink"],
            "title": post["title"],
        }

        # Add item labels if we have them
        if post["post_id"] in labels:
            label = labels[post["post_id"]]
            deal["vendor"] = label["vendor"]
            deal["items"] = {
                "main": label["main"],
                "snack": label["snack"],
                "drink": label["drink"],
            }
            all_mains.add(label["main"])
            all_snacks.add(label["snack"])
            all_drinks.add(label["drink"])
        else:
            deal["vendor"] = "unknown"
            deal["items"] = None  # not yet labelled

        deals.append(deal)

    # Sort by score (highest first)
    deals.sort(key=lambda d: d["score"], reverse=True)

    database = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_deals": len(deals),
        "labelled_deals": sum(1 for d in deals if d["items"] is not None),
        "items": {
            "main": sorted(all_mains),
            "snack": sorted(all_snacks),
            "drink": sorted(all_drinks),
        },
        "deals": deals,
    }

    return database


# ==================================================================
# MAIN
# ==================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  MEAL DEAL SCRAPER — Step 3: Build Database")
    print("=" * 60)

    # Load scored posts
    try:
        scored_posts = load_scored_posts()
        print(f"Loaded {len(scored_posts)} scored posts")
    except FileNotFoundError:
        print("ERROR: meal_deals_scored.json not found!")
        print("Run extract_scores.py first.")
        exit(1)

    # Load labels (or generate template)
    labels = load_labels()
    if labels:
        print(f"Loaded {len(labels)} item labels from labels.csv")
    else:
        print("No labels.csv found — generating template...")
        generate_label_template(scored_posts)
        print("\nBuilding database WITHOUT item labels (browse mode only)...")

    # Build the database
    database = build_database(scored_posts, labels)

    # Save to docs/ folder (where the website lives)
    output_path = os.path.join("..", "docs", "data.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=2, ensure_ascii=False)

    # Also save a local copy
    with open("data/deals_database.json", "w", encoding="utf-8") as f:
        json.dump(database, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"  DATABASE BUILT!")
    print(f"{'='*60}")
    print(f"  Total rated deals:   {database['total_deals']}")
    print(f"  Labelled deals:      {database['labelled_deals']}")
    print(f"  Unique mains:        {len(database['items']['main'])}")
    print(f"  Unique snacks:       {len(database['items']['snack'])}")
    print(f"  Unique drinks:       {len(database['items']['drink'])}")
    print(f"\n  Saved to: {output_path}")
    print(f"  Also at:  data/deals_database.json")
    print(f"\nYour website data is ready!")