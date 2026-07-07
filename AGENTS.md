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

## Testing Guidelines

There is no dedicated automated test suite. Validate changes by running `hugo` before committing. For content changes, run `hugo server -D` and inspect the page locally. For metadata, social card, or asset changes, verify the generated HTML in `public/` or the browser output and confirm images resolve from `static/images/`.

## Commit & Pull Request Guidelines

Recent commits use short, imperative subjects such as `Fix meta`, `Improve css`, and `Update PaperMod theme to latest version`. Follow that style: keep the first line direct and under about 72 characters. Pull requests should explain the user-visible change, list validation performed, link any related issue, and include screenshots when visual layout, typography, images, or metadata previews change.

## Blog Writing Style Guidelines

Write all blog posts (Markdown files under `content/posts/`) matching the repository's writing style. The complete ruleset, including argumentation rules, the banned-phrase list, and grep-based verification, lives in the `writing-ja` skill; use that skill when writing or polishing posts. The essentials:

Formatting:

- Sentence endings: plain/declarative form ("だ/である" style), mixed with 体言止め and light colloquial phrases. Never polite form ("です/ます" style).
- One sentence per line (一文一行). Separate paragraphs with an empty line. Keep each paragraph under 240 characters.
- No bold markdown syntax (`**`) anywhere in the body, lists, quotes, headings, or labels. Use ■ for labels and ※ for notes.
- No colons (`:` or `：`) to end headings, sentences, quotes, or labels.
- No em dashes (— or ——), no emoji, no exclamation marks.
- No middle dots (`・`) for parallel word lists; use `と` or `や` instead.
- Tag format: underscores (`_`) as word separators in front matter `tags`, never hyphens. For example, `machine_learning` instead of `machine-learning`. Hyphens break hashtag recognition on social platforms like X (Twitter).

Structure and voice:

- Titles state the outcome or change, often in the "〜した話" pattern. Numbers and product names are welcome.
- No "はじめに", "おわりに", or "まとめ" headings. Sentence-style headings that state the section's conclusion are preferred; avoid paper-style headings like "〜における課題".
- Post shape: personal problem/trigger → solution overview (table or flow list) → details with the reason behind each choice → what changed after adopting it, closing with a short personal note.
- First person is 「自分」, not 「筆者」 or 「私」.
- Include at least one honest personal remark or reservation. Put a one-sentence lead-in before each code block. Write screenshot alt text in Japanese describing the screen.
- Avoid AI-ish stock phrases (「〜することができます」「〜と言えるでしょう」「重要なのは〜」, and repeated 「実現した」「堅牢な」「大幅に」). The `writing-ja` skill has the full banned list and grep checks.

## Security & Configuration Tips

Do not commit local secrets, deployment tokens, or generated credentials. Keep canonical site settings in `hugo.yaml`, and check production URLs carefully when editing `baseURL`, Open Graph, Twitter card, or language configuration.

## Blog Writing Skills

The primary skill for writing and polishing posts is `writing-ja`. It is standalone: it merges `japanese-tech-writing`, `human-writing-ja`, and `humanizer-ja`, with conflicts between them resolved against this site's published posts, and includes grep-based verification steps. Prefer it over combining the three source skills manually.

Other available writing skills:

| Skill | Purpose |
|-------|---------|
| `edit-article` | Article structure, editing, and revision (mattpocock/skills) |
| `content-strategy` | Content strategy and topic planning (coreyhaines31/marketingskills) |
| `copywriting` | Sales copy, CTAs, and headlines (coreyhaines31/marketingskills) |
| `blog-writing-guide` | Blog writing style guide (getsentry/skills) |

Typical workflows:

- "Plan the structure of a technical blog post" → `edit-article` + `content-strategy`
- "Write or polish a blog post in Japanese" → `writing-ja`
- "Write blog post headlines and CTAs" → `copywriting`

