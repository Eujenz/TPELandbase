"""
[PROBE SCRIPT - 非正式應用程式碼 / 研究探測用]
功能: 檢驗 MOI 實價登錄下載檔之涵蓋期間、manifest 內容與交易日期分布，
並測試歷年季度/發布下載端點。
"""

import zipfile
import pandas as pd
import io

zip_path = "data/raw/probes/lvr_landcsv.zip"

with zipfile.ZipFile(zip_path) as z:
    # 1. Inspect manifest.csv
    output_lines = []
    if "manifest.csv" in z.namelist():
        manifest_text = z.read("manifest.csv").decode("utf-8", errors="replace")
        output_lines.append("=== manifest.csv content ===")
        output_lines.append(manifest_text)
    
    # 2. Inspect a_lvr_land_a.csv (Taipei main buy/sell)
    df = pd.read_csv(z.open("a_lvr_land_a.csv"), encoding="utf-8", skiprows=[1], low_memory=False)
    output_lines.append(f"\nTotal Taipei transactions in current file: {len(df)}")
    
    # Date column: 交易年月日 (ROC format YYYMMDD)
    dates = df["交易年月日"].dropna().astype(str).str.strip()
    valid_dates = dates[dates.str.match(r"^\d{6,7}$")]
    output_lines.append(f"Valid date records: {len(valid_dates)} / {len(dates)}")
    
    # Parse ROC year
    years = valid_dates.apply(lambda d: int(d[:-4]) if len(d) in (6, 7) else None).dropna()
    output_lines.append("\nTransaction Count by ROC Year (民國年):")
    for yr, cnt in years.value_counts().sort_index().items():
        output_lines.append(f"  民國 {yr} 年 (西元 {yr+1911} 年): {cnt} 筆")
    
    output_lines.append(f"\nEarliest transaction date: {valid_dates.min()}")
    output_lines.append(f"Latest transaction date: {valid_dates.max()}")

with open("scripts/probes/moi_period_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))
print("Saved summary to scripts/probes/moi_period_summary.txt")
