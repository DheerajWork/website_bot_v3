#!/usr/bin/env python3
"""
api.py — FastAPI wrapper for website_bot.py
"""

import os, json
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
    url = request.url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    try:
        data = scrape_website(url)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Website Scraper API is running."}
