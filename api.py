from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from website_bot import scrape_website
import uvicorn

app = FastAPI(title="Website Scraper API")

class ScrapeRequest(BaseModel):
    url: str

@app.post("/scrape")
async def scrape_endpoint(request: ScrapeRequest):
    try:
        data = await scrape_website(request.url)
        return {"status":"success","data":data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message":"✅ API running"}

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, timeout_keep_alive=60)
