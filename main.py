import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yt_dlp

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

    height = 720
    if quality == "1080p":
        height = 1080
    elif quality == "360p":
        height = 360

    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['tvhtml5', 'android_creator', 'mweb'],
                'skip': ['webpage', 'configs']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (SmartHub; SMART-TV; U; Linux/SmartTV) AppleWebKit/538.1+ (KHTML, like Gecko) TV Safari/538.1+'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'video')
            formats = info.get('formats', [])
            
            stream_url = None
            for f in formats:
                if f.get('height') == height and f.get('ext') == 'mp4' and f.get('url'):
                    stream_url = f['url']
                    break
            
            if not stream_url:
                for f in formats:
                    if f.get('ext') == 'mp4' and f.get('url') and f.get('vcodec') != 'none':
                        stream_url = f['url']
                        break

            if not stream_url:
                raise HTTPException(status_code=500, detail="Gagal menemukan link stream video.")

        return JSONResponse({
            "title": title,
            "download_url": stream_url,
            "quality": quality
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses video: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)