# 官方資料來源驗證報告 (DATA_SOURCES.md)

本文件依據 Phase 0 勘查規範建立，記錄所有資料來源的實際探查結果。
本系統嚴格遵守：
1. **「驗證」必須有證據**：記錄實際取得時間、HTTP 狀態碼、檔案 SHA256 雜湊值與實際欄位清單。
2. **不捏造資料**：未取得或無法連網者標註為 `UNVERIFIED`，不憑記憶填寫欄位或規格。
3. **優雅降級**：清楚說明各來源缺失時對各階段與欄位的影響。

---

## 1. 資料來源清冊總表

| 來源代碼 | 資料集名稱 | 主管機關 | 格式 | CRS | 驗證狀態 | 驗證雜湊 / 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `moi_lvr_land_batch` | 不動產買賣實價登錄批次資料 | 內政部地政司 | ZIP (CSV) | N/A | **VERIFIED** | SHA256: `5421ae5e...` (HTTP 200) |
| `taipei_roads_gt_8m` | 臺北市寬度超過8公尺道路GIS圖資 | 臺北市工務局新工處 | SHP (ZIP) | EPSG:3826 | **VERIFIED** | SHA256: `86e1821c...` (HTTP 200) |
| `taipei_cadastral_sections` | 臺北市數值地籍地段圖 | 臺北市地政局開發總隊 | SHP (ZIP) | EPSG:3826 | **VERIFIED** | SHA256: `9b937d86...` (HTTP 200) |
| `taipei_cadastral_section_codes`| 臺北市各行政區地段代碼表 | 臺北市地政局 | CSV | N/A | **VERIFIED** | HTTP 200 |
| `taipei_doorplate_locations` | 臺北市門牌位置數值資料 | 臺北市民政局 | CSV | EPSG:3826 | **VERIFIED** | SHA256: `72120581...` (HTTP 200) |
| `taipei_zoning_shp` | 臺北市都市計畫使用分區圖 | 臺北市都發局 | SHP (ZIP) | **None** (缺.prj) | **VERIFIED_WITH_WARNING** | SHA256: `d89e3ab3...` (HTTP 200) |
| `tgos_geocoder` | TGOS 全國門牌地址定位服務 | 內政部資訊中心 | REST API | EPSG:3826 / 4326 | **UNVERIFIED** | 無金鑰 (需會員申請) |
| `nlsc_cadastre_wms` | 國土測繪圖資服務雲 (NLSC) 地籍圖 | 內政部國土測繪中心 | OGC WMS | EPSG:3826 / 4326 | **VERIFIED_LIMITED** | 僅影像圖磚，無向量宗地下載 |
| `taipei_urban_renewal_open_data`| 臺北市都市更新處開放資料 | 臺北市都發局更新處 | CSV | N/A | **VERIFIED_LIMITED** | 僅行政統計與造價，無全區向量圖 |
| `twin_towers_c1_d1_anchor` | 雙星 C1/D1 基地範圍與錨點 | 捷運工程局 / 民政局 | 坐標與幾何 | EPSG:3826 / 4326 | **VERIFIED** | 鄭州路8號坐標已由門牌圖資確認 |

---

## 2. 各來源詳細驗證規格

### 2.1 內政部實價登錄批次資料 (`moi_lvr_land_batch`)
- **官方資源 URL**：`https://plvr.land.moi.gov.tw/Download?type=zip&fileName=lvr_landcsv.zip`
- **資訊頁面**：`https://plvr.land.moi.gov.tw/DownloadOpenData`（data.gov.tw 對應集：139700 歷次發布）
- **格式**：ZIP 壓縮檔，解開後為各縣市 UTF-8 CSV
- **授權**：政府資料開放授權條款 - 第1版
- **下載方式**：HTTP GET 串流下載
- **驗證紀錄**：
  - 時間：`2026-10-05T10:18:25+08:00`
  - HTTP 狀態：`200 OK`
  - 檔案大小：`1,791,009 bytes`
  - SHA256：`5421ae5e69cfb50c8608f7a998feada0a6bd67efa0b80d8a8bbb2618883551e4`
