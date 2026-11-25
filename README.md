# zollo.net

Source for [www.zollo.net](https://www.zollo.net), Joe Zollo's personal site: career, open-source
projects and homelab. A small Python script turns YAML content and Jinja templates into plain
static files, so it can be hosted anywhere. It's deployed on Cloudflare Pages.

## Editing content

Everything you'd normally want to change is in `content/`:

| File | What's in it |
|---|---|
| `content/profile.yaml` | Name, tagline, contact links, about text, stats, talks, awards |
| `content/experience.yaml` | Jobs, newest first (education is intentionally left out) |
| `content/projects.yaml` | Open-source project cards. Add `live: https://…` to show a "try it" link |
| `content/homelab.yaml` | The homelab rack and highlights. **Architecture level only** (see below) |
| `content/skills.yaml` | Skill groups and certifications |

Photos are in `assets/photos/`. The build resizes them to WebP and JPEG at several widths and
makes the social preview card (`img/og-card.jpg`).

Markup is in `templates/` (`index.html`, `404.html`, `base.html`), styles in `static/css/site.css`,
and the small amount of JavaScript (theme toggle, typing effect, the contact terminal) in
`static/js/site.js`. CSS and JS get a content hash in their file names at build time.

## Building

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python build.py            # writes dist/
python build.py --serve    # builds and serves on http://localhost:8000
python -m pytest -q        # builds into a temp folder and checks the output
```

The tests check that every project is listed, that local links and images resolve, that the CSP
in `_headers` covers the inline script, and that nothing sensitive leaks into the HTML: private IP
addresses, internal host names and domains, VLAN/VPN details, account names or the phone number.
Keep the homelab section to architecture and tooling; if a test fails, reword the content rather
than loosening the test.

## Deploying on Cloudflare Pages

Connect this repository in the Cloudflare dashboard (Workers & Pages → Create → Pages → Connect to
Git) with these settings:

| Setting | Value |
|---|---|
| Production branch | `main` |
| Framework preset | None |
| Build command | `pip install -r requirements.txt && python build.py` |
| Build output directory | `dist` |
| Environment variable | `PYTHON_VERSION` = `3.12` (also pinned in `.python-version`) |

Every push to `main` deploys production; pull requests get preview URLs. Then add the custom
domains `zollo.net` and `www.zollo.net` under the project's **Custom domains** tab.

The build writes a Cloudflare `_headers` file into `dist/` with security headers (HSTS, CSP,
`nosniff`, `Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy`) and long cache lifetimes for
the hashed CSS and JS. The CSP is generated from the templates, so it stays in step with the inline
theme script. `404.html` is served automatically by Pages for unknown paths.

Fonts (Inter, JetBrains Mono) load from Google Fonts; everything else is served from the site
itself. There are no analytics, trackers or cookies.
