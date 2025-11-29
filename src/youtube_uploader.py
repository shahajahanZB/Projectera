import os
import time
import json
import logging
import random
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_youtube_client_from_refresh_token(client_id: str, client_secret: str, refresh_token: str):
    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=YOUTUBE_SCOPES
    )
    youtube = build("youtube", "v3", credentials=creds)
    return youtube

def upload_video(youtube, filepath: str, caption: str, privacy_status="public", max_retries=10):
    """
    Uploads file at filepath to YouTube using resumable upload.
    Returns uploaded video id.
    """
    body = {
        "snippet": {
            "title": caption[:90] or "Uploaded with bot",
            "description": caption or "",
            "tags": []
        },
        "status": {
            "privacyStatus": privacy_status
        }
    }

    media = MediaFileUpload(filepath, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    retry = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                logger.info("Upload progress: %d%%", int(status.progress() * 100))
        except HttpError as e:
            logger.exception("HttpError during upload: %s", e)
            if e.resp.status in [500, 502, 503, 504] and retry < max_retries:
                sleep_seconds = (2 ** retry) + (random.random() * 2)
                logger.info("Retrying in %s seconds...", sleep_seconds)
                time.sleep(sleep_seconds)
                retry += 1
            else:
                raise
    # Log full response for debugging (API returns lots of useful info)
    logger.info("Upload finished response: %s", json.dumps(response, indent=2))
    video_id = response.get("id")
    logger.info("Upload finished, video id=%s", video_id)

    # Optional: check processing status briefly to help diagnose stuck uploads.
    # Controlled by environment variable YT_CHECK_PROCESS_SECONDS (int seconds). Default 0 = disabled.
    try:
        check_seconds = int(os.getenv("YT_CHECK_PROCESS_SECONDS", "0"))
    except ValueError:
        check_seconds = 0

    if video_id and check_seconds > 0:
        # poll processing status every 5 seconds up to check_seconds
        logger.info("Checking processing status for video=%s for up to %s seconds", video_id, check_seconds)
        start = time.time()
        while time.time() - start < check_seconds:
            try:
                details = youtube.videos().list(part="status,processingDetails", id=video_id).execute()
                items = details.get("items", [])
                if items:
                    status = items[0].get("status", {})
                    proc = items[0].get("processingDetails", {})
                    logger.info("Video status: %s; processingDetails summary: %s", status, proc.get("processingStatus"))
                    # If processing has failed, log error and break
                    if status.get("uploadStatus") in ("rejected", "failed") or proc.get("processingStatus") == "failed":
                        logger.error("Video processing failed: %s", json.dumps(items[0], indent=2))
                        break
                    # If processed, break
                    if proc.get("processingStatus") == "succeeded":
                        logger.info("Video processing completed successfully")
                        break
            except HttpError as e:
                logger.exception("Error while checking processing status: %s", e)
            time.sleep(5)

    return video_id

def get_video_details(youtube, video_id: str):
    """Return full details for a video id (status + processingDetails)"""
    try:
        resp = youtube.videos().list(part="status,processingDetails", id=video_id).execute()
        return resp
    except HttpError:
        logger.exception("Failed to fetch video details for %s", video_id)
        return None
