# Repository Guidelines

## Project Structure & Module Organization

This repository is a Hugo static site for `j1nn0.com` using the PaperMod theme. Site configuration lives in `hugo.yaml`. Content belongs under `content/`, with posts expected in `content/posts/` as Markdown files. Theme overrides and custom templates live in `layouts/partials/`, including `extend_head.html` and `extend_footer.html`. Custom styling is in `assets/css/extended/custom.css`. Static files that should be copied as-is, such as Open Graph images, belong in `static/images/`. The upstream theme is stored in `themes/PaperMod`; avoid editing it directly unless intentionally updating the vendored theme.

## Instruction Precedence

- Repository structure, commands, Hugo and PaperMod implementation, front matter, taxonomy, assets, URLs, SNS integration, and validation rules in this file take precedence over skills.
- `blog-writing-guide-ja` takes precedence for Japanese technical blog article planning, structure, titles, headings, introductions, conclusions, SEO considerations, and article-level editorial review.
- `writing-ja` takes precedence for Japanese sentence-level style, wording, rhythm, and formatting.
- When the writing skills overlap, `writing-ja` takes precedence only for sentence-level style and formatting.
- Skills must not override repository-specific technical constraints.

## Build, Test, and Development Commands

- `hugo server -D`: run the local development server and include draft content.
- `hugo`: build the production site into `public/`.
- `hugo --minify`: build with minified output for a release-style check.
- `hugo --cleanDestinationDir`: remove stale generated files during a build.

There is no `package.json` workflow in this repository, so do not assume `npm test`, `npm run build`, or frontend package tooling exists.

## Coding Style & Naming Conventions

Use two-space indentation in YAML, HTML, and CSS to match the existing small-file style. Keep Hugo front matter concise and valid YAML. Prefer lowercase, hyphenated slugs for content filenames, for example `content/posts/my-post.md`. Keep custom CSS scoped and readable in `assets/css/extended/custom.css`; avoid broad theme rewrites when a small override is enough.

## Tag Taxonomy

Tags are reader-facing, cross-post navigation, not an index of every technology mentioned in an article. Use three to five tags per post, with broad themes first and products or technologies that are the article's main subject after them. Use lowercase, underscore-separated values in front matter, such as `ai_agents`, `cloudflare_pages`, and `machine_learning`. Do not use hyphens or spaces. This keeps shared tags stable and lets PaperMod remove whitespace before passing tags to social-network hashtag URLs.

Tag names determine Hugo's generated term URLs. Do not add redirects merely for a tag rename; first identify the changed term URLs and confirm the desired redirect strategy. When removing a tag, do not redirect it unless there is an unambiguous successor.

Define reader-facing tag names in `content/tags/<internal_value>/_index.md` with a `title`. Keep the article front matter values unchanged for this purpose. PaperMod uses the term title in tag pages and post footers, while its X sharing template uses the article's internal tag values.

## Scope Control

- Make only the changes required by the request.
- Do not rewrite unrelated articles only to satisfy writing skills.
- Do not rename content files, slugs, tags, taxonomies, or generated URLs without reporting the impact.
- Preserve the author's factual claims, personal experience, opinions, and uncertainty.
- Do not invent tests, results, motivations, usage history, failures, or reasons for choosing a tool.
- Do not turn assumptions into confirmed facts.
- When updating a potentially time-sensitive factual statement, verify it from a primary source.
- Do not make broad formatting changes outside the requested files.
- Do not modify the theme submodule directly when an override in the site repository can achieve the same result.

## Validation by Change Type

Run the checks relevant to the change. There is no dedicated automated test suite.

### Any change

- Run `hugo --minify`.
- Confirm that the build has no errors or unexpected warnings.
- Do not commit `public/` unless it is intentionally tracked by the repository.

### Content changes

- Inspect the affected page with `hugo server -D`.
- Confirm headings, code blocks, links, tables, and article metadata.

### Front matter changes

- Confirm the title, date, summary, tags, draft status, and generated URL.
- Confirm that the YAML is valid.

### Tag changes

- Confirm that the internal tag value uses lowercase and underscores.
- Confirm the reader-facing label in `content/tags/<internal_value>/_index.md`.
- Confirm the post-footer label, terms-page label, generated tag URL, and SNS sharing value.
- Confirm that SNS sharing uses the internal underscore-separated value, not the display label.
- Confirm that no duplicate or orphaned tag pages were introduced.

### Summary or description changes

- Confirm that the home page and posts list do not expose unintended body content.
- Confirm that metadata uses the intended summary or description.

### OGP or metadata changes

- Inspect the generated HTML under `public/`.
- Confirm the title, description, canonical URL, Open Graph, and X/Twitter metadata.

### Layout or CSS changes

Inspect at least the home page, a post page, the posts list, the tags list, an individual tag page, and the About page in desktop and mobile layouts.

### URL-affecting changes

- List the affected old and new URLs.
- Add or recommend redirects.
- Confirm internal links and canonical URLs.

## Commit Guidelines

Use Conventional Commits format in English. Keep the subject line under 72 characters.

## Security & Configuration Tips

Do not commit local secrets, deployment tokens, or generated credentials. Keep canonical site settings in `hugo.yaml`, and check production URLs carefully when editing `baseURL`, Open Graph, Twitter card, or language configuration.

## Blog Writing Skills

Use the relevant skills for writing work while keeping repository-specific constraints in this file.

| Skill | Purpose |
|-------|---------|
| `blog-writing-guide-ja` | Japanese technical blog article planning, structure, titles and headings, SEO judgment, and article-level review |
| `writing-ja` | Japanese sentence-level style, wording, rhythm, formatting, and paragraph-level revision |

Never use `japanese-tech-writing`, `human-writing-ja`, or `humanizer-ja` directly; always use `writing-ja` instead.

Typical workflows:

- "Plan the structure of a technical blog post" → `blog-writing-guide-ja`
- "Write or polish a blog post in Japanese" → `blog-writing-guide-ja` + `writing-ja`
