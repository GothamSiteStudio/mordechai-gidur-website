"""Compare a candidate host against production before flipping DNS.

Usage:
    python migration/verify_redirects.py https://mordechai-gidur.pages.dev

Checks every canonical URL in sitemap.xml plus every legacy .html path, and
reports any status code or redirect target that differs from what the live
Netlify site does today. Exit code is non-zero if anything mismatches, so it
can gate the cutover.
"""

import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

PROD = "https://mordechaigidur.co.il"
ROOT = Path(__file__).resolve().parent.parent


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Capture the first hop instead of following it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def probe(url):
    """Return (status, location) for one URL, without following redirects."""
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "cutover-check"})
    try:
        with OPENER.open(req, timeout=20) as resp:
            return resp.status, resp.headers.get("Location")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location")
    except Exception as e:  # DNS, TLS, timeout
        return f"ERR {type(e).__name__}", None


def normalize(location):
    """Strip the host so prod and candidate targets are comparable."""
    if not location:
        return None
    for host in (PROD, "https://mordechai-gidur.pages.dev"):
        if location.startswith(host):
            return location[len(host):] or "/"
    if location.startswith("http"):
        # Absolute URL on some other host - keep it, a mismatch is meaningful.
        return location
    return location


def collect_paths():
    """Canonical paths from sitemap.xml, plus their legacy .html twins."""
    paths = set()

    sitemap = ROOT / "sitemap.xml"
    tree = ET.parse(sitemap)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for loc in tree.iterfind(".//sm:loc", ns):
        url = (loc.text or "").strip()
        if url.startswith(PROD):
            paths.add(url[len(PROD):] or "/")

    # Legacy .html paths that must keep 301-ing after the move.
    for line in (ROOT / "_redirects").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        paths.add(line.split()[0])

    return sorted(paths)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    candidate = sys.argv[1].rstrip("/")
    paths = collect_paths()
    print(f"Comparing {len(paths)} paths: {candidate} vs {PROD}\n")

    mismatches = []
    for path in paths:
        want_status, want_loc = probe(PROD + path)
        got_status, got_loc = probe(candidate + path)
        want_loc, got_loc = normalize(want_loc), normalize(got_loc)

        if (want_status, want_loc) == (got_status, got_loc):
            print(f"  ok   {path}  [{want_status}]")
        else:
            mismatches.append((path, want_status, want_loc, got_status, got_loc))
            print(f"  DIFF {path}")
            print(f"         prod      -> {want_status} {want_loc or ''}")
            print(f"         candidate -> {got_status} {got_loc or ''}")

    print()
    if mismatches:
        print(f"{len(mismatches)} mismatch(es). Do NOT flip DNS until these are resolved.")
        return 1

    print(f"All {len(paths)} paths match production. Safe to flip DNS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
