#!/usr/bin/env python3
"""
api.py — FastAPI wrapper for website_bot.py (Async Scraper)
"""

import os, asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from website_bot import scrape_website

load_dotenv()
app = FastAPI(title="Website Scraper API", version="2.0")

class ScrapeRequest(BaseModel):
    url: str

@app.get("/")
async def root():
    return {"message": "✅ Website Scraper API v2.0 is running fine!"}

@app.post("/scrape")
async def scrape_endpoint(request: ScrapeRequest):
    url = request.url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    try:
        # 120 sec timeout for long scrapes
        return await asyncio.wait_for(scrape_website(url), timeout=120)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out (site took too long to load).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")
