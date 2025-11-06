import os, re, json, asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from openai import OpenAI
from chromadb.utils import embedding_functions
import chromadb

OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Setup clients
openai_client = OpenAI(api_key=OPENAI_KEY)
chroma_client = chromadb.Client()
embedding_function = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_KEY, model_name="text-embedding-3-small"
)

# ------------- Helper functions -------------
def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

def chunk_text(text, size=400, overlap=50):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i+size]))
        i += size - overlap
    return chunks

def extract_email(text):
    m = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return m[0] if m else ""

def extract_phone(text):
    m = re.findall(r"(\+\d{1,3}[\s\-]?\(?\d+\)?[\s\-]?\d+[\s\-]?\d+)", text)
    return m[0] if m else ""

def extract_address(text):
    lines = text.split("\n")
    for line in lines:
        if any(ch.isdigit() for ch in line) and len(line.split()) > 3:
            return line.strip()
    return ""

# ------------- Playwright async fetch -------------
async def fetch_page(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(url, timeout=45000)
            await asyncio.sleep(2)
            html = await page.content()
        except:
            html = ""
        await page.close()
        await context.close()
        await browser.close()
    return html

async def scrape_main_pages(base_url):
    html = await fetch_page(base_url)
    soup = BeautifulSoup(html, "html.parser")
    urls = [base_url]
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "about" in href.lower(): urls.append(href if href.startswith("http") else base_url+href)
        if "contact" in href.lower(): urls.append(href if href.startswith("http") else base_url+href)
    return urls[:3]  # home, about, contact

# ------------- RAG + GPT extraction -------------
async def rag_extract(chunks, url):
    coll = chroma_client.get_or_create_collection(
        "rag_collection", embedding_function=embedding_function
    )
    for i, ch in enumerate(chunks):
        coll.add(documents=[ch], metadatas=[{"url": url, "chunk": i}], ids=[f"{url}_chunk_{i}"])
    query = "Extract JSON with Business Name, About Us, Main Services, Email, Phone, Address, Social Links, Description, URL"
    res = coll.query(query_texts=[query], n_results=3)
    context_text = " ".join(res.get("documents", [[]])[0]) if res else " ".join(chunks[:3])
    prompt = f"""
Extract clean JSON from the following text:
URL: {url}
Text: {context_text}
Return JSON with keys: Business Name, About Us, Main Services, Email, Phone, Address, Facebook, Instagram, LinkedIn, Twitter / X, Description, URL
"""
    resp = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        request_timeout=30
    )
    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r"^```json", "", raw)
    raw = re.sub(r"```$", "", raw)
    try: return json.loads(raw)
    except: return {"raw_ai": raw}

# ------------- Public scrape function -------------
async def scrape_website(url):
    if not url.startswith("http"): url = "https://" + url
    main_pages = await scrape_main_pages(url)
    all_text = ""
    for page_url in main_pages:
        html = await fetch_page(page_url)
        soup = BeautifulSoup(html, "html.parser")
        [s.extract() for s in soup(["script","style","noscript"])]
        text = clean_text(soup.get_text(" ", strip=True))
        all_text += " " + text
    chunks = chunk_text(all_text)
    data = await rag_extract(chunks, url)
    if not data:
        data = {
            "Business Name":"",
            "About Us":"",
            "Main Services":[],
            "Email":extract_email(all_text),
            "Phone":extract_phone(all_text),
            "Address":extract_address(all_text),
            "Facebook":"",
            "Instagram":"",
            "LinkedIn":"",
            "Twitter / X":"",
            "Description":"",
            "URL":url
        }
    return data
