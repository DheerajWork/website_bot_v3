#!/usr/bin/env python3
"""
api.py — FastAPI wrapper for website_bot.py (Async Compatible)
"""

import os, json, asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from website_bot import scrape_website
from dotenv import load_dotenv

load_dotenv()  # Load .env automatically

app = FastAPI(title="Website Scraper API")

class ScrapeRequest(BaseModel):
    url: str


@app.post("/scrape")
async def scrape_endpoint(request: ScrapeRequest):
    """
    POST /scrape
    Body: {"url": "https://example.com"}
    """
    url = request.url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    try:
        # ✅ call async scrape_website function properly
        data = await scrape_website(url)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Health check route"""
    return {"message": "Website Scraper API is running."}
