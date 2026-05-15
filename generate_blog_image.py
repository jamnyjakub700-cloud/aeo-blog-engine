#!/usr/bin/env python3
"""
generate_blog_image.py — Blog Hero Image Generator

Generuje featured image pro blog článek (1920×1080, 16:9).
Sdílí vizuální DNA s create_post.py: Ideogram pozadí, adaptive overlay,
Bebas Neue + DM Sans, cream paleta, cyrcID logo.

Každý článek dostane:
  - Unikátní texturu látky (rotace 4–5 variant na kategorii, určeno hashem titulku)
  - Titulek článku přes obrázek (Bebas Neue, cream, vlevo dole, auto-wrap)
  - Kategorii nad titulkem (spaced caps, warm accent)
  - Divider linku
  - Logo vpravo nahoře

Použití:
    python generate_blog_image.py --title "Jak připravit DPP audit" \
                                  --category "DPP" \
                                  --excerpt "Od 2028 musí každý textilní výrobek..."
"""

import sys
import os
import re
import argparse
import hashlib
import requests
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageStat

# ═══════════════════════════════════════════════════════════════
#  KONFIGURACE
# ═══════════════════════════════════════════════════════════════

def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

IDEOGRAM_API_KEY = os.environ.get("IDEOGRAM_API_KEY", "")
IDEOGRAM_URL     = "https://api.ideogram.ai/v1/ideogram-v3/generate"

LOGO_PATH  = os.environ.get("LOGO_PATH",
             "./assets/logo.png")
OUTPUT_DIR = os.environ.get("BLOG_IMAGE_DIR",
             "./blog_images")
FONTS_DIR  = os.environ.get("FONTS_DIR",
             "./fonts")

IMAGE_SIZE   = (1920, 1080)
FONT_BEBAS   = os.path.join(FONTS_DIR, "BebasNeue-Regular.ttf")
FONT_DM_LIGHT= os.path.join(FONTS_DIR, "DMSans-Light.ttf")

_FALLBACK_BOLD = [
    ("/Library/Fonts/Arial Bold.ttf", None),
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", None),
    ("/System/Library/Fonts/Helvetica.ttc", 1),
]
_FALLBACK_LIGHT = [
    ("/Library/Fonts/Arial.ttf", None),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", None),
    ("/System/Library/Fonts/Helvetica.ttc", 0),
]

COLOR_CREAM       = (245, 240, 232)
COLOR_WARM_ACCENT = (210, 195, 160)

PAD        = 64    # okraj od kraje obrazovky
LABEL_GAP  = 7     # mezery mezi písmeny kategorie
LOGO_WIDTH = 88


# ═══════════════════════════════════════════════════════════════
#  FONT LOADING
# ═══════════════════════════════════════════════════════════════

def _load_font(path, size, fallbacks=None):
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        pass
    if fallbacks:
        for fb_path, fb_idx in (fallbacks or []):
            try:
                if fb_idx is not None:
                    return ImageFont.truetype(fb_path, size, index=fb_idx)
                return ImageFont.truetype(fb_path, size)
            except (OSError, IOError):
                continue
    return ImageFont.load_default()

def load_bebas(size):    return _load_font(FONT_BEBAS,    size, _FALLBACK_BOLD)
def load_dm_light(size): return _load_font(FONT_DM_LIGHT, size, _FALLBACK_LIGHT)


# ═══════════════════════════════════════════════════════════════
#  IDEOGRAM PROMPTY — rotace látek
#
#  Každá kategorie má 4–5 variant textury.
#  Výběr varianty = hash(title) % počet_variant
#  → každý článek dostane jiné pozadí, ale vždy sedí k tématu
# ═══════════════════════════════════════════════════════════════

_NEGATIVE = (
    "people, faces, hands, text, letters, words, numbers, logos, "
    "watermark, bright colors, oversaturated, busy background"
)

