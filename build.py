#!/usr/bin/env python3
"""Build zollo.net into a folder of static files.

    python build.py              # writes dist/
    python build.py --serve      # builds, then serves dist/ on http://localhost:8000

Content lives in content/*.yaml, markup in templates/, CSS and JS in static/,
source photos in assets/photos/. The output is plain HTML/CSS/JS/images and
can be hosted anywhere that serves static files.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import functools
import hashlib
import http.server
import re
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
PHOTOS = ROOT / "assets" / "photos"

# name -> (source file, widths to generate, crop aspect (w/h) or None)
IMAGES = {
    "headshot": ("headshot.jpg", (160, 320, 640), 1.0),
    "full_body": ("full_body.jpg", (480, 800, 1200), None),
}


def load_content() -> dict:
    data = {}
    for path in sorted(CONTENT.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            data[path.stem] = yaml.safe_load(fh)
    return data


def short_hash(text: str) -> str:
    """A stable, git-looking 7 character hash, used as decoration on the timeline."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:7]


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


def build_images(out: Path) -> dict:
    """Resize each photo to several widths, as WebP and JPEG. Returns template metadata."""
    img_dir = out / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, (src_name, widths, aspect) in IMAGES.items():
        src = Image.open(PHOTOS / src_name)
        src = ImageOps.exif_transpose(src).convert("RGB")
        if aspect:
            w, h = src.size
            if w / h > aspect:
                new_w = int(h * aspect)
                src = src.crop(((w - new_w) // 2, 0, (w - new_w) // 2 + new_w, h))
            else:
                src = src.crop((0, 0, w, int(w / aspect)))
        variants = []
        for width in widths:
            width = min(width, src.width)
            height = round(src.height * width / src.width)
            resized = src.resize((width, height), Image.LANCZOS)
            for fmt, ext, opts in (
                ("WEBP", "webp", {"quality": 82, "method": 6}),
                ("JPEG", "jpg", {"quality": 84, "optimize": True, "progressive": True}),
            ):
                resized.save(img_dir / f"{name}-{width}.{ext}", fmt, **opts)
            variants.append((width, height))
        largest_w, largest_h = variants[-1]
        meta[name] = {
            "webp": ", ".join(f"/img/{name}-{w}.webp {w}w" for w, _ in variants),
            "jpg": ", ".join(f"/img/{name}-{w}.jpg {w}w" for w, _ in variants),
            "src": f"/img/{name}-{variants[1 if len(variants) > 1 else 0][0]}.jpg",
            "width": largest_w,
            "height": largest_h,
        }

    # Social preview card (1200x630): headshot on the site's background color.
    card = Image.new("RGB", (1200, 630), (11, 15, 20))
    head = ImageOps.fit(Image.open(PHOTOS / "headshot.jpg").convert("RGB"), (630, 630))
    card.paste(head, (570, 0))
    accent = Image.new("RGB", (8, 630), (61, 220, 151))
    card.paste(accent, (562, 0))
    card.save(img_dir / "og-card.jpg", "JPEG", quality=85, optimize=True)
    return meta


def copy_static(out: Path) -> dict:
    """Copy static/ to dist/, adding a content hash to CSS and JS names for caching."""
    assets = {}
    for path in STATIC.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(STATIC)
        if path.suffix in {".css", ".js"}:
            hashed = rel.with_name(f"{path.stem}.{fingerprint(path)}{path.suffix}")
            assets[rel.as_posix()] = "/" + hashed.as_posix()
            rel = hashed
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    return assets


def build(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    content = load_content()
    images = build_images(out)
    assets = copy_static(out)

    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["short_hash"] = short_hash
    env.filters["slug"] = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

    today = dt.date.today()
    context = {
        **content,
        "images": images,
        "asset": lambda name: assets[name],
        "built": today.isoformat(),
        "year": today.year,
    }

    script_hashes = set()
    for page in ("index.html", "404.html"):
        html = env.get_template(page).render(**context)
        (out / page).write_text(html, encoding="utf-8")
        script_hashes.update(inline_script_hashes(html))

    (out / "_headers").write_text(headers_file(sorted(script_hashes)))

    site = content["profile"]["site_url"].rstrip("/")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site}/sitemap.xml\n")
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{site}/</loc><lastmod>{today.isoformat()}</lastmod></url>\n"
        "</urlset>\n"
    )
    print(f"Built {sum(1 for p in out.rglob('*') if p.is_file())} files into {out}")


INLINE_SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)


def inline_script_hashes(html: str) -> list[str]:
    """CSP hashes for inline <script> blocks (not JSON-LD, which browsers don't run)."""
    return [
        "'sha256-" + base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode() + "'"
        for body in INLINE_SCRIPT.findall(html)
    ]


def headers_file(script_hashes: list[str]) -> str:
    """Cloudflare Pages `_headers`: security headers for every page, long caching for assets."""
    csp = "; ".join([
        "default-src 'self'",
        "script-src 'self' " + " ".join(script_hashes),
        "style-src 'self' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data:",
        "connect-src 'self'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
        "upgrade-insecure-requests",
    ])
    return "\n".join([
        "/*",
        "  Strict-Transport-Security: max-age=31536000; includeSubDomains",
        "  X-Content-Type-Options: nosniff",
        "  X-Frame-Options: DENY",
        "  Referrer-Policy: strict-origin-when-cross-origin",
        "  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()",
        "  Cross-Origin-Opener-Policy: same-origin",
        f"  Content-Security-Policy: {csp}",
        "",
        "/css/*",
        "  Cache-Control: public, max-age=31536000, immutable",
        "/js/*",
        "  Cache-Control: public, max-age=31536000, immutable",
        "/img/*",
        "  Cache-Control: public, max-age=604800",
        "",
    ])


def serve(out: Path, port: int) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving {out} at http://localhost:{port} (Ctrl+C to stop)")
        httpd.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "dist", help="output folder (default: dist/)")
    parser.add_argument("--serve", action="store_true", help="serve the output after building")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    build(args.out)
    if args.serve:
        serve(args.out, args.port)


if __name__ == "__main__":
    main()
