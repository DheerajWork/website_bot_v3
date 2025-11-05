#!/usr/bin/env python3
"""
website_bot.py — stealth + proxy scraper + RAG + ChromaDB support (Async Safe)
"""

import os, re, time, json, urllib.parse, random, asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
    import chromadb
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False

# ---------------- Config ----------------
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
PROXY = os.getenv("PROXY", "")
MAX_PAGES = 30
CHUNK_SIZE = 180
CHUNK_OVERLAP = 30

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
]

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

def js_stealth_script():
    return """
(() => {
  Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
  Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
  Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
})();
"""

async def launch_browser(url, headless=True, proxy=None):
    ua = random.choice(USER_AGENTS)
    options = {"headless": headless}
    if proxy:
        options["proxy"] = {"server": proxy}

    async with async_playwright() as p:
        browser = await p.chromium.launch(**options)
        context = await browser.new_context(user_agent=ua, locale="en-US", viewport={"width": 1366, "height": 768})
        page = await context.new_page()
        await page.add_init_script(js_stealth_script())

        html = ""
        try:
            await page.goto(url, timeout=60000)
            await asyncio.sleep(2)
            html = await page.content()
        except Exception:
            pass

        await page.close()
        await context.close()
        await browser.close()
        return html

def extract_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].split("#")[0].strip()
        full = urllib.parse.urljoin(base_url, href)
        if full.startswith(base_url):
            links.add(full.rstrip("/"))
    return list(links)

def extract_emails(text):
    return list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)))

def extract_phones(text):
    return list(set(re.findall(r"(\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{2,4}[\s\-]?\d{2,4})", text)))

def extract_addresses(text):
    lines = text.splitlines()
    candidates = [l.strip() for l in lines if len(l.split()) >= 4 and any(ch.isdigit() for ch in l)]
    return candidates[:3]

def rag_extract(text, url):
    if not (CHROMA_AVAILABLE and OPENAI_KEY):
        return None

    client = chromadb.Client()
    openai_client = OpenAI(api_key=OPENAI_KEY)

    words = text.split()
    chunks = [" ".join(words[i:i + CHUNK_SIZE]) for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP)]
    coll = client.get_or_create_collection("website_scraper")

    for i, ch in enumerate(chunks):
        coll.add(documents=[ch], metadatas=[{"url": url, "chunk": i}], ids=[f"{url}_chunk_{i}"])

    query = "Extract Business Name, About Us, Services, Contact Emails, Phones, Address, Socials"
    res = coll.query(query_texts=[query], n_results=3)
    context = " ".join(res["documents"][0]) if res and "documents" in res else " ".join(chunks[:3])

    prompt = f"""
You are a data extraction assistant. From the text below, produce clean JSON with fields:
Business Name, About Us, Main Services, Email, Phone, Address, Facebook, Instagram, LinkedIn, Twitter / X, Description, URL.

URL: {url}
Text:
{context}
"""
    resp = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    raw = resp.choices[0].message.content
    raw = re.sub(r"^```json", "", raw.strip())
    raw = re.sub(r"```$", "", raw.strip())
    try:
        return json.loads(raw)
    except Exception:
        return {"raw_ai": raw}

async def scrape_website(url):
    html = await launch_browser(url, headless=True, proxy=PROXY)
    links = extract_links(html, url)
    target_pages = [url] + [l for l in links if any(k in l.lower() for k in ["contact", "about"])]

    all_text = ""
    for page in target_pages[:3]:
        html_page = await launch_browser(page, headless=True, proxy=PROXY)
        all_text += " " + clean_text(html_page)

    emails = extract_emails(all_text)
    phones = extract_phones(all_text)
    addresses = extract_addresses(all_text)

    ai_result = rag_extract(all_text, url)

    output = {
        "Business Name": "",
        "About Us": "",
        "Main Services": "",
        "Email": emails[0] if emails else "",
        "Phone": phones[0] if phones else "",
        "Address": addresses[0] if addresses else "",
        "Facebook": "",
        "Instagram": "",
        "LinkedIn": "",
        "Twitter / X": "",
        "Description": "",
        "URL": url
    }

    if ai_result:
        for k in output:
            if k in ai_result and ai_result[k]:
                output[k] = ai_result[k]

    return output

if __name__ == "__main__":
    url = input("Enter website URL: ").strip()
    result = asyncio.run(scrape_website(url))
    print(json.dumps(result, indent=2, ensure_ascii=False))