_PROMPT_GROUPS = {

    "regulation": [
        "Close-up macro photography of tightly woven technical canvas fabric, "
        "structured precise grid weave, cool olive and slate grey tones, "
        "sharp raking light from upper left casting geometric micro-shadows, "
        "extreme texture detail, wide landscape crop, no text, "
        "desaturated editorial aesthetic",

        "Wide macro shot of rigid woven polypropylene technical textile, "
        "pale grey and stone tones, hard overhead fluorescent light, "
        "clinical precision, repeating square grid pattern, "
        "landscape format, no text, desaturated",

        "Close-up of folded stiff interfacing fabric, cream and ecru tones, "
        "strong raking side light, precise grid structure visible, "
        "landscape format, no text, muted editorial",

        "Macro photography of industrial twill weave, charcoal and warm grey, "
        "diagonal rib pattern crisp in hard light, "
        "landscape format, no text, high contrast editorial",

        "Wide macro of plain-weave cotton shirting at extreme close range, "
        "cool white and pale blue tones, hard window light casting thread shadows, "
        "landscape format, no text, clinical editorial",

        "Macro shot of stiff woven buckram canvas, off-white and bone tones, "
        "raking directional light revealing every thread intersection, "
        "landscape format, no text, minimal editorial",

        "Close-up of structured ponte knit fabric, "
        "cool medium grey with subtle horizontal rib, hard side light, "
        "landscape format, no text, desaturated editorial",

        "Wide macro of woven label tape unspooled on flat surface, "
        "cream and warm white, soft top light, repeating geometric weave, "
        "landscape format, no text, minimal editorial",
    ],

    "sustainability": [
        "Wide macro photography of raw natural linen fibers unraveling, "
        "organic texture, warm sand and ecru tones, "
        "soft diffused natural light from the side, "
        "landscape format, no text, muted editorial",

        "Close-up of undyed organic cotton boll fibers spread across surface, "
        "cream and warm white tones, soft window light, "
        "landscape format, no text, clean editorial aesthetic",

        "Macro shot of loosely woven jute textile, warm amber and brown tones, "
        "diffused soft light, visible fiber imperfections, "
        "landscape format, no text, organic editorial",

        "Wide macro of recycled fabric cross-section showing fiber layers, "
        "muted terracotta and sand, raking side light, "
        "landscape format, no text, editorial material study",

        "Close-up of raw hemp canvas fabric, warm khaki and straw tones, "
        "soft diffused natural light, coarse fiber texture prominent, "
        "landscape format, no text, earthy editorial",

        "Macro of unbleached muslin draped loosely, "
        "warm cream and off-white, backlit soft light creating translucency, "
        "landscape format, no text, organic minimal editorial",

        "Wide macro of nettle fiber woven textile, pale sage and ecru, "
        "soft side light, organic irregular weave structure, "
        "landscape format, no text, natural editorial",

        "Close-up of cork-backed fabric surface, warm tan and amber, "
        "raking light revealing cellular texture, "
        "landscape format, no text, editorial material study",

        "Macro shot of bouclé yarn knit, warm oatmeal and cream loops, "
        "soft overhead light, irregular looped texture prominent, "
        "landscape format, no text, editorial fashion",
    ],

    "supply_chain": [
        "Wide macro photography of industrial woven mesh textile, "
        "metallic grey and charcoal tones, hard directional studio light, "
        "sharp geometric weave pattern, landscape format, no text, "
        "high contrast desaturated editorial",

        "Macro close-up of tight plain-weave polyester technical fabric, "
        "cool silver and steel tones, single hard light source, "
        "landscape format, no text, clinical aesthetic",

        "Wide shot of stacked rolled fabric bolts viewed from side, "
        "cool grey and slate, clean studio light, "
        "minimal industrial composition, landscape format, no text",

        "Macro of chain-link structure woven from metallic yarn, "
        "silver and dark grey, hard directional raking light, "
        "landscape format, no text, technical editorial",

        "Close-up of woven carbon fibre composite material, "
        "deep charcoal with subtle diagonal sheen, single hard studio light, "
        "landscape format, no text, technical editorial",

        "Wide macro of industrial non-woven spunbond fabric, "
        "cool pale grey, raking light revealing random fiber structure, "
        "landscape format, no text, clinical editorial",

        "Macro of tightly coiled thread spools viewed from above, "
        "cool grey and white, overhead studio light, "
        "geometric repeating composition, landscape format, no text",

        "Close-up of reflective technical tricot lining fabric, "
        "silver and cool grey with subtle sheen, hard side light, "
        "landscape format, no text, industrial editorial",
    ],

    "dpp": [
        "Close-up of a clean woven garment label on folded dark fabric, "
        "minimal composition, cool grey and charcoal, "
        "soft studio light, shallow depth of field, "
        "landscape format, no text visible, editorial",

        "Macro of fabric edge with woven selvedge detail, "
        "dark navy and white thread, precise studio light, "
        "landscape format, no text, clean product editorial",

        "Wide shot of folded dark technical fabric with subtle sheen, "
        "charcoal and midnight blue tones, single soft light source, "
        "minimal composition, landscape format, no text",

        "Close-up of care label stitching on dark wool fabric, "
        "warm charcoal and cream thread, soft focus background, "
        "landscape format, no text, editorial fashion",

        "Macro of serial number tag clipped to dark garment fabric, "
        "muted charcoal and cream, clinical studio light, "
        "landscape format, no visible text on tag, editorial product",

        "Wide macro of folded black technical jersey, "
        "deep charcoal with subtle surface texture, single soft light, "
        "minimal composition, landscape format, no text, editorial",

        "Close-up of woven brand tape on dark wool overcoat fabric, "
        "charcoal and ecru thread, raking light revealing weave, "
        "landscape format, no readable text, fashion editorial",

        "Macro of heat-transfer film applied to dark technical fabric, "
        "matte charcoal with reflective strip, hard studio light, "
        "landscape format, no text, industrial editorial",
    ],

    "implementation": [
        "Wide macro photography of folded premium textile layers, "
        "structured stacking of different fabric weights and weaves, "
        "neutral warm tones, soft directional light, "
        "landscape format, no text, editorial",

        "Macro of fabric cross-section showing warp and weft construction, "
        "cream and warm grey, raking studio light, "
        "landscape format, no text, material study",

        "Close-up of wool herringbone fabric at 45-degree angle, "
        "warm charcoal and cream, precise raking light, "
        "landscape format, no text, editorial menswear",

        "Wide macro of loosely woven gauze layers, cream and soft white, "
        "diffused backlight creating translucency, "
        "landscape format, no text, clean editorial",

        "Macro of seersucker cotton puckered texture, "
        "pale blue and white, soft diffused window light, "
        "landscape format, no text, editorial",

        "Close-up of jacquard woven fabric showing raised pattern, "
        "warm ivory and gold thread, raking side light revealing relief, "
        "landscape format, no text, editorial fashion",

        "Wide macro of flannel fabric surface, "
        "warm mid grey with soft nap texture, diffused overhead light, "
        "landscape format, no text, editorial menswear",

        "Macro of premium cotton poplin at high magnification, "
        "cool white and pale grey, hard raking light showing thread count, "
        "landscape format, no text, editorial product",

        "Close-up of double-weave fabric pulled apart at corner, "
        "cream and warm white two-layer structure, side light, "
        "landscape format, no text, material study editorial",
    ],

    "default": [
        "Wide macro photography of woven cotton fabric with subtle fold, "
        "muted earth tones, soft directional light, "
        "landscape format, no text, editorial",

        "Macro of fine merino wool knit texture, warm oatmeal and cream, "
        "soft diffused light, extreme fiber detail, "
        "landscape format, no text, editorial",

        "Close-up of denim twill fabric at angle, "
        "deep indigo and faded blue tones, hard side light, "
        "landscape format, no text, editorial",

        "Wide shot of silk satin folded fabric, "
        "cool ivory and pale grey, soft studio light creating sheen, "
        "landscape format, no text, editorial fashion",

        "Macro of fine cashmere knit, warm sand and camel tones, "
        "soft diffused light, extremely fine fiber detail, "
        "landscape format, no text, luxury editorial",

        "Close-up of velvet fabric surface at angle, "
        "deep teal with directional nap sheen, raking hard light, "
        "landscape format, no text, editorial fashion",

        "Wide macro of organza weave held against backlight, "
        "cool ivory and pale gold, diffused backlight showing translucency, "
        "landscape format, no text, editorial",

        "Macro of waffle-knit thermal fabric, "
        "warm cream and ecru, side light casting grid shadows, "
        "landscape format, no text, editorial",

        "Close-up of raw silk noil fabric, warm champagne and ivory, "
        "soft overhead light, irregular slub texture prominent, "
        "landscape format, no text, editorial fashion",
    ],
}

