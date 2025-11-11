#!/usr/bin/env python3
"""
api.py — Stable FastAPI wrapper for website_bot (non-blocking, Railway safe)
"""

import os, threading, json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv(override=True)

from website_bot import scrape_website

app = FastAPI(title="WebsiteBot v3 - Stable")

results_cache = {}

@app.get("/")
def home():
    return {"status": "✅ API is running successfully!"}


@app.post("/scrape")
def scrape_endpoint(payload: dict):
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' in request body")

    task_id = str(abs(hash(url)))

    def run_scrape():
        try:
            result = scrape_website(url)
            results_cache[task_id] = result
        except Exception as e:
            results_cache[task_id] = {"error": str(e)}

    threading.Thread(target=run_scrape, daemon=True).start()

    return JSONResponse({"message": "Scraping started in background", "task_id": task_id})


@app.get("/result/{task_id}")
def get_result(task_id: str):
    if task_id not in results_cache:
        return {"status": "running"}
    return results_cache[task_id]
