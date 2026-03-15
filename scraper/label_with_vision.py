"""
label_with_vision.py — Step 2b: Auto-label meal deal items using GPT-4o Vision
================================================================================
Reads meal_deals_scored.json, sends each image URL to OpenAI's Vision API,
and asks GPT to identify the main, snack, and drink.

Outputs labels.csv which you should SPOT-CHECK before building the database.

USAGE:
    export OPENAI_API_KEY="sk-your-key-here"
    python label_with_vision.py

    Or on Windows:
    set OPENAI_API_KEY=sk-your-key-here
    python label_with_vision.py

INPUT:  meal_deals_scored.json  (from extract_scores.py)
OUTPUT: labels.csv              (auto-generated, needs spot-checking)

COST ESTIMATE:
    gpt-4o-mini with low detail: ~$0.0003 per image
    50 images ≈ $0.015 (about 1.5 pence)y
    100 images ≈ $0.03 (about 3 pence)
"""

import json
import csv
import os
import time
import requests


# ============================================================
# CONFIG
# ============================================================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-4o-mini"       # cheapest vision model, plenty good for this
DETAIL = "low"               # "low" = fixed 85 tokens per image, very cheap
SLEEP_BETWEEN_CALLS = 1.0   # seconds — stay under rate limits
OUTPUT_FILE = "data/labels.csv"


# The prompt that tells GPT what to extract
SYSTEM_PROMPT = """You are a UK meal deal expert. You will be shown a photo of a UK supermarket meal deal .

A meal deal has exactly 3 items:
- MAIN: a sandwich, wrap, baguette, pasta, salad, or sushi
- SNACK: crisps, fruit, yogurt, chocolate bar, nuts, popcorn, or similar
- DRINK: a bottle or can of drink (water, juice, smoothie, energy drink, fizzy drink)

From the image, identify each item as specifically as possible.
Also identify which store/vendor the meal deal is from if you can tell (from packaging, bags, receipts, or store branding).
If you cannot determine the vendor, say "unknown".

Respond in EXACTLY this format (no other text):
vendor: [store name or unknown]
main: [item name]
snack: [item name]  
drink: [item name]

Examples of good responses:
vendor: tesco
main: chicken club sandwich
snack: walkers cheese and onion crisps
drink: oasis citrus punch

vendor: unknown
main: blt sandwich
snack: hula hoops original
drink: diet coke 500ml"""


