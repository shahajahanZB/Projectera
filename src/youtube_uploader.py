import os
import time
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
    video_id = response.get("id")
    logger.info("Upload finished, video id=%s", video_id)
    return video_id
