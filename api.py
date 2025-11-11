import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from concurrent.futures import ThreadPoolExecutor
import uuid
from website_bot import scrape_website

# Disable debug mode for asyncio to avoid performance overhead
asyncio.get_event_loop().set_debug(False)

app = FastAPI(title="🚀 Website Scraper API (Optimized)")

executor = ThreadPoolExecutor(max_workers=3)
scrape_results = {}  # In-memory storage for task results

@app.get("/")
async def home():
    return {"message": "✅ Website Scraper API is running successfully on Railway!"}

def run_scrape(task_id: str, url: str):
    """Run the website scrape in a background thread"""
    try:
        print(f"🔍 Starting scrape for {url}")
        result = scrape_website(url)
        scrape_results[task_id] = {"status": "success", "data": result}
        print(f"✅ Completed scrape for {url}")
    except Exception as e:
        scrape_results[task_id] = {"status": "error", "message": str(e)}
        print(f"❌ Error scraping {url}: {e}")

@app.post("/scrape")
async def scrape(request: Request, background_tasks: BackgroundTasks):
    """Start the scraping task"""
    body = await request.json()
    url = body.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' field")

    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_scrape, task_id, url)

    return {
        "status": "processing",
        "task_id": task_id,
        "message": f"Full RAG scraping started in background for {url}"
    }

@app.get("/result/{task_id}")
async def get_result(task_id: str):
    """Check task result"""
    result = scrape_results.get(task_id)
    if not result:
        return {"status": "pending", "message": "⏳ Result not ready yet"}
    return result
