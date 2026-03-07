from __future__ import annotations

import numpy as np
import pandas as pd


def compute_regional_stats() -> dict[str, object]:
    """Aggregate regional sales data using pandas and numpy."""
    data = {
        "region": ["us-east", "us-west", "eu-west", "ap-south"],
        "sales": [1200.0, 850.0, 1350.0, 920.0],
    }
    df = pd.DataFrame(data)
    return {
        "mean": float(np.mean(df["sales"])),
        "peak": str(df.loc[df["sales"].idxmax(), "region"]),
    }
