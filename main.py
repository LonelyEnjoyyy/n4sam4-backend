import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COBALT_API_URL = "https://api.cobalt.tools/"

@app.get("/api/download")
async def get_video_stream(url: str = Query(...), quality: str = Query("720p")):
    if not url:
        raise HTTPException(status_code=400, detail="URL tidak boleh kosong")

    video_quality = "720"
    if quality == "1080p":
        video_quality = "1080"
    elif quality == "360p":
        video_quality = "360"

    payload = {
        "url": url,
        "videoQuality": video_quality,
        "downloadMode": "auto"
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(COBALT_API_URL, json=payload, headers=headers)
            data = response.json()

            if response.status_code == 200 and data.get("url"):
                return JSONResponse({
                    "title": "YouTube Video",
                    "download_url": data["url"],
                    "quality": quality
                })
            
            error_msg = data.get("text") or "Gagal memproses video via Cobalt API."
            raise HTTPException(status_code=500, detail=error_msg)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal terhubung ke API extractor: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)