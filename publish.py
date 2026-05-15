#!/usr/bin/env python3
"""
publish.py — nahraje markdown article jako draft do Blog API.

Usage:
    python publish.py articles/2026-03-21-nazev-clanku-cs.md

Setup:
    Create a .env file in this directory with:
        BLOG_API_TOKEN=your_api_token
        AUTHOR_ID=your_author_id   (optional, default: 1)
"""

import sys
import os
import json
import math
import re
import requests
from datetime import date
from pathlib import Path

# --- Load configuration ---

def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

API_BASE = os.environ.get("BLOG_API_BASE", "https://example.com/api")
TOKEN = os.environ.get("BLOG_API_TOKEN", "")
ADMIN_URL = os.environ.get("BLOG_ADMIN_URL", "")

if not TOKEN:
    print("❌ Missing BLOG_API_TOKEN v fileu .env")
    print("   Create a .env file with:")
    print("   BLOG_API_TOKEN=your_api_token")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json",
}

# --- Parse frontmatter ---

def parse_frontmatter(text):
    """Extract YAML frontmatter and article body."""
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    raw = text[3:end].strip()
    body = text[end + 3:].strip()

    meta = {}
    for line in raw.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"').strip("'")
            meta[key.strip()] = val

    # Type conversion
    if "isFeatured" in meta:
        meta["isFeatured"] = meta["isFeatured"].lower() == "true"
    if "readTime" in meta:
        try:
            meta["readTime"] = int(meta["readTime"])
        except ValueError:
            pass

    return meta, body

# --- Reading time calculation ---

def calculate_read_time(text):
    """Word count divided by 200 wpm, rounded up."""
    words = len(re.findall(r'\w+', text))
    return max(1, math.ceil(words / 200))

# --- Generating slugu ---

def slugify(text):
    """Convert name to URL-friendly slug."""
    text = text.lower()
    # Czech diakritika
    replacements = {
        'á':'a','č':'c','ď':'d','é':'e','ě':'e','í':'i','ň':'n',
        'ó':'o','ř':'r','š':'s','ť':'t','ú':'u','ů':'u','ý':'y','ž':'z',
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text.strip())
    text = re.sub(r'-+', '-', text)
    return text[:80]

# --- Resolve author and category IDs ---

def get_author_id(name_or_id):
    """Find author ID by name or return number directly."""
    if str(name_or_id).isdigit():
        return int(name_or_id)

    try:
        r = requests.get(f"{API_BASE}/blog/authors/", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            for author in results:
                if name_or_id.lower() in str(author.get("name", "")).lower():
                    return author.get("id")
    except Exception:
        pass

    # Default: first author
    return int(os.environ.get("AUTHOR_ID", "1"))

def get_category_id(name_or_id):
    """Find category ID by name or return number directly."""
    if str(name_or_id).isdigit():
        return int(name_or_id)

    try:
        r = requests.get(f"{API_BASE}/blog/categories/", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            for cat in results:
                cat_name = cat.get("name", cat.get("title", ""))
                if name_or_id.lower() in cat_name.lower():
                    return cat.get("id")
    except Exception:
        pass

    return None

# --- Detect API schema (which fields POST accepts) ---

def detect_content_field():
    """Detect the field name for article content (content/body/text)."""
    try:
        r = requests.options(f"{API_BASE}/blog/posts/", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            schema = r.json()
            actions = schema.get("actions", {}).get("POST", {})
            for field in ["content", "body", "text", "html_content"]:
                if field in actions:
                    return field
    except Exception:
        pass
    return "content"  # default assumption

# --- Main publish function ---

def publish(filepath):
    path = Path(filepath)
    if not path.exists():
        print(f"❌ Soubor nenalezen: {filepath}")
        sys.exit(1)

    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)

    print(f"\n📄 Uploading: {path.name}")

    # Required fields
    title = meta.get("title", "")
    if not title:
        print("❌ Missing 'title' ve frontmatter")
        sys.exit(1)

    slug = meta.get("slug") or slugify(title)
    read_time = meta.get("readTime") or calculate_read_time(body)
    excerpt = meta.get("excerpt", body[:200].replace("\n", " ") + "...")
    is_featured = meta.get("isFeatured", False)
    pub_date = meta.get("date", str(date.today()))

    # Kategorie a autor
    category_raw = meta.get("category", "DPP")
    author_raw = meta.get("author", os.environ.get("AUTHOR_ID", "1"))

    print(f"   Looking up category '{category_raw}'...")
    category_id = get_category_id(category_raw)
    if not category_id:
        print(f"   ⚠️  Category not found, trying to send as string")

    print(f"   Looking up author '{author_raw}'...")
    author_id = get_author_id(str(author_raw))

    # Pole pro obsah
    content_field = detect_content_field()
    print(f"   Pole pro obsah: '{content_field}'")

    # Build payload
    payload = {
        "slug": slug,
        "title": title,
        "excerpt": excerpt[:500],
        content_field: body,
        "date": pub_date,
        "readTime": read_time,
        "isFeatured": is_featured,
        "isPublished": False,  # always draft
        "author": author_id,
    }

    # Kategorie — zkus ID, pak string
    if category_id:
        payload["category"] = category_id
    else:
        payload["category"] = category_raw

    print(f"\n   Sending POST to {API_BASE}/blog/posts/")
    print(f"   Slug: {slug}")
    print(f"   Read time: {read_time} min | Length: {len(body.split())} words")

    try:
        r = requests.post(
            f"{API_BASE}/blog/posts/",
            headers=HEADERS,
            json=payload,
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        print("❌ Failed to connect to API.")
        print("   Check if Tailscale (VPN) is running.")
        sys.exit(1)

    if r.status_code in (200, 201):
        data = r.json()
        post_id = data.get("id", "?")
        print(f"\n✅ Draft created!")
        print(f"   Admin URL: {ADMIN_URL}/{post_id}/change/")

        # --- Generating hero image ---
        try:
            from generate_blog_image import generate_blog_image
            image_path = generate_blog_image(
                title=title,
                category=meta.get("category", "DPP"),
                excerpt=excerpt,
                title_cs=meta.get("title_cs", ""),
            )
            print(f"\n🖼  Hero image saved: {image_path}")
            image_checklist = f"   3. Nahraj hero image z: {image_path}"
        except Exception as e:
            print(f"\n⚠️  Generating image selhalo: {e}")
            image_checklist = "   3. Upload featured image manually"

        print(f"\n📋 What to do next:")
        print(f"   1. Open: {ADMIN_URL}/{post_id}/change/")
        print(f"   2. Review and edit text")
        print(image_checklist)
        print(f"   4. Set 'Is published' to ON")
        print(f"   5. Klikni Save — article je live 🚀")
    else:
        print(f"\n❌ Error {r.status_code}")
        print(f"   Response: {r.text[:1000]}")
        print(f"\n   Payload (pro debug):")
        payload_debug = {k: v if k != content_field else f"[{len(str(v))} chars]" for k, v in payload.items()}
        print(f"   {json.dumps(payload_debug, ensure_ascii=False, indent=2)}")
        sys.exit(1)

# --- Entry point ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python publish.py path/k/article.md")
        sys.exit(1)
    publish(sys.argv[1])
