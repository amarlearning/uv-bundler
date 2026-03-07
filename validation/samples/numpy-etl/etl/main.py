from __future__ import annotations

from etl.transform import compute_regional_stats


def run() -> int:
    stats = compute_regional_stats()
    print(f"ETL complete: mean_sales={stats['mean']:.1f} peak_region={stats['peak']}")
    return 0
