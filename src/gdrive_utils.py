import re
import requests
from tqdm import tqdm

def extract_file_id(gdrive_link: str) -> str:
    # supports https://drive.google.com/file/d/<id>/view?...
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", gdrive_link)
    if m:
        return m.group(1)
    # also support id=FILEID style
    m = re.search(r"id=([a-zA-Z0-9_-]+)", gdrive_link)
    if m:
        return m.group(1)
    raise ValueError("Could not extract Google Drive file ID from link.")

def direct_download_url(file_id: str) -> str:
    # This produces a direct-download link for publicly-shared files.
    return f"https://drive.google.com/uc?export=download&id={file_id}"

def download_video(gdrive_link: str, out_path: str, chunk_size: int = 32768):
    """
    Download a publicly-shared Google Drive file to out_path.
    For very large files Drive sometimes uses a confirmation token; for many public files this works.
    """
    file_id = extract_file_id(gdrive_link)
    url = direct_download_url(file_id)

    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(out_path, "wb") as f, tqdm(total=total, unit='B', unit_scale=True, desc="Downloading") as pbar:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
    return out_path