_KEYWORD_MAP = [
    ("regulation", ["regulation", "regulac", "espr", "compliance", "zákon",
                    "nařízení", "povinnost", "deadline", "legislation", "legislativ"]),
    ("sustainability", ["sustainable", "circular", "recycled", "recykl", "organic",
                        "upcycl", "udržiteln", "environment", "carbon", "footprint",
                        "emise", "lca", "životní prostředí"]),
    ("supply_chain", ["supply chain", "dodavatel", "řetěz", "blockchain",
                      "traceability", "transparenc", "tracking", "sledov",
                      "data", "infrastructure"]),
    ("dpp", ["qr", "label", "štítek", "scan", "tag", "digital product passport",
             "digitální produktový pas", "dpp", "identifier"]),
    ("implementation", ["audit", "implementac", "krok", "guide", "návod",
                        "proces", "checklist", "preparation", "příprava", "how to"]),
]


def _title_hash(title: str) -> int:
    """Deterministický hash titulku pro výběr varianty — stejný titulek = stejný obrázek."""
    return int(hashlib.md5(title.lower().encode()).hexdigest(), 16)


def build_blog_prompt(title: str, category: str, excerpt: str = "") -> str:
    text  = f"{title} {category} {excerpt}".lower()
    group = "default"
    for gname, keywords in _KEYWORD_MAP:
        if any(kw in text for kw in keywords):
            group = gname
            break

    variants = _PROMPT_GROUPS[group]
    chosen   = variants[_title_hash(title) % len(variants)]
    print(f"   Skupina: {group} | Varianta {_title_hash(title) % len(variants) + 1}/{len(variants)}")
    return chosen


