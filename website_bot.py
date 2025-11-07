#!/usr/bin/env python3
"""
website_bot.py — Advanced Async Website Scraper with GPT + RAG Extraction
"""

import os, re, json, random, urllib.parse, asyncio
from typing import Dict, List
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ---------------- Config ----------------
load_dotenv(override=True)
USE_HEADLESS = True
MAX_PAGES = 10
CHUNK_SIZE = 200
CHUNK_OVERLAP = 40

# ---------------- Text Cleaning ----------------
def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def chunk_text(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> list:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = words[i:i + size]
        chunks.append(" ".join(chunk))
        i += size - overlap
    return chunks

# ---------------- Simple Extraction Helpers ----------------
def extract_meta_info(soup):
    """Extract meta title, description, and site_name"""
    meta = {"title": "", "description": "", "site_name": ""}
    if not soup:
        return meta
    title_tag = soup.find("title")
    meta["title"] = title_tag.get_text(strip=True) if title_tag else ""
    desc_tag = soup.find("meta", attrs={"name": "description"})
    meta["description"] = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""
    og_site = soup.find("meta", property="og:site_name")
    meta["site_name"] = og_site["content"].strip() if og_site and og_site.get("content") else ""
    return meta

def extract_email(text: str) -> str:
    m = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return m[0] if m else ""

def extract_phone(text: str) -> str:
    m = re.findall(r"(\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{2,4}[\s\-]?\d{2,4})", text)
    return m[0] if m else ""

def extract_address(text: str) -> str:
    lines = text.splitlines()
    for line in lines:
        if any(ch.isdigit() for ch in line) and len(line.split()) > 3:
            return line.strip()
    return ""

def extract_services(soup):
    """Try to extract service or product items"""
    services = set()
    if not soup:
        return []
    for tag in soup.find_all(["li", "p", "h3", "h4", "span"]):
        txt = clean_text(tag.get_text(" ", strip=True))
        if any(w in txt.lower() for w in ["service", "solution", "product", "design", "consulting"]):
            if 3 < len(txt.split()) < 15:
                services.add(txt)
    return list(services)

def extract_social_links(soup):
    socials = {"Facebook": "", "Instagram": "", "LinkedIn": "", "Twitter / X": ""}
    if not soup:
        return socials
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "facebook.com" in href:
            socials["Facebook"] = href
        elif "instagram.com" in href:
            socials["Instagram"] = href
        elif "linkedin.com" in href:
            socials["LinkedIn"] = href
        elif "twitter.com" in href or "x.com" in href:
            socials["Twitter / X"] = href
    return socials

# ---------------- Async Playwright ----------------
from playwright.async_api import async_playwright

async def fetch_page(url: str, headless=USE_HEADLESS) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        html = ""
        try:
            await page.goto(url, timeout=45000)
            await asyncio.sleep(2 + random.random() * 2)
            html = await page.content()
        except Exception:
            html = ""
        finally:
            await page.close()
            await context.close()
            await browser.close()
    return html

async def crawl_site(base_url: str, max_pages=MAX_PAGES) -> List[str]:
    visited, queue = set(), [base_url.rstrip("/")]
    all_urls = []
    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        html = await fetch_page(url)
        if not html:
            continue
        all_urls.append(url)
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = urllib.parse.urljoin(base_url, a["href"].split("#")[0])
            if href.startswith(base_url):
                queue.append(href.rstrip("/"))
        visited.add(url)
    return list(dict.fromkeys(all_urls))

# ---------------- GPT + RAG ----------------
try:
    import chromadb
    from chromadb.utils import embedding_functions
    from openai import OpenAI
except ImportError:
    chromadb = None
    embedding_functions = None
    OpenAI = None

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
chroma_client = chromadb.Client() if chromadb else None
openai_client = OpenAI(api_key=OPENAI_KEY) if OpenAI and OPENAI_KEY else None
openai_ef = (
    embedding_functions.OpenAIEmbeddingFunction(api_key=OPENAI_KEY, model_name="text-embedding-3-small")
    if embedding_functions and OPENAI_KEY else None
)

async def rag_extract(chunks, url):
    """Use GPT + RAG to extract structured info"""
    if not openai_client or not openai_ef:
        return None

    coll = chroma_client.get_or_create_collection("rag_extraction", embedding_function=openai_ef)
    for i, ch in enumerate(chunks):
        coll.add(documents=[ch], metadatas=[{"url": url}], ids=[f"{url}_chunk_{i}"])

    query_text = "Extract full structured company information."
    res = coll.query(query_texts=[query_text], n_results=3)
    context = " ".join(res.get("documents", [[]])[0]) if res else " ".join(chunks[:3])

    prompt = f"""
You are a professional data extraction assistant.
From the provided text, extract detailed company data.
Return STRICT JSON (no markdown, no explanation).

Keys:
- Business Name
- About Us
- Main Services (as list)
- Email
- Phone
- Address
- Facebook
- Instagram
- LinkedIn
- Twitter / X
- Description
- URL

Website: {url}

Text:
{context}
"""

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r"^```json", "", raw)
    raw = re.sub(r"```$", "", raw)
    try:
        return json.loads(raw)
    except:
        return {"raw_ai_output": raw}

# ---------------- Public Function ----------------
async def scrape_website(site_url: str) -> Dict:
    if not site_url.startswith("http"):
        site_url = "https://" + site_url

    urls = await crawl_site(site_url, MAX_PAGES)
    main_urls = [u for u in urls if any(x in u for x in ["about", "contact", "service"])] or urls[:3]

    full_text = ""
    combined_soup = None
    for u in main_urls:
        html = await fetch_page(u)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for s in soup(["script", "style", "noscript"]):
            s.extract()
        main_block = soup.find("main") or soup
        full_text += " " + clean_text(main_block.get_text(" ", strip=True))
        combined_soup = soup

    full_text = clean_text(full_text)
    chunks = chunk_text(full_text)

    # Try GPT + RAG extraction
    data = await rag_extract(chunks, site_url)
    if data:
        return data

    # Fallback simple extraction
    meta = extract_meta_info(combined_soup)
    socials = extract_social_links(combined_soup)
    services = extract_services(combined_soup)
    return {
        "Business Name": meta["site_name"] or meta["title"],
        "About Us": full_text[:600],
        "Main Services": services[:10],
        "Email": extract_email(full_text),
        "Phone": extract_phone(full_text),
        "Address": extract_address(full_text),
        "Facebook": socials["Facebook"],
        "Instagram": socials["Instagram"],
        "LinkedIn": socials["LinkedIn"],
        "Twitter / X": socials["Twitter / X"],
        "Description": meta["description"] or full_text[:400],
        "URL": site_url
    }
