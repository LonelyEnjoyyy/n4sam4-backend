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

@app.get("/api/download")
async def get_video_stream(url: str = Query(...), quality: str = Query("720p")):
    if not url:
        raise HTTPException(status_code=400, detail="URL tidak boleh kosong")

    api_url = f"https://api.y2mate.guru/api/convert"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            res = await client.get(f"https://co.wuk.sh/api/json", params={"url": url}, headers={"Accept": "application/json"})
            
            if res.status_code != 200:
                res = await client.post("https://cobalt.stream/api/json", json={"url": url}, headers={"Accept": "application/json"})

            data = res.json()
            stream_url = data.get("url")

            if stream_url:
                return JSONResponse({
                    "title": "YouTube Video",
                    "download_url": stream_url,
                    "quality": quality
                })

            raise HTTPException(status_code=500, detail="Gagal mendapatkan link download dari server extractor.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses video: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)