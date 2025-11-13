from fastapi import FastAPI, HTTPException
from website_bot import crawl_site, select_main_pages, fetch_page, clean_text, chunk_text, rag_extract, extract_email, extract_phone, extract_address
from bs4 import BeautifulSoup
import json

app = FastAPI(title="Website Info Extractor API")

@app.get("/")
def root():
    return {"message": "Website Info Extractor API is running 🚀"}

@app.post("/scrape")
def scrape_website(data: dict):
    site_url = data.get("url")
    if not site_url:
        raise HTTPException(status_code=400, detail="Missing 'url' in request body")

    if not site_url.startswith("http"):
        site_url = "https://" + site_url

    print(f"🔍 Crawling: {site_url}")
    all_urls = crawl_site(site_url, max_pages=50)
    main_pages = select_main_pages(all_urls)

    all_text = ""
    for page_url in main_pages:
        html = fetch_page(page_url)
        soup = BeautifulSoup(html, "html.parser")
        [s.extract() for s in soup(["script", "style", "noscript"])]
        text = clean_text(soup.get_text(" ", strip=True))
        all_text += " " + text

    all_text = clean_text(all_text)
    chunks = chunk_text(all_text)

    final_data = rag_extract(chunks, site_url)

    if not final_data:
        final_data = {
            "Business Name": "",
            "About Us": "",
            "Main Services": "",
            "Email": extract_email(all_text),
            "Phone": extract_phone(all_text),
            "Address": extract_address(all_text),
            "Facebook": "",
            "Instagram": "",
            "LinkedIn": "",
            "Twitter / X": "",
            "Description": "",
            "URL": site_url,
        }

    return json.loads(json.dumps(final_data, ensure_ascii=False))