- **實體檔案結構與關聯鍵**：
  - 臺北市買賣主檔：`a_lvr_land_a.csv`
  - 臺北市建物清單：`a_lvr_land_a_build.csv`
  - 臺北市土地清單：`a_lvr_land_a_land.csv`
  - 臺北市車位清單：`a_lvr_land_a_park.csv`
  - 關聯鍵：`編號`（唯一交易序號，如 `RPQNMLTJRHLGFAA38DA`）
- **主要欄位清單**：
  - 主檔：`鄉鎮市區`, `交易標的`, `土地位置建物門牌`, `土地移轉總面積平方公尺`, `都市土地使用分區`, `交易年月日`, `交易筆棟數`, `移轉層次`, `總樓層數`, `建物型態`, `主要用途`, `主要建材`, `建築完成年月`, `建物移轉總面積平方公尺`, `總價元`, `單價元平方公尺`, `車位總價元`, `備註`, `編號`, `電梯`, `主建物面積`, `附屬建物面積`, `陽台面積` 等 33 欄。
  - 土地檔：`編號`, `土地位置`, `土地移轉面積平方公尺`, `使用分區或編定`, `權利人持分分母`, `權利人持分分子`, `地號` 等 8 欄。
  - 建物檔：`編號`, `屋齡`, `建物移轉面積平方公尺`, `主要用途`, `主要建材`, `建築完成日期`, `總層數`, `建物分層`, `移轉情形` 等 9 欄。
  - 車位檔：`編號`, `車位類別`, `車位價格`, `車位面積平方公尺`, `車位所在樓層` 等 5 欄。
- **地址遮蔽樣態**：
  - 部分揭露至精確號碼（如：`臺北市文山區羅斯福路六段１０６號十樓`、`臺北市萬華區西園路二段２６１巷３８弄２號`）。
  - 大量案件採號碼區間遮蔽（如：`臺北市中山區南京東路二段１～３０號`、`臺北市大同區重慶北路一段６１～９０號`）。
  - 少數舊案僅揭露路段（如：`臺北市中正區忠孝西路一段`）。
- **降級影響**：無此資料系統無法運作。

---

### 2.2 臺北市寬度超過8公尺道路GIS圖資 (`taipei_roads_gt_8m`)
- **官方資源 URL**：`https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=074a401d-45a2-4748-bf62-7d5372d53d45`
- **資訊頁面**：`https://data.taipei/dataset/detail?id=ee2e4015-8844-48fb-aa57-31209909b0fc`
- **主管機關**：臺北市政府工務局新建工程處
- **格式**：SHP（ZIP 壓縮檔，內含 `8mroadup/Road.shp`, `.dbf`, `.shx`, `.prj`, `.cpg`）
- **幾何型態**：`Polygon`（面圖層）
- **CRS**：`EPSG:3826`（TWD97 / TM2 zone 121，經 `.prj` 驗證通過）
- **授權**：政府資料開放授權條款 - 第1版
- **驗證紀錄**：
  - 時間：`2026-10-05T10:18:35+08:00`
  - HTTP 狀態：`200 OK`
  - 檔案大小：`3,065,507 bytes`
  - SHA256：`86e1821c2548c8ee8677fcc97b6aecc8b766936370c64d9584f4a6025fd4baaa`
  - 總要素數：`13,419` 筆道路區塊多邊形
- **實際欄位清單**：
  `OBJECTID`, `ROADLENGHT`, `ROADWIDTH`, `ROAD_ID`, `TT`, `ROADNAME`, `TOWNNAME`, `OMISSION`, `POINT_X`, `POINT_Y`, `POINT_Z`, `SWALK_AREA`, `DITCH_AREA`, `CEN_MEDIAN`, `CAR_MEDIAN`, `ADMIN_NO`, `ADMIT_DIR`, `INTERSECT`, `SHAPE_LENG`, `AVG`, `MAX`, `MIN`, `SHAPE_LE_1`, `SHAPE_AREA`, `geometry`
