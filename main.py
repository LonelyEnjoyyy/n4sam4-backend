import os
import base64
import glob
import tempfile
import uuid
import shutil
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import yt_dlp

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
print(f"[startup] ffmpeg tersedia: {FFMPEG_AVAILABLE} (path: {shutil.which('ffmpeg')})")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COOKIES_PATH = None
_cookies_raw = os.environ.get("YT_COOKIES_RAW")
_cookies_b64 = os.environ.get("YT_COOKIES_B64")

if _cookies_raw:
    try:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp.write(_cookies_raw)
        tmp.close()
        COOKIES_PATH = tmp.name
        print(f"[startup] Cookies (raw) loaded to {COOKIES_PATH}")
    except Exception as e:
        print(f"[startup] Gagal simpan YT_COOKIES_RAW: {e}")
elif _cookies_b64:
    try:
        cookies_content = base64.b64decode(_cookies_b64).decode("utf-8")
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp.write(cookies_content)
        tmp.close()
        COOKIES_PATH = tmp.name
        print(f"[startup] Cookies (base64) loaded to {COOKIES_PATH}")
    except Exception as e:
        print(f"[startup] Gagal decode YT_COOKIES_B64: {e}")
else:
    print("[startup] WARNING: Cookies tidak diset (YT_COOKIES_RAW/YT_COOKIES_B64). Kemungkinan besar akan kena 'Sign in to confirm you're not a bot'.")


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


def _build_ydl_opts(strategy: dict, out_template: str, height: int) -> dict:
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
        "format": f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}]/best",
        "merge_output_format": "mp4",
        "outtmpl": out_template,
    }
    if COOKIES_PATH:
        opts["cookiefile"] = COOKIES_PATH
    return opts


def _cleanup_file(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


@app.get("/api/download")
async def get_video_stream(
    background_tasks: BackgroundTasks,
    url: str = Query(...),
    quality: str = Query("720p"),
):
    if not url:
        raise HTTPException(status_code=400, detail="URL tidak boleh kosong")

    if not FFMPEG_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="ffmpeg tidak ditemukan di server. Set env var NIXPACKS_APT_PKGS=ffmpeg di Railway lalu redeploy.",
        )

    height = 720
    if quality == "1080p":
        height = 1080
    elif quality == "360p":
        height = 360

    job_id = uuid.uuid4().hex
    tmp_dir = tempfile.gettempdir()
    out_template = os.path.join(tmp_dir, f"{job_id}.%(ext)s")

    last_error = None

    for strategy in CLIENT_STRATEGIES:
        ydl_opts = _build_ydl_opts(strategy, out_template, height)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            candidates = glob.glob(os.path.join(tmp_dir, f"{job_id}.*"))
            final_path = next((p for p in candidates if p.endswith(".mp4")), None)
            if not final_path and candidates:
                final_path = candidates[0]

            if final_path and os.path.exists(final_path):
                title = info.get("title", "video")
                safe_title = "".join(
                    c for c in title if c.isalnum() or c in (" ", "-", "_")
                ).strip()[:100] or "video"

                for p in candidates:
                    if p != final_path:
                        _cleanup_file(p)
                background_tasks.add_task(_cleanup_file, final_path)

                return FileResponse(
                    path=final_path,
                    filename=f"{safe_title}.mp4",
                    media_type="video/mp4",
                )

            last_error = "File hasil download tidak ditemukan setelah proses."

        except yt_dlp.utils.DownloadError as e:
            last_error = str(e)
            for p in glob.glob(os.path.join(tmp_dir, f"{job_id}.*")):
                _cleanup_file(p)
            continue
        except Exception as e:
            last_error = str(e)
            for p in glob.glob(os.path.join(tmp_dir, f"{job_id}.*")):
                _cleanup_file(p)
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