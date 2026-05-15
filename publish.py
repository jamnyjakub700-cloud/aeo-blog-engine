#!/usr/bin/env python3
"""
publish.py — nahraje markdown článek jako draft do Blog API.

Použití:
    python publish.py articles/2026-03-21-nazev-clanku-cs.md

Nastavení:
    Vytvoř soubor .env v této složce s obsahem:
        BLOG_API_TOKEN=tvůj_api_token
        CYRCID_AUTHOR_ID=id_tvého_autora   (volitelné, výchozí: 1)
"""

import sys
import os
import json
import math
import re
import requests
from datetime import date
from pathlib import Path

# --- Načtení konfigurace ---

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
    print("❌ Chybí BLOG_API_TOKEN v souboru .env")
    print("   Vytvoř soubor .env s obsahem:")
    print("   BLOG_API_TOKEN=tvůj_token_z_adminu")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json",
}

# --- Parsování frontmatter ---

def parse_frontmatter(text):
    """Vytáhne YAML frontmatter a tělo článku."""
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

    # Převod typů
    if "isFeatured" in meta:
        meta["isFeatured"] = meta["isFeatured"].lower() == "true"
    if "readTime" in meta:
        try:
            meta["readTime"] = int(meta["readTime"])
        except ValueError:
            pass

    return meta, body

# --- Výpočet délky čtení ---

def calculate_read_time(text):
    """Počet slov děleno 200 slov/min, zaokrouhleno nahoru."""
    words = len(re.findall(r'\w+', text))
    return max(1, math.ceil(words / 200))

# --- Generování slugu ---

def slugify(text):
    """Převede název na URL-friendly slug."""
    text = text.lower()
    # Česká diakritika
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

# --- Zjištění ID autora a kategorie ---

def get_author_id(name_or_id):
    """Najde ID autora podle jména nebo vrátí číslo přímo."""
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

    # Výchozí: první autor
    return int(os.environ.get("CYRCID_AUTHOR_ID", "1"))

def get_category_id(name_or_id):
    """Najde ID kategorie podle názvu nebo vrátí číslo přímo."""
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

# --- Zjištění schématu API (jaká pole POST přijímá) ---

def detect_content_field():
    """Zjistí, jak se jmenuje pole pro obsah článku (content/body/text)."""
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
    return "content"  # výchozí předpoklad

# --- Hlavní publikační funkce ---

def publish(filepath):
    path = Path(filepath)
    if not path.exists():
        print(f"❌ Soubor nenalezen: {filepath}")
        sys.exit(1)

    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)

    print(f"\n📄 Nahrávám: {path.name}")

    # Povinná pole
    title = meta.get("title", "")
    if not title:
        print("❌ Chybí 'title' ve frontmatter")
        sys.exit(1)

    slug = meta.get("slug") or slugify(title)
    read_time = meta.get("readTime") or calculate_read_time(body)
    excerpt = meta.get("excerpt", body[:200].replace("\n", " ") + "...")
    is_featured = meta.get("isFeatured", False)
    pub_date = meta.get("date", str(date.today()))

    # Kategorie a autor
    category_raw = meta.get("category", "DPP")
    author_raw = meta.get("author", os.environ.get("CYRCID_AUTHOR_ID", "1"))

    print(f"   Zjišťuji kategorii '{category_raw}'...")
    category_id = get_category_id(category_raw)
    if not category_id:
        print(f"   ⚠️  Kategorie '{category_raw}' nenalezena, zkouším odeslat jako string")

    print(f"   Zjišťuji autora '{author_raw}'...")
    author_id = get_author_id(str(author_raw))

    # Pole pro obsah
    content_field = detect_content_field()
    print(f"   Pole pro obsah: '{content_field}'")

    # Sestavení payloadu
    payload = {
        "slug": slug,
        "title": title,
        "excerpt": excerpt[:500],
        content_field: body,
        "date": pub_date,
        "readTime": read_time,
        "isFeatured": is_featured,
        "isPublished": False,  # vždy draft
        "author": author_id,
    }

    # Kategorie — zkus ID, pak string
    if category_id:
        payload["category"] = category_id
    else:
        payload["category"] = category_raw

    print(f"\n   Odesílám POST na {API_BASE}/blog/posts/")
    print(f"   Slug: {slug}")
    print(f"   Read time: {read_time} min | Délka: {len(body.split())} slov")

    try:
        r = requests.post(
            f"{API_BASE}/blog/posts/",
            headers=HEADERS,
            json=payload,
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        print("❌ Nepodařilo se připojit k API.")
        print("   Zkontroluj, zda máš zapnutý Tailscale (VPN).")
        sys.exit(1)

    if r.status_code in (200, 201):
        data = r.json()
        post_id = data.get("id", "?")
        print(f"\n✅ Draft vytvořen!")
        print(f"   Admin URL: {ADMIN_URL}/{post_id}/change/")

        # --- Generování hero image ---
        try:
            from generate_blog_image import generate_blog_image
            image_path = generate_blog_image(
                title=title,
                category=meta.get("category", "DPP"),
                excerpt=excerpt,
                title_cs=meta.get("title_cs", ""),
            )
            print(f"\n🖼  Hero image uložen: {image_path}")
            image_checklist = f"   3. Nahraj hero image z: {image_path}"
        except Exception as e:
            print(f"\n⚠️  Generování obrázku selhalo: {e}")
            image_checklist = "   3. Nahraj featured image ručně"

        print(f"\n📋 Co teď udělat:")
        print(f"   1. Otevři: {ADMIN_URL}/{post_id}/change/")
        print(f"   2. Zkontroluj text a případně uprav")
        print(image_checklist)
        print(f"   4. Přepni 'Is published' na ON")
        print(f"   5. Klikni Save — článek je live 🚀")
    else:
        print(f"\n❌ Chyba {r.status_code}")
        print(f"   Response: {r.text[:1000]}")
        print(f"\n   Payload (pro debug):")
        payload_debug = {k: v if k != content_field else f"[{len(str(v))} znaků]" for k, v in payload.items()}
        print(f"   {json.dumps(payload_debug, ensure_ascii=False, indent=2)}")
        sys.exit(1)

# --- Spuštění ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Použití: python publish.py cesta/k/article.md")
        sys.exit(1)
    publish(sys.argv[1])
