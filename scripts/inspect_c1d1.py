import pandas as pd
from pyproj import Transformer

df = pd.read_csv('data/raw/probes/taipei_doorplate.csv')
c1_d1_candidates = df[
    (df['街路段'].str.contains('鄭州路', na=False) & df['號'].str.contains('８號', na=False)) |
    (df['街路段'].str.contains('北平西路', na=False) & df['號'].str.contains('３號|７號', na=False))
]

transformer = Transformer.from_crs("EPSG:3826", "EPSG:4326", always_xy=True)

with open('scripts/c1d1_candidates.txt', 'w', encoding='utf-8') as f:
    for _, r in c1_d1_candidates.iterrows():
        x = r['橫座標']
        y = r['縱座標']
        lon, lat = transformer.transform(x, y)
        line = f"District: {r['鄉鎮市區代碼']} | Road: {r['街路段']} | No: {r['號']} | TWD97 (X, Y): ({x:.3f}, {y:.3f}) | WGS84 (lon, lat): ({lon:.6f}, {lat:.6f})\n"
        f.write(line)
        print(line.strip())
