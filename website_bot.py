import os, json, re, time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🔥 Strong prompt for RAG extraction
EXTRACTION_PROMPT = """
You are an intelligent business data extractor.
From the provided website text, extract the following fields:
- Business Name
- About Us
- Main Services (list)
- Email
- Phone
- Address (city wise if found)
- Facebook
- Instagram
- LinkedIn
- Twitter
- Description (short 2–3 lines)
Return a valid JSON.
"""

def scrape_website(url: str):
    print(f"🔍 Running full scrape (this may take a while)...")

    # Playwright scrape (fast mode)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, timeout=60000)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # Extract visible text quickly
    text = " ".join(s.get_text(separator=" ", strip=True) for s in soup.find_all(["p", "h1", "h2", "h3", "li"]))
    text = re.sub(r"\s+", " ", text)

    # Use OpenAI RAG prompt
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.4,
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": text[:10000]}  # limit to avoid timeout
        ],
    )

    raw_output = response.choices[0].message.content.strip()

    # Validate JSON safely
    try:
        data = json.loads(raw_output)
    except Exception:
        data = {"Raw Response": raw_output}

    # Ensure URL field is present
    data["URL"] = url

    print("✅ Extraction complete!")
    return data
