# 台北雙星土地型自住房研究引擎：UI 規範與候選資料契約 (UI_SPEC)

> [!IMPORTANT]
> **狀態：UI-0 預覽版（待審查確認後凍結為 v1）**  
> 本規範定義本機研究引擎前端呈現之單一資料契約（View-Model）、版面架構、地圖呈現規格、圖層控制邏輯與雙模式（真實資料 vs 合成示範）運作規則。

---

## 1. 候選資料契約 (Candidate View-Model Contract)

為落實「UI 僅依契約呈現，不直接讀取底層散落欄位」之不可違反原則，前端一律透過 `CandidateViewModel` 進行資料繫結。  
在 **Phase 1a/UI-0** 階段，尚未實作之演算法與圖層欄位（評分、分級計算、路寬判定、街廓完整度、整合潛力、都更進度、交通等）**一律回傳字串 `"待實作"` 或 `ConditionStatus.UNKNOWN`，嚴禁填入假設值或偽造分數**。

### 1.1 欄位對應與呈現規格表

| 契約欄位代碼 (`key`) | 中文顯示名稱 | 內部型態 | 來源/衍生邏輯 (Phase 1a 現狀) | 預覽版真實模式呈現 | 示範模式呈現 (Fixture) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `candidate_id` | 候選編號 | `str` | `raw_transactions.serial_number` | 實值（如 `CAN_RPQNML...`） | `DEMO_A_001` 等 |
| `district` | 行政區 | `str` | `raw_transactions.district` | 實值（中正/大同/萬華/中山） | 實值 |
| `address_display` | 門牌/標的地址 | `str` | `transactions.address_raw` | 實值門牌（遮蔽或全揭露） | 示範地址 |
| `address_precision` | 地址解析精度 | `str` | `locations.precision` | `EXACT` / `NUMBER_RANGE` 等 | 各精度示範 |
| `is_location_overridden` | 人工核實標記 | `bool` | `locations.is_overridden` | `True` / `False` | `True` / `False` |
| `transaction_date_str` | 成交年月 | `str` | `transactions.transaction_date_str` | 實值（民國/西元） | 實值 |
| `total_price_w` | 登記總價 (萬元) | `float` | `transactions.total_price_twd / 10000` | 實值數值 | 實值數值 |
| `parking_price_w` | 車位總價 (萬元) | `float` | `transactions.parking_price_twd / 10000` | 實值數值（無則0） | 實值數值 |
| `property_price_w` | 房地淨價 (萬元) | `float` | `transactions.property_price_twd / 10000` | 實值數值（扣除車位價） | 實值數值 |
| `parking_included_flag` | 車位內含標記 | `bool` | `transactions.parking_price_included_in_total` | `True`（內含） / `False` | 示範標記 |
| `land_area_ping` | 土地面積 (坪) | `float` | `transactions.land_area_ping` (法定常數換算) | 實值數值（小數2位） | 實值數值 |
| `land_share_confidence` | 土地持份信心 | `str` | `transactions.land_share_confidence` | `HIGH` / `MEDIUM` / `LOW` | 各級示範 |
| `building_area_ping` | 建物面積 (坪) | `float` | `transactions.building_area_ping` | 實值數值 | 實值數值 |
| `building_age_years` | 屋齡 (年) | `Optional[float]` | 由 `calculation_as_of` 確定性運算 | 實值數值（缺值為 `"未知"`） | 實值數值 |
| `building_type` | 建物型態 | `str` | `transactions.building_type` | 公寓/華廈/大樓/透天 | 實值 |
| `distance_c1d1_m` | 雙星多邊形距離 (m) | `Optional[float]` | `candidate_properties.distance_point_m` | 實值公尺（點估計或區間重心） | 實值數值 |
| `distance_min_m` | 距離下界 (m) | `Optional[float]` | `candidate_properties.distance_min_m` | 實值（EXACT 則等於距離） | 實值數值 |
| `distance_max_m` | 距離上界 (m) | `Optional[float]` | `candidate_properties.distance_max_m` | 實值（EXACT 則等於距離） | 實值數值 |
| `distance_verified` | 距離已精確驗證 | `bool` | `candidate_properties.distance_verified` | `True` / `False` | `True` / `False` |
| `road_width_m` | 面臨道路寬度 (m) | `str` | **待 2b 道路圖層實作** | **`"待實作"`** | 示範數值（如 `12m`） |
| `road_status` | 道路寬度判定 | `str` | **待 2b 實作** | **`"待實作"`** | `PASS` / `NEAR` / `FAIL` |
| `zoning_code` | 使用分區 | `str` | **待 2b 分區圖層實作** | **`"待實作"`** | 示範代碼（商三/住三） |
| `block_integrity` | 街廓完整度 | `str` | **待 2b 實作** | **`"待實作"`** | `UNKNOWN` (依協議) |
| `integration_potential`| 鄰地整合潛力 | `str` | **待 2b 實作** | **`"待實作"`** | `UNKNOWN` (依協議) |
| `urban_renewal_status` | 都更整合進度 | `str` | **待 2c 實作** | **`"待實作"`** | 示範進度 |
| `station_distances` | 鄰近捷運站距離 | `dict` | **待 2a 實作** | **`"待實作"`** | 示範距離 |
| `candidate_grade` | 候選分級代碼 | `str` | **待 1b 實作** | **`"待實作"`** | `A` / `A*` / `B` / `B*` / `C` / `D` / `X` |
| `total_score` | 綜合評分 (0-100) | `str` | **待 1b 實作** | **`"待實作"`** | 示範得分（如 `88.5`） |
| `requires_manual_check`| 需人工查核標記 | `bool` | 依距離跨越門檻或缺值自動標記 | `True` / `False` | `True` / `False` |