# ═══════════════════════════════════════════════════════════════
#  GENEROVÁNÍ POZADÍ
# ═══════════════════════════════════════════════════════════════

def generate_background(prompt: str) -> Image.Image:
    if not IDEOGRAM_API_KEY:
        print("  ⚠️  Chybí IDEOGRAM_API_KEY v .env — generuji tmavý placeholder")
        return Image.new("RGB", IMAGE_SIZE, (32, 30, 28))

    print(f"  Volám Ideogram API...")
    resp = requests.post(
        IDEOGRAM_URL,
        headers={"Api-Key": IDEOGRAM_API_KEY, "Content-Type": "application/json"},
        json={
            "prompt": prompt,
            "aspect_ratio": "16x9",
            "rendering_speed": "DEFAULT",
            "magic_prompt": "OFF",
            "negative_prompt": _NEGATIVE,
            "num_images": 1,
            "style_type": "REALISTIC",
        },
        timeout=120,
    )
    resp.raise_for_status()
    img_bytes = requests.get(resp.json()["data"][0]["url"], timeout=60).content
    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    return img.resize(IMAGE_SIZE, Image.LANCZOS)


# ═══════════════════════════════════════════════════════════════
#  OVERLAY — o něco tmavší než dřív, text musí být čitelný
# ═══════════════════════════════════════════════════════════════

