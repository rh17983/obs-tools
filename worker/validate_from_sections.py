"""Validate links extracted from HTML sections and output results to YAML.
Usage: python3 validate_from_sections.py <sections.html> <links-out.yaml>"""

#!/usr/bin/env python3
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import yaml

# Import the async validator's process() function
import check_links_async as checker

def extract_links_from_sections(html_text: str):
    soup = BeautifulSoup(html_text, "lxml")

    # If fragment (no <html>), wrap so selectors are consistent
    if not soup.find("html"):
        wrapper = BeautifulSoup("<html><body></body></html>", "lxml")
        body = wrapper.find("body")
        for node in soup.contents:
            body.append(node)
        soup = wrapper

    out = []
    for section in soup.select("div.section"):
        h2 = section.find("h2")
        region = (h2.get_text(strip=True) if h2 else "Unknown").strip()
        sites = []
        for a in section.select(".card-container .card a[href]"):
            name = a.get_text(strip=True)
            href = a.get("href", "").strip()
            if name and href:
                sites.append({name: {"link": href}})
        if sites:
            out.append({region: sites})
    return out

def main():
    if len(sys.argv) != 3:
        print("Usage: validate_from_sections.py <sections.html> <links-out.yaml>", file=sys.stderr)
        sys.exit(1)

    sections_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    # 1) parse CM fragment to extract links

    # read HTML sections
    html = sections_path.read_text(encoding="utf-8")

    # extract links. out is a list of region objects
    data = extract_links_from_sections(html)

    # 2) run async validator on the in-memory data. returns updated data with statuses
    updated = checker.asyncio.run(checker.process(data))

    # 3) write only the final result (what the UI reads)
    out_path.write_text(yaml.safe_dump(updated, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