---

## 2. 兩種運行模式架構 (Modes)

### 2.1 真實資料模式 (Real Data Mode)
- **資料來源**：本機 `data/processed/twintower.duckdb` 與 `config/`。
- **資料庫唯讀**：UI runtime 絕不呼叫外部網路 API，亦不向資料庫發出破壞性寫入。
- **嚴格誠實呈現**：
  - 頂部常駐醒目警告橫幅：
    > ⚠️ **預覽版：資料為單一期；C1/D1 幾何來源待驗證；分級與評分尚未實作**
  - 所有未實作欄位一律顯示 `"待實作"`，絕不顯示假分數。
- **資料匯出**：提供 CSV / GeoJSON 匯出功能。

### 2.2 示範模式 (Synthetic Demo Mode)
- **資料來源**：純記憶體常駐之合成測試案例 (`src/twintower/ui/fixtures.py`)，涵蓋規格第 13 節之完整情境：
  1. `DEMO_A_CORE`：方案 B 核心全符合（Grade A，總價 1850萬，土地 8.2坪，距離 320m，路寬 10m）。
  2. `DEMO_A_STAR_RANGE`：核心符合但帶號碼區間且跨門檻（Grade A*，延平北路一段 1~50號，距離 420~580m）。
  3. `DEMO_B_NEAR_PRICE`：總價落在軟上限區間（Grade B，總價 2150萬，其餘皆 PASS）。
  4. `DEMO_B_STAR_PARKING`：無 FAIL 但車位未拆分帶 UNKNOWN（Grade B*）。
  5. `DEMO_C_SINGLE_FAIL`：恰有一項 FAIL（Grade C，總價 2450萬超標，土地 11坪，距離 280m）。
  6. `DEMO_D_MULTI_FAIL`：兩項以上 FAIL（Grade D，總價 3200萬，距離 950m）。
  7. `DEMO_X_UNRESOLVED`：地址無法解析定位（Grade X）。
  8. `DEMO_PARTIAL_DATA`：部分欄位缺漏。
  9. `DEMO_SPARSE_DATA`：極度稀疏資料。
- **全頁醒目橫幅與浮水印**：
  - 頂部常駐紅色警示橫幅：
    > 🧪 **【合成示範資料，非真實成交】此模式所有物件均為假資料，僅供 UI 版面、樣式與互動驗證**
  - 地圖與表格皆標註合成警語。
- **寫入與匯出防護**：
  - **示範資料絕不寫入 DuckDB 資料庫**。
  - **示範模式下匯出按鈕強制停用（Disabled）**。

---

## 3. 版面配置與互動規範 (UI Layout)

```
+-----------------------------------------------------------------------------------+
| [頂部橫幅] 模式宣告 / 警告標語 / 歷史成交研究說明                                       |
+-----------------------------------------------------------------------------------+
| [統計指標列] 總候選數 | 核心符合 (A/A*) | 次級符合 (B/B*) | 需人工查核筆數 | 基準日          |
+--------------------+--------------------------------------------------------------+
| [側邊面板]          | [主畫面 - 上半部]                                             |
| 1. 運行模式切換      |  總覽地圖 (Folium + NLSC WMTS / OSM)                          |
|    (真實 / 示範)    |  - C1/D1 基地多邊形                                           |
| 2. 顯示主題切換      |  - 500m 核心圈 (綠) / 700m 次級圈 (橘)                        |
|    (淺色 / 深色)    |  - 候選標的點 (依等級上色，A*/B* 虛線外框)                     |
| 3. 底圖切換         |  - 號碼區間多邊形 (Envelope 矩形)                              |
| 4. 篩選控制項        |  - 點擊標記與列表表格雙向聯動                                   |
|    - 行政區多選      +--------------------------------------------------------------+
|    - 總價/淨價滑桿   | [主畫面 - 下半部]                                             |
|    - 土地坪數滑桿   |  候選標的列表 (互動表格)                                       |
|    - 距離滑桿       |  - 支援排序、篩選、選取單筆標的                                |
| 5. 圖層面板 (Layer) |  - 欄位包含：等級、地址、淨價、土地坪數、距離、道路、分級標籤   |
|    - 分類、開關、筆數+--------------------------------------------------------------+
|    - TDX: 待啟用    | [抽屜 / 底部詳情面版] 單筆候選深入診斷                          |
|                     |  - 物件總覽 (基本登錄資料)                                     |
|                     |  - 「為何符合」條件雷達/核取檢視 (✓ PASS / ⚠ NEAR / ✗ FAIL)    |
|                     |  - 完整證據表 (欄位、數值、觀察狀態、來源出處、核實註記)        |
|                     |  - 局部精細街廓地圖 (含基地相對位置與臨路示意)                 |
+--------------------+--------------------------------------------------------------+
```

