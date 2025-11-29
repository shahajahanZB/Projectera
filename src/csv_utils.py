import pandas as pd
from typing import Tuple, Optional

CSV_FILE = "data/uploads.csv"

def _read_df():
    return pd.read_csv(CSV_FILE, dtype=str).fillna("")

def get_next_row() -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """
    Returns (index, gdrive_link, caption) for first row where uploaded != "yes".
    Index is the integer position (0-based).
    """
    df = _read_df()
    for idx, row in df.iterrows():
        # Skip rows already marked as uploaded (yes)
        # Also skip rows that already have a video_id (prevents re-uploading the same row)
        if str(row.get("uploaded", "")).strip().lower() != "yes" and not row.get("video_id"):
            return int(idx), row.get("gdrive_link"), row.get("caption")
    return None, None, None

def mark_uploaded(index: int, video_id: Optional[str] = None, status: str = "yes"):
    df = _read_df()
    # create video_id column if missing
    if "video_id" not in df.columns:
        df["video_id"] = ""

    df.at[index, "uploaded"] = status
    if video_id:
        df.at[index, "video_id"] = video_id

    df.to_csv(CSV_FILE, index=False)
