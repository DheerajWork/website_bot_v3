from fastapi import FastAPI, HTTPException
from website_bot import scrape_website

app = FastAPI(title="Website Data Scraper API")

@app.get("/")
def home():
    return {"message": "✅ Website Scraper API is running successfully."}

@app.post("/scrape")
def scrape(data: dict):
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' field in request body")
    try:
        result = scrape_website(url)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
