# Repository Guidelines

## Project Structure & Module Organization

This repository is a Hugo static site for `j1nn0.com` using the PaperMod theme. Site configuration lives in `hugo.yaml`. Content belongs under `content/`, with posts expected in `content/posts/` as Markdown files. Theme overrides and custom templates live in `layouts/partials/`, including `extend_head.html` and `extend_footer.html`. Custom styling is in `assets/css/extended/custom.css`. Static files that should be copied as-is, such as Open Graph images, belong in `static/images/`. The upstream theme is stored in `themes/PaperMod`; avoid editing it directly unless intentionally updating the vendored theme.

## Build, Test, and Development Commands

- `hugo server -D`: run the local development server and include draft content.
- `hugo`: build the production site into `public/`.
- `hugo --minify`: build with minified output for a release-style check.
- `hugo --cleanDestinationDir`: remove stale generated files during a build.

There is no `package.json` workflow in this repository, so do not assume `npm test`, `npm run build`, or frontend package tooling exists.

## Coding Style & Naming Conventions

Use two-space indentation in YAML, HTML, and CSS to match the existing small-file style. Keep Hugo front matter concise and valid YAML. Prefer lowercase, hyphenated slugs for content filenames, for example `content/posts/my-post.md`. Keep custom CSS scoped and readable in `assets/css/extended/custom.css`; avoid broad theme rewrites when a small override is enough.

## Tag Taxonomy

Tags are reader-facing, cross-post navigation, not an index of every technology mentioned in an article. Use three to five tags per post, with broad themes first and products or technologies that are the article's main subject after them. Use lowercase, underscore-separated values in front matter, such as `ai_agent`, `cloudflare_pages`, and `machine_learning`. This keeps shared tags stable and lets PaperMod remove whitespace before passing tags to social-network hashtag URLs.

Tag names determine Hugo's generated term URLs. Do not add redirects merely for a tag rename; first identify the changed term URLs and confirm the desired redirect strategy. When removing a tag, do not redirect it unless there is an unambiguous successor.

Define reader-facing tag names in `content/tags/<internal_value>/_index.md` with a `title`. Keep the article front matter values unchanged for this purpose. PaperMod uses the term title in tag pages and post footers, while its X sharing template uses the article's internal tag values.

## Testing Guidelines

There is no dedicated automated test suite. Validate changes by running `hugo` before committing. For content changes, run `hugo server -D` and inspect the page locally. For metadata, social card, or asset changes, verify the generated HTML in `public/` or the browser output and confirm images resolve from `static/images/`.

## Commit Guidelines

Use Conventional Commits format in English. Keep the subject line under 72 characters.

## Security & Configuration Tips

Do not commit local secrets, deployment tokens, or generated credentials. Keep canonical site settings in `hugo.yaml`, and check production URLs carefully when editing `baseURL`, Open Graph, Twitter card, or language configuration.

## Blog Writing Skills

The writing rules for all posts under `content/posts/` live entirely in the skills below. Do not duplicate those rules here; if AGENTS.md and a skill conflict, the skill wins.

| Skill | Purpose |
|-------|---------|
| `blog-writing-guide-ja` | Article planning, structure, headings/titles, SEO, quality bar, and pre-publish review for Japanese tech blog posts |
| `writing-ja` | Sentence-level style: da/de-aru tone, one sentence per line, banned phrases, AI-ish prose removal, and grep-based verification. Standalone merge of `japanese-tech-writing`, `human-writing-ja`, and `humanizer-ja`, resolved against this site's published posts |

Never use `japanese-tech-writing`, `human-writing-ja`, or `humanizer-ja` directly; always use `writing-ja` instead.

Typical workflows:

- "Plan the structure of a technical blog post" → `blog-writing-guide-ja`
- "Write or polish a blog post in Japanese" → `blog-writing-guide-ja` + `writing-ja`