def call_vision_api(image_url):
    """
    Send an image URL to GPT-4o-mini Vision API.
    Returns the raw text response.
    
    Uses the requests library directly (no openai package needed).
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    payload = {
        "model": MODEL,
        "max_tokens": 150,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What are the three meal deal items in this photo?",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                            "detail": DETAIL,
                        },
                    },
                ],
            },
        ],
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def parse_response(text):
    """
    Parse GPT's response into a dict.
    Expected format:
        vendor: tesco
        main: chicken club sandwich
        snack: walkers cheese and onion
        drink: oasis citrus punch
    """
    result = {"vendor": "unknown", "main": "", "snack": "", "drink": ""}

    for line in text.lower().strip().split("\n"):
        line = line.strip()
        if line.startswith("vendor:"):
            result["vendor"] = line.split(":", 1)[1].strip()
        elif line.startswith("main:"):
            result["main"] = line.split(":", 1)[1].strip()
        elif line.startswith("snack:"):
            result["snack"] = line.split(":", 1)[1].strip()
        elif line.startswith("drink:"):
            result["drink"] = line.split(":", 1)[1].strip()

    return result


def label_all_posts(scored_posts):
    """
    Send each post's image to GPT Vision and collect labels.
    Returns a list of label dicts.
    """
    labels = []
    total = len(scored_posts)
    errors = 0

    for i, post in enumerate(scored_posts):
        image_url = post["image_url"]
        title = post.get("title", "")

        print(f"  [{i+1}/{total}] {title[:55]}...")

        try:
            raw_response = call_vision_api(image_url)
            parsed = parse_response(raw_response)

            labels.append({
                "post_id": post["post_id"],
                "vendor": parsed["vendor"],
                "main": parsed["main"],
                "snack": parsed["snack"],
                "drink": parsed["drink"],
                "raw_response": raw_response,  # keep for debugging
                "image_url": image_url,
                "title": title,
            })

            # Show what GPT found
            print(f"         → {parsed['vendor']} | {parsed['main']} + {parsed['snack']} + {parsed['drink']}")

        except requests.exceptions.HTTPError as e:
            print(f"         ✗ API error: {e}")
            errors += 1
            # If we get a 429 (rate limit), wait longer
            if "429" in str(e):
                print("         Waiting 30s for rate limit...")
                time.sleep(30)
            labels.append({
                "post_id": post["post_id"],
                "vendor": "ERROR",
                "main": "",
                "snack": "",
                "drink": "",
                "raw_response": str(e),
                "image_url": image_url,
                "title": title,
            })

        except Exception as e:
            print(f"         ✗ Error: {str(e)[:60]}")
            errors += 1
            labels.append({
                "post_id": post["post_id"],
                "vendor": "ERROR",
                "main": "",
                "snack": "",
                "drink": "",
                "raw_response": str(e),
                "image_url": image_url,
                "title": title,
            })

        time.sleep(SLEEP_BETWEEN_CALLS)

    return labels, errors


def save_labels_csv(labels, filename=OUTPUT_FILE):
    """Save labels to CSV for spot-checking in Excel/Google Sheets."""
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "post_id", "vendor", "main", "snack", "drink",
            "image_url", "title", "raw_response",
        ])
        writer.writeheader()
        writer.writerows(labels)
    print(f"Saved to {filename}")


# ==================================================================
# MAIN
# ==================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  MEAL DEAL LABELLER — GPT-4o Vision")
    print("=" * 60)

    # Check API key
    if not OPENAI_API_KEY or OPENAI_API_KEY == "":
        print("\nERROR: No OpenAI API key found!")
        print("Set it with:")
        print("  export OPENAI_API_KEY='sk-your-key-here'    (Mac/Linux)")
        print("  set OPENAI_API_KEY=sk-your-key-here         (Windows)")
        print("\nGet a key at: https://platform.openai.com/api-keys")
        exit(1)

    # Load scored posts
    try:
        with open("data/meal_deals_scored.json", "r", encoding="utf-8") as f:
            scored_posts = json.load(f)
        # Only label posts that have ratings (skip unrated ones)
        rated_posts = [p for p in scored_posts if p["average_rating"] is not None]
        print(f"Loaded {len(scored_posts)} posts, {len(rated_posts)} have ratings")
    except FileNotFoundError:
        print("ERROR: data/meal_deals_scored.json not found!")
        print("Run extract_scores.py first.")
        exit(1)

    # Estimate cost
    cost_estimate = len(rated_posts) * 0.0003  # ~$0.0003 per image with gpt-4o-mini low detail
    print(f"\nEstimated cost: ~${cost_estimate:.3f} USD for {len(rated_posts)} images")
    print(f"Using model: {MODEL} (detail: {DETAIL})")

    # Confirm before spending money
    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        exit(0)

    # Label all posts
    print(f"\nLabelling {len(rated_posts)} meal deals...\n")
    labels, errors = label_all_posts(rated_posts)

    # Save
    save_labels_csv(labels)

    # Summary
    successful = sum(1 for l in labels if l["vendor"] != "ERROR")
    print(f"\n{'='*60}")
    print(f"  LABELLING COMPLETE")
    print(f"{'='*60}")
    print(f"  Successful:  {successful}/{len(labels)}")
    print(f"  Errors:      {errors}")
    print(f"  Output:      {OUTPUT_FILE}")
    print(f"\n  IMPORTANT: Open {OUTPUT_FILE} in Excel/Google Sheets")
    print(f"  and spot-check the results! Look for:")
    print(f"    - Items that seem wrong or generic")
    print(f"    - Posts where GPT couldn't identify items")
    print(f"    - Vendor guesses that look off")
    print(f"\n  Once you're happy, run: python build_database.py")