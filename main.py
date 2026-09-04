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

def extract_video_id(url: str) -> str:
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "shorts/" in url:
        return url.split("shorts/")[1].split("?")[0]
    return url

@app.get("/api/download")
async def get_video_stream(url: str = Query(...), quality: str = Query("720p")):
    if not url:
        raise HTTPException(status_code=400, detail="URL tidak boleh kosong")

    video_id = extract_video_id(url)
    
    piped_instances = [
        f"https://pipedapi.kavin.rocks/streams/{video_id}",
        f"https://api.piped.privacydev.net/streams/{video_id}",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for api_endpoint in piped_instances:
            try:
                res = await client.get(api_endpoint, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    audio_streams = data.get("audioStreams", [])
                    video_streams = data.get("videoStreams", [])
                    
                    combined_streams = [s for s in video_streams if not s.get("videoOnly")]
                    
                    stream_url = None
                    if combined_streams:
                        target_height = 720
                        if quality == "1080p":
                            target_height = 1080
                        elif quality == "360p":
                            target_height = 360

                        for stream in combined_streams:
                            if stream.get("quality") == f"{target_height}p" or stream.get("height") == target_height:
                                stream_url = stream.get("url")
                                break
                        
                        if not stream_url:
                            stream_url = combined_streams[0].get("url")

                    if stream_url:
                        return JSONResponse({
                            "title": data.get("title", "YouTube Video"),
                            "download_url": stream_url,
                            "quality": quality
                        })
            except Exception:
                continue

    raise HTTPException(
        status_code=500, 
        detail="Gagal mengekstraksi link video dari server eksternal."
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)