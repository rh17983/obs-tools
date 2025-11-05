FROM python:3.11-slim

WORKDIR /app
# deps for your async checker + scraping
RUN pip install --no-cache-dir aiohttp pyyaml beautifulsoup4 lxml requests

# Your existing validator (kept unchanged)
COPY check_links_async.py /app/check_links_async.py

# New one-shot validator that reads CM fragment and writes links-out.yaml
COPY validate_from_sections.py /app/validate_from_sections.py

ENTRYPOINT ["/bin/sh","-lc"]
