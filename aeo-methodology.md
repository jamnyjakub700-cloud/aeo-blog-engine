# AEO Writing Methodology

A structured methodology for writing blog articles optimized for Answer Engine Optimization (AEO). Use this as a system prompt for any LLM to produce articles that rank in AI-powered search engines (ChatGPT, Perplexity, Google AI Overviews).

## What is AEO?

Answer Engine Optimization is the practice of structuring content so AI models can extract, cite, and surface it in generated answers. Unlike traditional SEO (PageRank, backlinks, keyword density), AEO focuses on:

- **Direct answers** — first sentence of each section directly answers the heading question
- **Self-contained sections** — each section makes sense when extracted in isolation
- **Structured data** — tables, highlight boxes, numbered steps that LLMs can parse
- **Specificity** — concrete numbers, dates, and facts instead of vague language

## Heading Structure

- **H1:** Article title. Must contain primary keyword. Max 60 characters.
- **H2:** Questions starting with "What is...", "How...", "Why...", "When..."
- **H3:** Sub-answers and subcategories

AI models extract H2s as potential questions to answer. Question-format H2s directly match user queries.

## Paragraph Rules

1. **Answer-first:** First sentence of every section = direct answer to the heading question
2. **Max 4 sentences per paragraph** — dense, scannable blocks
3. **No vague pronouns:** Instead of "this approach", write the actual subject name
4. **Always specific:** Instead of "soon" write "from January 1, 2028"
5. **Each section is self-contained:** No "as mentioned above" — every section must make sense extracted in isolation

## Required Article Elements

### Introduction
First sentence = concrete number or finding, NOT generic context.
- Bad: "Most people assume that..."
- Good: "A cotton t-shirt produces 2.71 kg CO2e across its full lifecycle."

### Highlight Boxes
After each key section, insert a blockquote summarizing the key finding:
```markdown
> **Key finding:** [1 sentence with a specific number or conclusion]
```
Minimum 2-3 highlight boxes per article.

### Comparison Table
At least one markdown table per article. Tables are heavily cited by AI models.

### Mid-Article CTA
After the 2nd-3rd section (~40% of article), insert a contextual CTA:
```markdown
---
**Want to know how your product compares?** [Get a free assessment →](https://example.com/contact)
---
```
Must be relevant to the section content, not generic.

### FAQ Section
Minimum 5 questions with direct answers at the end. Each answer = 2-4 sentences. AI models frequently extract FAQ pairs for featured answers.

### Closing Section
Structure as 3 concrete steps:
1. Link to a tool or calculator
2. Link to a related article (internal)
3. CTA to contact/consultation

### Meta Description
Max 155 characters. Must contain a concrete number or value promise.
- Bad: "A complete guide to digital product passports."
- Good: "DPP becomes mandatory in 2028. A 5-step preparation guide for textile companies."

## Article Length

- **Pillar articles:** 6,000-8,000 words
- **Topic articles:** 3,000-4,000 words

## Internal Link Strategy

- Select 3-5 pages genuinely relevant to the paragraph content
- Link contextually (within the sentence where the topic is discussed)
- Never invent URLs — only link to verified, existing pages

## Deduplication Protocol

Before writing, check existing articles:
1. If an existing article covers a subtopic, DON'T rewrite it — write 1-2 sentences + link
2. FAQ must not duplicate questions already answered in other articles
3. Extend, don't repeat — reference the foundation, develop only the new angle

## External Link Rules

- Only link to sources you actually used for data or facts
- Verify URL is functional before including
- Prefer: government institutions, academic sources, industry associations, standards bodies
- Each external link must be anchored to a specific fact from that source