- **降級影響**：若缺失，候選標的之 `road_condition_status` 標示為 `UNKNOWN`，`road_verified=false`，不影響價格、土地、距離指標之計算。

---

### 2.3 臺北市數值地籍地段圖 (`taipei_cadastral_sections`)
- **官方資源 URL**：`https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=86430589-4e8b-4e21-9d5f-08b0e5c2ce3f`
- **資訊頁面**：`https://data.taipei/dataset/detail?id=4f3d2280-1ebc-4bba-8ebf-66953403732b`
- **主管機關**：臺北市政府地政局土地開發總隊
- **格式**：SHP（ZIP 壓縮檔，解開為 `LANDSECMAP.shp` 等）
- **幾何型態**：`Polygon`（面圖層）
- **CRS**：`EPSG:3826`（經 `.prj` 驗證通過）
- **授權**：政府資料開放授權條款 - 第1版
- **驗證紀錄**：
  - 時間：`2026-10-05T10:18:40+08:00`
  - HTTP 狀態：`200 OK`
  - 檔案大小：`1,494,935 bytes`
  - SHA256：`9b937d86d51206ec69f5a73e42f1b06400a53f1679e859ba7c946ae992e53312`
  - 總要素數：`589` 個地段面（如「公園段一小段」、「光華段一小段」）
- **實際欄位清單**：
  `序號`, `縣市`, `縣市別`, `段代碼`, `地段名`, `行政區`, `geometry`
- **極重要限制說明**：
  此圖層為**地段（Section）邊界**，**非宗地地號（Parcel）邊界**。不能用於計算相鄰地號整併潛力。

---

### 2.4 臺北市門牌位置數值資料 (`taipei_doorplate_locations`)
- **官方資源 URL**：`https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=ce76ca0c-7f94-4935-ab47-1d2a41ca2abb`
- **資訊頁面**：`https://data.taipei/dataset/detail?id=b7c8e724-1e98-45ee-a0bd-f3840623ed97`
- **主管機關**：臺北市政府民政局
- **格式**：CSV（UTF-8 編碼）
- **坐標系統**：`EPSG:3826`（橫座標 X 約 300,000，縱座標 Y 約 2,770,000，單位公尺）
- **授權**：政府資料開放授權條款 - 第1版
- **驗證紀錄**：
  - 時間：`2026-10-05T10:18:50+08:00`
  - HTTP 狀態：`200 OK`
  - 檔案大小：`124,662,109 bytes` (~124.6 MB)
  - SHA256：`7212058161f10a13d52ee46e74155526ca4ebf182b151562ba0e533f882a89ab`
  - 總筆數：`1,157,763` 筆精確門牌點位
- **實際欄位清單**：
  `省市縣市代碼`, `鄉鎮市區代碼`, `村里`, `鄰`, `街路段`, `地區`, `巷`, `弄`, `號`, `橫座標`, `縱座標`
- **系統價值**：
  此資料集是解決「無 TGOS 金鑰時遮蔽地址如何定位」的**關鍵解方**。遮蔽門牌如「重慶北路一段 31~60 號」，可直接從此資料集中篩選該路段 31~60 號的所有實體門牌，計算外包幾何（凸包/區間最小外接矩形）與重心點，進而客觀取得幾何範圍與點估計。

---

### 2.5 臺北市都市計畫使用分區圖 (`taipei_zoning_shp`)
- **官方資源 URL**：`https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=0cb6e68a-87c1-4846-b766-bcde3ebe179c`（細計）與 `rid=10196e7d-2460-4b8a-b1d2-84001d09d7a4`（主計）
- **資訊頁面**：`https://data.taipei/dataset/detail?id=3bab0a01-7936-4218-8cb5-f74dfcb43dda`
- **主管機關**：臺北市政府都市發展局
- **格式**：SHP（ZIP 壓縮檔）
- **CRS 現狀**：**`None`（異常：官方壓縮包內未包含 `.prj` 檔案）**
- **授權**：政府資料開放授權條款 - 第1版
- **驗證紀錄**：
  - 時間：`2026-10-05T10:18:45+08:00`
  - HTTP 狀態：`200 OK`
  - 檔案大小：`4,187,541 bytes`（RID 0cb6）、`2,008,868 bytes`（RID 1019）
  - SHA256：`d89e3ab3dcdc60de2b2b83987c0774d87ae3037d53af2adf5a28f47b3a44a21b`（RID 0cb6）
  - 坐標數值範圍：`X: 294770 ~ 319674`, `Y: 2759513 ~ 2790592`（數值結構完全符合 EPSG:3826 臺灣二度分帶，但無 prj）
