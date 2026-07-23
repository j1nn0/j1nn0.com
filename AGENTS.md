# Repository Guidelines

This repository is a Hugo static site for `j1nn0.com` using the PaperMod theme, deployed on Cloudflare Pages. Posts live in `content/posts/`, site configuration in `hugo.yaml`.

## Entry Point: blog-ops Skill

All work in this repository — discussing article ideas, writing or editing posts, publishing, tags, metadata, layout, configuration — starts with the `blog-ops` skill. It routes each stage to the right skill (`grilling` / `grill-me` for idea vetting, `blog-writing-guide-ja` + `writing-ja` for writing) and defines the default conventions: new post setup, pre-publish validation, tag taxonomy, coding style, scope control, and commit guidelines.

If your environment does not load skills automatically, read `.agents/skills/blog-ops/SKILL.md` directly and follow its routing.

## Repo-Specific Facts

This repository follows the blog-ops defaults as-is. Site-specific facts:

- Redirects: `static/_redirects` in Cloudflare Pages format (301 lines).
- Custom CSS: `assets/css/extended/custom.css`.
- Custom homepage: `layouts/index.html` (Hallmark hero + post list; no theme equivalent). Section/tag/archive listings still use the theme-derived `layouts/_default/list.html`.
- Theme overrides span `layouts/partials/`, `layouts/partials/templates/`, `layouts/_default/`, and `layouts/_default/_markup/`. Every overriding file has a header comment explaining why it diverges from `themes/PaperMod` — read that comment before touching one. Notable overrides: `header.html` (Hallmark nav, replaces theme's logo/lang-switcher header), `extend_footer.html` (the site's real visible footer + GLightbox init; the theme's own `footer.html` is kept unmodified for its scripts but hidden via CSS), `templates/opengraph.html`/`templates/twitter_cards.html` (`defaultImage` fallback + this site's flat `twitter`/`cover.image` params), `share_icons.html` (adds Bluesky and Hatena Bookmark buttons the theme doesn't ship).
- Images: `static/images/<slug>/ogp.png` (+ `.svg` source) is also mounted at `assets/images` via `hugo.yaml`'s `module.mounts`, so Hugo can generate responsive `cover.image`/`images:` srcset without duplicating files. Set `cover.image` without a leading `/` (e.g. `images/<slug>/ogp.png`) so the path matches the mounted resource; the OGP-only `images:` list keeps a leading `/`. OGP images must not break the overall web design's tone — match the site's visual language and the theme/content of the specific article.

## Build Commands

- `hugo server -D` — local dev server including drafts
- `hugo --minify` — release-style build check
- OGP/Twitter/schema meta tags and the theme's footer scripts only render when `hugo.IsProduction` is true; add `--environment production` (or `-D --environment production` for drafts) to inspect them locally.

## Hard Constraints

These apply even before any skill is loaded:

- Make only the changes required by the request. Preserve the author's factual claims, experience, opinions, and uncertainty.
- Do not rename files, slugs, tags, or generated URLs without reporting the impact.
- Do not modify `themes/PaperMod` directly when a site-side override can achieve the same result.
- Do not commit `public/`, secrets, or deployment tokens.