def apply_overlay(img: Image.Image) -> tuple:
    stat = ImageStat.Stat(img)
    brightness = sum(stat.mean[:3]) / 3
    if brightness > 160:
        opacity = 0.68
    elif brightness >= 100:
        opacity = 0.60
    else:
        opacity = 0.48
    overlay    = Image.new("RGB", img.size, (0, 0, 0))
    composited = Image.blend(img, overlay, opacity)
    return composited, brightness, opacity


# ═══════════════════════════════════════════════════════════════
#  LOGO
# ═══════════════════════════════════════════════════════════════

def load_logo():
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        data = logo.getdata()
        logo.putdata([
            (r, g, b, 0) if r > 240 and g > 240 and b > 240 else (r, g, b, a)
            for r, g, b, a in data
        ])
        ratio = LOGO_WIDTH / logo.width
        return logo.resize((LOGO_WIDTH, int(logo.height * ratio)), Image.LANCZOS)
    except (OSError, FileNotFoundError):
        print(f"  ⚠️  Logo nenalezeno: {LOGO_PATH}")
        return None


def place_logo(img: Image.Image, logo) -> Image.Image:
    if logo is None:
        return img
    result = img.convert("RGBA")
    result.paste(logo, (IMAGE_SIZE[0] - logo.width - PAD, PAD), logo)
    return result.convert("RGB")


# ═══════════════════════════════════════════════════════════════
#  TITULEK — auto-wrap + auto-size
# ═══════════════════════════════════════════════════════════════

MAX_TITLE_WIDTH = int(IMAGE_SIZE[0] * 0.58)  # titulek zabírá max 58% šířky (levá polovina)
MAX_FONT_SIZE   = 130
MIN_FONT_SIZE   = 52


def _wrap_title(draw, title: str, font) -> list[str]:
    """Rozdělí titulek na řádky tak, aby se vešel do MAX_TITLE_WIDTH."""
    words = title.split()
    lines, current = [], []
    for word in words:
        test = " ".join(current + [word])
        if draw.textlength(test.upper(), font=font) <= MAX_TITLE_WIDTH:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines[:4]  # max 4 řádky


def _auto_size_title(draw, title: str) -> tuple:
    """Najde největší font, při kterém se všechna slova vejdou."""
    for size in range(MAX_FONT_SIZE, MIN_FONT_SIZE - 1, -4):
        font  = load_bebas(size)
        lines = _wrap_title(draw, title, font)
        if all(draw.textlength(l.upper(), font=font) <= MAX_TITLE_WIDTH for l in lines):
            return font, lines, size
    font  = load_bebas(MIN_FONT_SIZE)
    return font, _wrap_title(draw, title, font), MIN_FONT_SIZE


def draw_spaced_text(draw, pos, text, font, fill, gap=LABEL_GAP):
    x, y = pos
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        x += draw.textlength(char, font=font) + gap


# ═══════════════════════════════════════════════════════════════
#  KOMPOZICE
# ═══════════════════════════════════════════════════════════════

