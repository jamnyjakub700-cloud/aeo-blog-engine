# AEO Blog Engine

Toolkit for creating blog articles optimized for Answer Engine Optimization (AEO) — making your content discoverable by AI-powered search engines like ChatGPT, Perplexity, and Google AI Overviews.

## What's inside

### 1. AEO Methodology (`aeo-methodology.md`)

A structured, battle-tested writing framework for LLM-generated articles that rank in AI answer engines. Use it as a system prompt for Claude, GPT, or any LLM. Covers:

- Answer-first paragraph structure
- Question-based heading hierarchy
- Highlight boxes for AI extraction
- FAQ section design
- Mid-article CTA placement
- Internal link and deduplication strategy
- Meta description optimization

### 2. Hero Image Generator (`generate_blog_image.py`)

Generates branded blog hero images (1920x1080) using AI-generated backgrounds + text overlay:

- **Ideogram API** for AI background generation with category-based prompt rotation
- **Adaptive overlay** — measures image brightness and adjusts dark overlay opacity for guaranteed text readability
- **Auto-sizing title** — binary-search font fitting (130px → 52px) with word wrapping
- **Deterministic prompts** — `md5(title) % variants` ensures same title always produces same image
- **Brand identity** — logo, custom fonts, color palette

### 3. CMS Publisher (`publish.py`)

Publishes markdown articles with YAML frontmatter to any REST API blog:

- YAML frontmatter parser (no PyYAML dependency)
- Slugify with diacritics removal (Czech, German, French, etc.)
- Auto-calculated read time
- API schema auto-detection (tries content/body/text fields)
- Author/category resolution by name

### 4. Article Template (`article_template.md`)

Ready-to-use markdown template following the AEO methodology. Shows the exact structure: intro with data hook, question-based sections, highlight boxes, comparison table, mid-article CTA, FAQ, and 3-step closing.

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/aeo-blog-engine.git
cd aeo-blog-engine

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your API keys and paths
```

## Usage

### Generate a hero image

```bash
python generate_blog_image.py \
  --title "How to Prepare for ESPR Compliance" \
  --category "regulation" \
  --excerpt "From 2028, every textile product sold in the EU..."
```

### Publish an article

```bash
python publish.py articles/2026-05-15-your-article-en.md
```

### Use the AEO methodology with an LLM

Copy `aeo-methodology.md` into your LLM's system prompt. Then ask it to write an article following the framework. The methodology works with any LLM and any topic.

## Customization

### Image prompts

The image generator uses category-based Ideogram prompts defined in `_KEYWORD_MAP` and `_PROMPT_VARIANTS` inside `generate_blog_image.py`. To customize for your industry:

1. Define your categories in `_KEYWORD_MAP` (keyword → category mapping)
2. Write 4-5 prompt variants per category in `_PROMPT_VARIANTS`
3. The generator deterministically selects variants based on title hash

### Brand identity

Set via environment variables or edit the CONFIG section:
- `LOGO_PATH` — your brand logo (PNG with transparency)
- `FONTS_DIR` — directory with your TTF/OTF fonts
- Color constants in the script (`COLOR_CREAM`, `COLOR_WARM_ACCENT`, etc.)

### CMS integration

`publish.py` works with any REST API that accepts JSON POST. Configure:
- `BLOG_API_BASE` — your API base URL
- `BLOG_API_TOKEN` — authentication token
- The script auto-detects the content field name (content/body/text/html_content)

## Why AEO matters

Traditional SEO optimizes for PageRank and SERP positions. But with ChatGPT, Perplexity, and Google AI Overviews now answering queries directly, your content needs to be structured so AI models can:

- **Extract** specific answers from your sections
- **Cite** your page as a source
- **Surface** your content in generated responses

The AEO methodology in this toolkit is based on production use across 15+ published articles with measured AI search visibility improvements.

## License

MIT
