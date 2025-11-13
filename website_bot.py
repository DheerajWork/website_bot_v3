#!/usr/bin/env python3
"""
website_bot.py — Fast multi-website scraper, returns structured data immediately
"""

import os, re, time, urllib.parse
from typing import List
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# ---------------- Config ----------------
load_dotenv(override=True)

USE_HEADLESS = True

# ---------------- Helper functions ----------------
def clean_text(t):
    return re.sub(r"\s+", " ", t).strip()

def fetch_page(url: str, headless: bool = USE_HEADLESS) -> str:
    """Fetch page with Playwright"""
    html = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            page.goto(url, timeout=50000, wait_until="networkidle")
            # scroll to load lazy content
            for _ in range(2):
                page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                time.sleep(1)
            html = page.content()
            # iframe content
            for frame in page.frames:
                try:
                    html += frame.content()
                except:
                    pass
            page.close()
            context.close()
            browser.close()
    except Exception as e:
        print(f"⚠️ Page fetch failed for {url}: {e}")
    return html

def extract_links(base_url, html_text) -> List[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("mailto:") or href.startswith("tel:"):
            continue
        full_url = urllib.parse.urljoin(base_url, href.split("#")[0])
        if full_url.startswith(base_url):
            links.add(full_url.rstrip("/"))
    return list(links)

def crawl_site(base_url, max_pages=10):
    visited, queue = set(), [base_url.rstrip("/")]
    structure = []
    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        html = fetch_page(url)
        structure.append(url)
        for link in extract_links(base_url, html):
            if link not in visited and len(visited) < max_pages:
                queue.append(link)
        visited.add(url)
    return structure

def select_main_pages(urls: List[str]):
    home = urls[0] if urls else ""
    about = next((u for u in urls if "about" in u.lower()), "")
    contact = next((u for u in urls if "contact" in u.lower()), "")
    return list(filter(None, [home, about, contact]))

# ---------------- Fallback Extraction ----------------
def fallback_extract(text, site_url):
    return {
        "Business Name": "",
        "About Us": "",
        "Main Services": [],
        "Email": re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text),
        "Phone": re.findall(r"\+?\d[\d\s\-]{7,}", text),
        "Address": {},
        "Facebook": "",
        "Instagram": "",
        "LinkedIn": "",
        "Twitter/X": "",
        "Description": "",
        "URL": site_url,
    }

# ---------------- Main Function ----------------
def scrape_website(site_url: str):
    if not site_url.startswith("http"):
        site_url = "https://" + site_url

    urls = crawl_site(site_url, max_pages=10)
    main_pages = select_main_pages(urls)

    full_text = ""
    for page in main_pages:
        html = fetch_page(page)
        soup = BeautifulSoup(html, "html.parser")
        [s.extract() for s in soup(["script", "style", "noscript"])]
        text = clean_text(soup.get_text(" ", strip=True))
        full_text += " " + text
        if soup.title:
            full_text += " " + soup.title.string

    data = fallback_extract(full_text, site_url)

    return data

# ---------------- CLI ----------------
if __name__ == "__main__":
    url = input("Enter website URL: ").strip()
    result = scrape_website(url)
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
