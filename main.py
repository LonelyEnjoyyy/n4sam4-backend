import os
import base64
import tempfile
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
COOKIES_PATH = None
_cookies_b64 = os.environ.get("YT_COOKIES_B64")
if _cookies_b64:
    try:
        cookies_content = base64.b64decode(_cookies_b64).decode("utf-8")
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp.write(cookies_content)
        tmp.close()
        COOKIES_PATH = tmp.name
        print(f"[startup] Cookies loaded to {COOKIES_PATH}")
    except Exception as e:
        print(f"[startup] Gagal decode YT_COOKIES_B64: {e}")
else:
    print("[startup] WARNING: YT_COOKIES_B64 tidak diset. Kemungkinan besar akan kena 'Sign in to confirm you're not a bot'.")

CLIENT_STRATEGIES = [
    {"player_client": ["ios"]},
    {"player_client": ["android"]},
    {"player_client": ["web_embedded"]},
    {"player_client": ["tv_embedded"]},
    {"player_client": ["web", "android", "ios"]},
]

USER_AGENTS = {
    "ios": "com.google.ios.youtube/19.29.1 (iPhone14,3; U; CPU iOS 17_5 like Mac OS X)",
    "android": "com.google.android.youtube/19.29.37 (Linux; U; Android 14) gzip",
}


def _build_ydl_opts(strategy: dict) -> dict:
    opts = {
        "quiet": True,
        "noplaylist": True,
        "socket_timeout": 15,
        "extractor_args": {"youtube": {**strategy}},
        "http_headers": {
            "User-Agent": USER_AGENTS.get(
                strategy["player_client"][0],
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
        },
        "source_address": "0.0.0.0",
    }
    if COOKIES_PATH:
        opts["cookiefile"] = COOKIES_PATH
    return opts


@app.get("/api/download")
async def get_video_stream(url: str = Query(...), quality: str = Query("720p")):
    if not url:
        raise HTTPException(status_code=400, detail="URL tidak boleh kosong")

    height = 720
    if quality == "1080p":
        height = 1080
    elif quality == "360p":
        height = 360

    last_error = None

    for strategy in CLIENT_STRATEGIES:
        ydl_opts = _build_ydl_opts(strategy)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                title = info.get("title", "video")
                formats = info.get("formats", [])

                stream_url = None
                for f in formats:
                    if f.get("height") == height and f.get("ext") == "mp4" and f.get("url"):
                        stream_url = f["url"]
                        break
                if not stream_url:
                    for f in formats:
                        if f.get("ext") == "mp4" and f.get("url") and f.get("vcodec") != "none":
                            stream_url = f["url"]
                            break

                if stream_url:
                    return JSONResponse({
                        "title": title,
                        "download_url": stream_url,
                        "quality": quality,
                        "client_used": strategy["player_client"][0],
                    })
                last_error = "Format video tidak ditemukan pada strategi ini."

        except yt_dlp.utils.DownloadError as e:
            last_error = str(e)
            continue
        except Exception as e:
            last_error = str(e)
            continue

    # semua strategi gagal
    if last_error and ("Sign in to confirm" in last_error or "not a bot" in last_error):
        raise HTTPException(
            status_code=503,
            detail=(
                "Semua strategi client diblokir YouTube ('not a bot'). "
                "IP server ini kemungkinan besar sudah kena flag permanen — "
                "solusi paling ampuh tetap cookies (set YT_COOKIES_B64) atau proxy residential."
            ),
        )
    raise HTTPException(status_code=500, detail=f"Gagal memproses video: {last_error}")