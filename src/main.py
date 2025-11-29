import os
import logging
import argparse
import shutil

from csv_utils import get_next_row, mark_uploaded
from gdrive_utils import download_video
from youtube_uploader import get_youtube_client_from_refresh_token, upload_video, get_video_details

TEMP_DIR = "videos"
TEMP_FILE = os.path.join(TEMP_DIR, "tmp_video.mp4")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")
logger = logging.getLogger("yt-autoupload")

def run_once():
    idx, link, caption = get_next_row()
    if idx is None:
        logger.info("No pending videos to upload. Exiting.")
        return 0

    logger.info("Next row index=%s link=%s", idx, link)
    os.makedirs(TEMP_DIR, exist_ok=True)
    try:
        logger.info("Downloading...")
        download_video(link, TEMP_FILE)

        logger.info("Building YouTube client...")
        CLIENT_ID = os.getenv("CLIENT_ID")
        CLIENT_SECRET = os.getenv("CLIENT_SECRET")
        REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

        if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
            logger.error("Missing CLIENT_ID/CLIENT_SECRET/REFRESH_TOKEN in environment.")
            return 2

        youtube = get_youtube_client_from_refresh_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)

        logger.info("Uploading to YouTube...")
        video_id = upload_video(youtube, TEMP_FILE, caption or "")
        logger.info("Uploaded video id=%s", video_id)

        # Fetch video details (processing status) so we can record video_id and status
        details = None
        if video_id:
            try:
                details = get_video_details(youtube, video_id)
                logger.info("Video details: %s", details)
            except Exception:
                logger.exception("Failed fetching video details for %s", video_id)

        # Mark the CSV row with video_id; record 'failed' if processing indicates failure
        status = "yes"
        try:
            if details:
                items = details.get("items", [])
                if items:
                    proc = items[0].get("processingDetails", {})
                    upload_status = items[0].get("status", {}).get("uploadStatus")
                    proc_status = proc.get("processingStatus")
                    logger.info("UploadStatus=%s, processingStatus=%s", upload_status, proc_status)
                    if upload_status in ("rejected", "failed") or proc_status == "failed":
                        status = "failed"
        except Exception:
            logger.exception("Error evaluating processing status for %s", video_id)

        logger.info("Marking CSV as '%s' and recording video_id=%s", status, video_id)
        mark_uploaded(idx, video_id=video_id, status=status)

    finally:
        # clean up
        try:
            if os.path.exists(TEMP_FILE):
                os.remove(TEMP_FILE)
        except Exception:
            logger.exception("Failed cleaning temp file")

    return 0

def generate_refresh_token_local():
    """
    Local helper that uses google-auth-oauthlib InstalledAppFlow to open a browser and get a refresh token.
    This requires local client_secret.json in repo root (downloaded from Google Cloud).
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    # this will open browser; ensure prompt=consent and access_type=offline by passing these params in run_local_server
    creds = flow.run_local_server(port=0, prompt="consent", authorization_prompt_message="", access_type="offline")
    print("REFRESH_TOKEN=", creds.refresh_token)
    print("CLIENT_ID and CLIENT_SECRET are in client_secret.json")
    return creds.refresh_token

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-token", action="store_true", help="Run local OAuth flow to print refresh token")
    args = parser.parse_args()

    if args.generate_token:
        generate_refresh_token_local()
    else:
        raise SystemExit(run_once())
