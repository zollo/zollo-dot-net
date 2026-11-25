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

The site is a Cloudflare Pages **direct-upload** project named `zollo-dot-net`, deployed by
GitHub Actions (`.github/workflows/deploy.yml`), not by Cloudflare's Git integration:

- **Push to `main`** (or run the workflow by hand): runs the tests, builds `dist/`, and runs
  `wrangler pages deploy dist --project-name=zollo-dot-net --branch=main` (production).
- **Pull requests** from this repository get a preview deployment on their branch name. PRs from
  forks are skipped, since they don't get the secrets.

It needs two repository secrets: `CLOUDFLARE_API_TOKEN` (a token with *Cloudflare Pages: Edit*)
and `CLOUDFLARE_ACCOUNT_ID`. Custom domains (`zollo.net`, `www.zollo.net`) are set on the Pages
project in the Cloudflare dashboard.

To build it the same way locally: `pip install -r requirements.txt && python build.py`, output in
`dist/`, Python 3.12.

The build writes a Cloudflare `_headers` file into `dist/` with security headers (HSTS, CSP,
`nosniff`, `Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy`) and long cache lifetimes for
the hashed CSS and JS. The CSP is generated from the templates, so it stays in step with the inline
theme script. `404.html` is served automatically by Pages for unknown paths.

Fonts (Inter, JetBrains Mono) load from Google Fonts; everything else is served from the site
itself. There are no analytics, trackers or cookies.
