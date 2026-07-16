# Repository Guidelines

This repository is a Hugo static site for `j1nn0.com` using the PaperMod theme, deployed on Cloudflare Pages. Posts live in `content/posts/`, site configuration in `hugo.yaml`.

## Entry Point: blog-ops Skill

All work in this repository — discussing article ideas, writing or editing posts, publishing, tags, metadata, layout, configuration — starts with the `blog-ops` skill. It routes each stage to the right skill (`grilling` / `grill-me` for idea vetting, `blog-writing-guide-ja` + `writing-ja` for writing) and defines the default conventions: new post setup, pre-publish validation, tag taxonomy, coding style, scope control, and commit guidelines.

If your environment does not load skills automatically, read `.agents/skills/blog-ops/SKILL.md` directly and follow its routing.

## Repo-Specific Facts

This repository follows the blog-ops defaults as-is. Site-specific facts:

- Redirects: `static/_redirects` in Cloudflare Pages format (301 lines).
- Custom CSS: `assets/css/extended/custom.css`.
- Theme overrides: `layouts/partials/extend_head.html` and `extend_footer.html`.

## Build Commands

- `hugo server -D` — local dev server including drafts
- `hugo --minify` — release-style build check

## Hard Constraints

These apply even before any skill is loaded:

- Make only the changes required by the request. Preserve the author's factual claims, experience, opinions, and uncertainty.
- Do not rename files, slugs, tags, or generated URLs without reporting the impact.
- Do not modify `themes/PaperMod` directly when a site-side override can achieve the same result.
- Do not commit `public/`, secrets, or deployment tokens.
