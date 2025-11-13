#!/usr/bin/env python3
"""
api.py — FastAPI wrapper for website_bot (synchronous)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from website_bot import scrape_website

app = FastAPI(title="WebsiteBot v3 - Simple")

class ScrapeRequest(BaseModel):
    url: str

@app.get("/")
def home():
    return {"status": "✅ API is running successfully!"}

@app.post("/scrape")
def scrape_endpoint(payload: ScrapeRequest):
    url = payload.url
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url'")
    try:
        data = scrape_website(url)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
