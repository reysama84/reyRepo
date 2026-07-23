#!/usr/bin/env python3
"""Static validation for the Visionet company-profile website.

This repository is a dependency-free static site with no build step or test
runner, so this script is the automated test suite. It parses the shipped HTML
and CSS files (Python standard library only — no external dependencies) and
asserts the structural guarantees the site depends on:

  * the three required pages and the shared stylesheet all exist;
  * every page links styles.css;
  * every page's primary nav cross-links to all three pages;
  * each page marks exactly its own nav link as active;
  * the "Visionet" brand appears in each page's <title> and brand mark;
  * the contact form exposes the required labelled fields.

Run it with:  python3 validate.py
It exits 0 when every check passes, or 1 (printing each failure) otherwise.
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

PAGES = {
    "index.html": "index.html",
    "about.html": "about.html",
    "contact.html": "contact.html",
}
CROSS_LINKS = ("index.html", "about.html", "contact.html")
REQUIRED_FORM_FIELDS = ("name", "email", "subject", "message")

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def read(name: str) -> str:
    with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
        return handle.read()


def title_of(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ""


def active_links(html: str) -> list[str]:
    """hrefs of nav anchors carrying the `active` class."""
    found = []
    for anchor in re.findall(r"<a\b[^>]*>", html, re.IGNORECASE):
        if re.search(r'class\s*=\s*"[^"]*\bactive\b[^"]*"', anchor, re.IGNORECASE):
            href = re.search(r'href\s*=\s*"([^"]*)"', anchor, re.IGNORECASE)
            if href:
                found.append(href.group(1))
    return found


def main() -> int:
    # 1. Required files exist.
    for name in list(PAGES) + ["styles.css"]:
        check(os.path.isfile(os.path.join(ROOT, name)), f"missing required file: {name}")
    if failures:
        # Nothing else can be checked reliably without the files.
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    for page, self_link in PAGES.items():
        html = read(page)

        # 2. Shared stylesheet is linked.
        check(
            re.search(r'<link[^>]+href\s*=\s*"styles\.css"', html, re.IGNORECASE) is not None,
            f"{page}: does not link styles.css",
        )

        # 3. Nav cross-links to all three pages.
        for target in CROSS_LINKS:
            check(
                re.search(rf'href\s*=\s*"{re.escape(target)}"', html) is not None,
                f"{page}: missing nav link to {target}",
            )

        # 4. Exactly this page's link is marked active.
        actives = active_links(html)
        check(
            self_link in actives,
            f"{page}: expected active nav link to {self_link}, got {actives or 'none'}",
        )
        check(
            all(link == self_link for link in actives),
            f"{page}: active state on a foreign link: {actives}",
        )

        # 5. Visionet branding in <title> and brand mark.
        check("Visionet" in title_of(html), f"{page}: 'Visionet' missing from <title>")
        check(
            re.search(r'class\s*=\s*"brand"', html, re.IGNORECASE) is not None
            and "Visionet" in html,
            f"{page}: 'Visionet' brand mark missing",
        )

    # 6. Contact form exposes the required labelled fields.
    contact = read("contact.html")
    check(
        re.search(r"<form\b", contact, re.IGNORECASE) is not None,
        "contact.html: no <form> element",
    )
    for field in REQUIRED_FORM_FIELDS:
        check(
            re.search(rf'\bname\s*=\s*"{field}"', contact, re.IGNORECASE) is not None,
            f"contact.html: form missing field name=\"{field}\"",
        )
        check(
            re.search(rf'<label[^>]+for\s*=\s*"{field}"', contact, re.IGNORECASE) is not None,
            f"contact.html: form field '{field}' has no <label for=\"{field}\">",
        )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"\n{len(failures)} check(s) failed.")
        return 1

    print("All static validation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