---

## 4. 地圖視覺與幾何語意規範

1. **雙星 C1/D1 基地**：
   - 繪製官方都市計畫特定專用區 C1 (FID 802) 與 D1 (FID 803) 基地多邊形邊界（深藍填色，紅色邊框）。
   - 誠實註記：「C1/D1 幾何來源：臺北市都市計畫主要計畫特定專用區圖層，待官方進一步公報校準」。
2. **門檻緩衝圈**：
   - `500m` 核心範圍圈：半透明綠色外框線。
   - `700m` 次級範圍圈：半透明橘黃色外框線。
3. **標記幾何語意**：
   - **`EXACT` 精確點**：圓形實心標記（CircleMarker）。
   - **`NUMBER_RANGE` / `ROAD_SEGMENT` 區間**：半透明外包矩形框（Bounding Box）或多邊形，中心標註重心點。
   - **分級視覺標記**：
     - `Grade A`：綠色實心圓（🟢）。
     - `Grade A*`：綠色空心圓帶虛線外框（⭕，代表含區間不確定性或待查核）。
     - `Grade B`：藍色實心圓（🔵）。
     - `Grade B*`：藍色空心圓帶虛線外框（帶 UNKNOWN 或車位未拆）。
     - `Grade C`：黃色實心圓（🟡）。
     - `Grade D`：紅色實心圓（🔴）。
     - `Grade X`：灰色問號圓（⚪，無法定位）。

---

## 5. 圖層控制面板 (Layer Panel) 規範

圖層面板分類與狀態顯示原則：
1. **基礎地理與研究核心 (Core Layers)**：
   - C1/D1 官方基地幾何（預設開啟，`ENABLED`）
   - 500m / 700m 距離圈（預設開啟，`ENABLED`）
   - 候選住宅標的成交點（預設開啟，`ENABLED`）
2. **都市規劃與道路 (Phase 2b - Planning & Roads)**：
   - 8米以上計畫道路圖層（預設開啟，未到期前標記 `待 2b 啟用`）
   - 都市計畫使用分區圖層（預設關閉，標記 `待 2b 啟用`）
3. **大眾運輸圖層 (Transit Layers)**：
   - 捷運車站出入口 (免金鑰開放資料，Phase 2a 啟用)
   - 公車站位點 (免金鑰開放資料，Phase 2a 啟用)
   - **TDX 整合運輸圖層（高鐵/台鐵/公車即時動態）**：狀態一律明確標記為：
     > 🔒 **待啟用（NOT_ENABLED）** — 延後至 Phase T 評估額度並取得授權後啟用。
4. **重大建設圖層 (Phase 2c - Major Projects)**：
   - 西區門戶計畫、雙子星、E1/E2、郵政雙塔等空間邊界（標記 `待 2c 啟用`）。

---

## 6. 色彩與主題代碼表 (Design Tokens)

| Token 代碼 | 淺色主題 (Light) | 深色主題 (Dark) | 語意說明 |
| :--- | :--- | :--- | :--- |
| `--bg-main` | `#FFFFFF` | `#121212` | 主頁面背景 |
| `--bg-card` | `#F8F9FA` | `#1E1E1E` | 卡片與面板背景 |
| `--border-color` | `#DEE2E6` | `#333333` | 分隔線與框線 |
| `--text-primary` | `#212529` | `#E0E0E0` | 主要文字 |
| `--text-muted` | `#6C757D` | `#888888` | 次要/備註文字 |
| `--grade-a` | `#28A745` | `#2ECC71` | Grade A (核心通過) |
| `--grade-b` | `#007BFF` | `#3498DB` | Grade B (次級/接近) |
| `--grade-c` | `#FFC107` | `#F1C40F` | Grade C (單項不符) |
| `--grade-d` | `#DC3545` | `#E74C3C` | Grade D (多項不符) |
| `--grade-x` | `#6C757D` | `#95A5A6` | Grade X (未知/無坐標) |
| `--c1d1-anchor` | `#1F4E79` | `#5DADE2` | 雙星 C1/D1 基地 |
| `--radius-500` | `#28A745` | `#2ECC71` | 500m 距離圈 |
| `--radius-700` | `#FD7E14` | `#E67E22` | 700m 距離圈 |
| `--status-pass` | `#28A745` | `#2ECC71` | PASS (符合) |
| `--status-near` | `#FD7E14` | `#E67E22` | NEAR (接近/寬鬆通過) |
| `--status-fail` | `#DC3545` | `#E74C3C` | FAIL (不符合) |
| `--status-unknown`| `#6C757D`| `#95A5A6` | UNKNOWN (未知/待查) |
