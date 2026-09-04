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

    height_map = {
        "1080p": 1080,
        "720p": 720,
        "360p": 360
    }
    target_height = height_map.get(quality, 720)

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': f'bestvideo[height<={target_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={target_height}][ext=mp4]/best',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            stream_url = info.get('url')
            
            if not stream_url and 'formats' in info:
                for f in info['formats']:
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        stream_url = f.get('url')
                        break
                if not stream_url:
                    stream_url = info['formats'][-1].get('url')

            return JSONResponse({
                "title": info.get('title', 'YouTube Video'),
                "download_url": stream_url,
                "quality": quality
            })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses video: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)