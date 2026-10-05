"""
[PROBE SCRIPT - 非正式應用程式碼 / 研究探測用]
功能: 實測臺北市住宅房地交易的 address_precision 分布 (依成交年份)
並探查 MOI 地址遮蔽規則 (區間表示法、單雙號、巷弄門牌樣態)
"""

import zipfile
import pandas as pd
import re
import io

zip_path = "data/raw/probes/lvr_landcsv.zip"

with zipfile.ZipFile(zip_path) as z:
    df = pd.read_csv(z.open("a_lvr_land_a.csv"), encoding="utf-8", skiprows=[1], low_memory=False)

output = []
output.append(f"Total raw transactions: {len(df)}")

# Filter residential property transactions (房地交易)
res_types = ["住宅大樓(11層含以上有電梯)", "華廈(10層含以下有電梯)", "公寓(5樓含以下無電梯)", "透天厝"]
target_types = ["房地(土地+建物)", "房地(土地+建物)+車位"]

df_res = df[df["交易標的"].isin(target_types) & df["建物型態"].isin(res_types)].copy()
output.append(f"Residential transactions: {len(df_res)}")

# Parse ROC Year
def extract_year(d_str):
    if pd.isna(d_str):
        return "UNKNOWN"
    d_str = str(d_str).strip()
    if len(d_str) in (6, 7):
        return int(d_str[:-4])
    return "INVALID"

df_res["roc_year"] = df_res["交易年月日"].apply(extract_year)

# Address precision classification logic
def classify_precision(addr):
    if pd.isna(addr):
        return "UNRESOLVED"
    addr = str(addr).strip()
    if not addr:
        return "UNRESOLVED"
    
    # Check for range: e.g. １～３０號, 31~60號, 1-30號
    if re.search(r'[０-９0-9]+[～~至\-][０-９0-9]+號', addr):
        return "NUMBER_RANGE"
    
    # Check for exact doorplate: e.g. １０６號, 2號
    if re.search(r'[０-９0-9]+號', addr):
        return "EXACT"
    
    # Check if road or lane exists
    if re.search(r'(路|街|大道|巷|弄)', addr):
        return "ROAD_SEGMENT"
    
    if re.search(r'(區)', addr):
        return "DISTRICT_ONLY"
    
    return "UNRESOLVED"

df_res["precision"] = df_res["土地位置建物門牌"].apply(classify_precision)

# Precision by year table
ct = pd.crosstab(df_res["roc_year"], df_res["precision"], margins=True)
output.append("\n=== Address Precision Distribution by ROC Year ===")
output.append(ct.to_string())

# Inspect samples of NUMBER_RANGE to check odd/even and format
range_samples = df_res[df_res["precision"] == "NUMBER_RANGE"]["土地位置建物門牌"].head(20).tolist()
output.append("\n=== Sample NUMBER_RANGE Addresses ===")
for s in range_samples:
    output.append(f"  {s}")

exact_samples = df_res[df_res["precision"] == "EXACT"]["土地位置建物門牌"].head(10).tolist()
output.append("\n=== Sample EXACT Addresses ===")
for s in exact_samples:
    output.append(f"  {s}")

with open("scripts/probes/address_precision_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("Saved report to scripts/probes/address_precision_report.txt")
