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
        if str(row.get("uploaded", "")).strip().lower() != "yes":
            return int(idx), row.get("gdrive_link"), row.get("caption")
    return None, None, None

def mark_uploaded(index: int):
    df = _read_df()
    df.at[index, "uploaded"] = "yes"
    df.to_csv(CSV_FILE, index=False)