def render_blog_hero(base_img: Image.Image, title: str,
                     category: str, logo) -> Image.Image:
    """
    Layout (vlevo dole, směrem nahoru):
      [metadata strip]
      [KATEGORIE  spaced caps warm accent]
      [── divider line ──]
      [TITULEK ČLÁNKU  Bebas Neue cream  2–3 řádky auto-sized]
    Logo: vpravo nahoře.
    """
    img  = base_img.copy().convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    # ── Metadata strip (úplně dole) ──
    font_meta = load_dm_light(18)
    meta_y    = IMAGE_SIZE[1] - PAD + 4
    brand_w   = draw.textlength("CYRCID.COM", font=font_meta)
    draw.text((IMAGE_SIZE[0] - PAD - brand_w, meta_y),
              "CYRCID.COM", font=font_meta, fill=(*COLOR_CREAM, 55))

    # ── Kategorie (nad titulkem) ──
    font_cat = load_dm_light(22)
    # pozici kategorie spočítáme zpětně od spodního okraje

    # ── Titulek — auto-size ──
    font_title, lines, font_size = _auto_size_title(draw, title)
    line_h    = int(font_size * 0.88)          # tight leading (stejně jako create_post.py)
    total_h   = len(lines) * line_h
    meta_zone = 52                              # prostor pro metadata strip
    title_bottom = IMAGE_SIZE[1] - PAD - meta_zone
    title_top    = title_bottom - total_h

    # Vykresli řádky titulku
    y = title_top
    for i, line in enumerate(lines):
        fill = (*COLOR_CREAM, 245) if i == 0 else (*COLOR_WARM_ACCENT, 230)
        draw.text((PAD, y), line.upper(), font=font_title, fill=fill)
        y += line_h

    # ── Divider ──
    div_y   = title_top - 20
    div_len = int(IMAGE_SIZE[0] * 0.10)
    draw.line([(PAD, div_y), (PAD + div_len, div_y)],
              fill=(255, 255, 255, 65), width=1)

    # ── Kategorie ──
    cat_y = div_y - 22 - 16
    draw_spaced_text(draw, (PAD, cat_y), category.upper(),
                     font_cat, (*COLOR_WARM_ACCENT, 160))

    # ── Logo ──
    result = Image.alpha_composite(
        img, Image.new("RGBA", IMAGE_SIZE, (0, 0, 0, 0))
    ).convert("RGB")
    return place_logo(result, logo)


# ═══════════════════════════════════════════════════════════════
#  HLAVNÍ FUNKCE
# ═══════════════════════════════════════════════════════════════

def generate_blog_image(title: str, category: str = "DPP",
                        excerpt: str = "", title_cs: str = "") -> str:
    print(f"\n🖼  Generuji hero image...")
    print(f"   Článek: {title[:70]}")

    slug     = re.sub(r'[^a-z0-9]+', '-', title.lower())[:50].strip('-')
    prompt   = build_blog_prompt(title, category, excerpt)
    bg       = generate_background(prompt)
    comp, brightness, opacity = apply_overlay(bg)
    print(f"   Brightness: {brightness:.0f} → overlay: {opacity:.0%}")

    logo  = load_logo()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    from datetime import date

    # EN verze
    final_en = render_blog_hero(comp, title, category, logo)
    filepath_en = os.path.join(OUTPUT_DIR, f"blog_{date.today()}_{slug}.jpg")
    final_en.save(filepath_en, "JPEG", quality=92, optimize=True)
    print(f"   ✅ EN uloženo: {filepath_en}")

    # CS verze (pokud je zadán český titulek)
    filepath_cs = None
    if title_cs:
        final_cs = render_blog_hero(comp, title_cs, category, logo)
        filepath_cs = os.path.join(OUTPUT_DIR, f"blog_{date.today()}_{slug}_cs.jpg")
        final_cs.save(filepath_cs, "JPEG", quality=92, optimize=True)
        print(f"   ✅ CS uloženo: {filepath_cs}")

    return filepath_en if not filepath_cs else f"{filepath_en}\n{filepath_cs}"


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description="Blog Hero Image Generator")
    p.add_argument("--title",    required=True, help="Anglický titulek článku")
    p.add_argument("--title-cs", default="",    help="Český titulek článku (generuje druhou verzi obrázku)")
    p.add_argument("--category", default="DPP")
    p.add_argument("--excerpt",  default="")
    args = p.parse_args()
    path = generate_blog_image(args.title, args.category, args.excerpt, args.title_cs)
    print(f"\n{'='*60}")
    print(f"  Hotovo: {path}")
    print(f"  Nahraj do Cyrcid Adminu → Featured Image")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
