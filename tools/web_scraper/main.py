import sys
import json
import urllib.request
import re

def run():
    if len(sys.argv) < 2:
        print("Error: No arguments provided to web_scraper tool.")
        return

    try:
        args = json.loads(sys.argv[1])
        url = args.get("url", "")
    except Exception as e:
        print(f"Error parsing arguments: {e}")
        return

    if not url:
        print("Error: No URL provided.")
        return

    if not url.startswith('http'):
        url = 'https://' + url

    try:
        # We use a standard user agent to avoid being blocked by simple bot protection
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')

            # Very basic HTML stripping since we can't guarantee beautifulsoup4 is installed.
            # Remove scripts and styles first
            html = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html)

            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()

            # Cap size so we don't blow up the LLM context
            if len(text) > 10000:
                text = text[:10000] + "\n\n...[Content truncated for length]"

            if not text:
                print(f"Could not extract any readable text from {url}.")
                return

            print(f"Content scraped from {url}:\n\n{text}")

    except Exception as e:
        print(f"Error scraping URL '{url}': {e}")

if __name__ == "__main__":
    run()
