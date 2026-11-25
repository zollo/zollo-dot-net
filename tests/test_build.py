"""Build the site into a temp folder and check the output.

Run with:  python -m pytest -q
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

# Things that must never appear on the public site: the homelab section stays at
# the architecture level (see content/homelab.yaml), and the phone number stays off.
FORBIDDEN = [
    (r"\b(?:10|127)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "private IPv4 address"),
    (r"\b192\.168\.\d{1,3}\.\d{1,3}\b", "private IPv4 address"),
    (r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b", "private IPv4 address"),
    (r"\b99\.69\.\d{1,3}\.\d{1,3}\b", "home public IP"),
    (r"\.int\.zollo\.net|home\.zollo\.net|\.prod\.zollo\.net|\.dev\.zollo\.net|apps\.zollo\.net", "internal or environment domain"),
    (r"(?i)\bprx\d|zollo-srv\d|zollo-san\d|k3s-(?:server|agent)", "internal host name"),
    (r"(?i)wireguard|vpn\.zollo|geoip|\bvlan", "network/VPN detail"),
    (r"(?i)bitwarden|svc\.automation|ZOLLO\\\\", "secret or account detail"),
    (r"\b404[-. ]?314[-. ]?5839\b", "phone number"),
]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for key in ("href", "src"):
            if a.get(key):
                self.refs.append(a[key])
        for key in ("srcset",):
            if a.get(key):
                self.refs += [part.strip().split(" ")[0] for part in a[key].split(",")]


@pytest.fixture(scope="session")
def dist(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("dist")
    build.build(out)
    return out


def test_pages_exist(dist):
    for name in ("index.html", "404.html", "_headers", "robots.txt", "sitemap.xml", "favicon.svg", "img/og-card.jpg"):
        assert (dist / name).is_file(), name


@pytest.mark.parametrize("page", ["index.html", "404.html"])
def test_no_sensitive_details(dist, page):
    html = (dist / page).read_text(encoding="utf-8")
    for pattern, what in FORBIDDEN:
        match = re.search(pattern, html)
        assert not match, f"{what} on {page}: {match.group(0)!r}"


def test_all_projects_listed(dist):
    html = (dist / "index.html").read_text(encoding="utf-8")
    for name in ("navi", "tabula", "trove", "azuregos", "diglett", "certainly"):
        assert f"https://github.com/zollo/{name}" in html


def test_no_education_section(dist):
    html = (dist / "index.html").read_text(encoding="utf-8")
    assert "ITT Technical" not in html and "Education" not in html


@pytest.mark.parametrize("page", ["index.html", "404.html"])
def test_local_links_resolve(dist, page):
    parser = Links()
    parser.feed((dist / page).read_text(encoding="utf-8"))
    for ref in parser.refs:
        if ref.startswith(("http://", "https://", "mailto:")):
            continue
        if ref.startswith("#"):
            assert ref == "#" or ref[1:] in parser.ids, f"missing anchor {ref}"
            continue
        assert (dist / ref.lstrip("/").split("#")[0]).exists() or ref == "/", f"missing file {ref}"


def test_csp_allows_inline_scripts(dist):
    headers = (dist / "_headers").read_text()
    for page in ("index.html", "404.html"):
        for digest in build.inline_script_hashes((dist / page).read_text(encoding="utf-8")):
            assert digest in headers