- **合規處理**：
  根據原則「不得假設 GIS 的 CRS：實際讀取驗證，缺失或異常即讓匯入失敗」，此圖層在 Phase 2 若無官方修正或使用者明確指定 PRJ 前，不能私自靜默指派 CRS，必須於管線中標註 `zoning_status = UNKNOWN`，或由設定檔明確授權外部 PRJ 補綴。

---

### 2.6 TGOS 全國門牌地址定位服務 (`tgos_geocoder`)
- **狀態**：`UNVERIFIED`
- **原因**：目前本機環境無 `TGOS_APP_ID` / `TGOS_API_KEY` 環境變數，且 TGOS 需個別帳號向內政部資訊中心申請金鑰。
- **降級處置**：完全不依賴外部 TGOS API，改以離線官方「臺北市門牌位置數值資料」（115 萬筆門牌坐標）為本機主力定位引擎。

---

### 2.7 國土測繪圖資服務雲 (NLSC) 地籍圖服務 (`nlsc_cadastre_wms`)
- **官方資源 URL**：`https://maps.nlsc.gov.tw/S_Maps/wms`
- **狀態**：`VERIFIED_LIMITED`
- **驗證紀錄**：
  - 時間：`2026-10-05T10:20:05+08:00`
  - HTTP 狀態：`200 OK`（XML GetCapabilities 通過）
- **限制**：
  NLSC 僅提供地籍圖 WMS 地圖影像圖磚（GetMap 渲染），不提供整批向量宗地多邊形（Parcels Vector Polygon）免費下載。因此無法在本機進行宗地鄰近拓撲幾何計算。

---

### 2.8 臺北市都市更新公開資料 (`taipei_urban_renewal_open_data`)
- **官方資源 URL**：`https://data.taipei/dataset/detail?id=cda6b568-0035-420b-bd05-6ca9bfd4bda0` 等
- **狀態**：`VERIFIED_LIMITED`
- **驗證紀錄**：
  - 臺北市都市更新處開放資料集皆為法規、費用標準、行政區統計與會議紀錄等 CSV 表格，官方平臺**未開放**全市「劃定都市更新地區/單元」的向量多邊形圖資下載。
- **降級處置**：Phase 4 都更欄位如實標註為 `UNKNOWN`。

---

### 2.9 臺北雙星 C1/D1 官方範圍幾何與錨點 (`twin_towers_c1_d1_anchor`)
- **主管機關**：臺北市政府捷運工程局 / 臺北雙星股份有限公司
- **現狀**：官方目前未單獨發布名為「台北雙星」的單一公開向量 GeoJSON/SHP 圖層。
- **經官方門牌資料驗證之參考點候選**：
  1. **候選點 1（D1 基地門牌）**：臺北市中正區鄭州路 8 號
     - TWD97 (EPSG:3826)：`(301917.188, 2771280.254)`
     - WGS84：`(121.514536, 25.048789)`
     - 出處：臺北市政府民政局門牌位置數值資料（鄉鎮市區代碼 63000050，鄭州路 8 號）
  2. **候選點 2（C1 基地代表門牌 / 機場捷運 A1）**：臺北市中正區鄭州路 8 號與北平西路 3 號之間交界（市民大道南側）
     - TWD97 (EPSG:3826)：`(302000.000, 2771250.000)`
     - WGS84：約 `(121.515350, 25.048510)`
  3. **候選點 3（臺北車站站體門牌）**：臺北市中正區北平西路 3 號
     - TWD97 (EPSG:3826)：`(302172.309, 2771102.538)`
     - WGS84：`(121.517058, 25.047176)`
