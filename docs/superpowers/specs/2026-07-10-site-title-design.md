# Spec: Site Title Change to "j1nn0 lab"

## Goal
Change the site title from "j1nn0 note" to "j1nn0 lab" to better reflect the blog's theme of experimentation, hands-on tutorials, and custom development setups. Update all configuration, homepage layout titles, and the default OGP social images.

## Affected Components

1. **`hugo.yaml`**
   - Change site-wide title to `j1nn0 lab`.
   - Change `params.homeInfoParams.Title` to `"j1nn0 lab"`.

2. **`static/images/ogp-default.svg`**
   - Update `<title>` element text.
   - Update `<desc>` element text.
   - Update the rendered text block `<text>` displaying the title from `j1nn0 note` to `j1nn0 lab`.

3. **`static/images/ogp-default.png`**
   - Re-generate `ogp-default.png` (1200x630px) from `ogp-default.svg` using Chromium screenshot to ensure correct rendering.

## Verification
- Build the site via `hugo --minify` to ensure no YAML or template build errors.
- Verify generated `public/index.html` title tag is `<title>j1nn0 lab</title>`.
- Verify homepage card title in `public/index.html` is `<h1>j1nn0 lab</h1>`.
- Open generated OGP image and verify title text says "j1nn0 lab".
