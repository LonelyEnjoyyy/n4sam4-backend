import os
import tempfile
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = tempfile.gettempdir()

@app.get("/api/download")
async def download_video(url: str = Query(...), quality: str = Query("720p")):
    if not url:
        raise HTTPException(status_code=400, detail="URL tidak boleh kosong")

    format_selector = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    if quality == "1080p":
        format_selector = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    elif quality == "360p":
        format_selector = "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    out_template = os.path.join(TEMP_DIR, "%(id)s.%(ext)s")

    ydl_opts = {
        'format': format_selector,
        'outtmpl': out_template,
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'tv_embedded'],
            }
        },
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            final_filename = base + ".mp4"
            
            if not os.path.exists(final_filename):
                final_filename = filename

        return FileResponse(
            path=final_filename,
            media_type="video/mp4",
            filename=os.path.basename(final_filename)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses video: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)