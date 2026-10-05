"""
UI-0 靜態預覽 HTML 產生器 (Generate Standalone HTML Previews)
產出 4 種組合：
1. 真實模式 - 淺色主題 (Real Light)
2. 真實模式 - 深色主題 (Real Dark)
3. 示範模式 - 淺色主題 (Demo Light)
4. 示範模式 - 深色主題 (Demo Dark)
供使用者立即以瀏覽器檢閱版面、樣式、地圖圖層與資訊密度。
"""

import json
import os
import duckdb
from twintower.ui.fixtures import DEMO_CANDIDATES
from twintower.ui.map_views import build_overview_map
from twintower.ui.view_model import CandidateViewModel


def load_real_candidates(db_path: str = "data/processed/twintower.duckdb"):
    if not os.path.exists(db_path):
        return []
    con = duckdb.connect(db_path, read_only=True)
    query = """
        SELECT 
            c.candidate_id, c.district, c.address, c.address_precision,
            c.transaction_date, c.total_price_twd, c.property_price_twd,
            c.parking_price_twd, c.parking_price_included_in_total,
            c.land_area_ping, c.land_share_confidence, c.building_area_ping,
            c.building_age_years, c.distance_point_m, c.distance_min_m,
            c.distance_max_m, c.distance_verified, c.requires_manual_verification,
            c.distance_threshold_status,
            l.lat_wgs84, l.lon_wgs84, l.min_x_twd97, l.min_y_twd97,
            l.max_x_twd97, l.max_y_twd97, l.is_overridden,
            t.building_type
        FROM candidate_properties c
        LEFT JOIN locations l ON c.location_id = l.location_id
        LEFT JOIN transactions t ON c.transaction_id = t.transaction_id
        ORDER BY c.distance_point_m ASC NULLS LAST
    """
    df = con.execute(query).fetchdf()
    con.close()
    return [CandidateViewModel.from_real_duckdb_row(r) for r in df.to_dict(orient="records")]


def generate_html_preview(
    candidates,
    is_demo: bool,
    is_dark: bool,
    output_path: str,
):
    # 建立地圖 HTML
    f_map = build_overview_map(candidates, is_demo_mode=is_demo, is_dark_theme=is_dark)
    map_html = f_map.get_root().render()

    bg_main = "#121212" if is_dark else "#FFFFFF"
    bg_card = "#1E1E1E" if is_dark else "#F8F9FA"
    bg_side = "#181818" if is_dark else "#F1F3F5"
    text_color = "#E0E0E0" if is_dark else "#212529"
    border_color = "#333333" if is_dark else "#DEE2E6"
    th_bg = "#2A2A2A" if is_dark else "#E9ECEF"

    mode_title = "合成示範模式 (Demo Fixtures)" if is_demo else "真實資料模式 (Phase 1a)"
    theme_title = "深色主題 (Dark)" if is_dark else "淺色主題 (Light)"

    banner_html = ""
    watermark_html = ""
    if is_demo:
        banner_html = """
        <div style="background-color: #F8D7DA; color: #721C24; border: 1px solid #F5C6CB; padding: 12px 18px; border-radius: 8px; margin-bottom: 16px; font-weight: bold;">
            🧪 【合成示範資料，非真實成交】此模式所有物件均為合成假資料（依規格第 13 節建構），僅供驗證版面配置、視覺著色與互動流程。示範資料不存入資料庫，匯出功能已停用。
        </div>
        """
        watermark_html = """
        <div style="position: fixed; bottom: 20px; right: 25px; background: rgba(220, 53, 69, 0.9); color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 13px; z-index: 99999; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
            🧪 合成示範資料，非真實成交
        </div>
        """
    else:
        banner_html = """
        <div style="background-color: #FFF3CD; color: #856404; border: 1px solid #FFEEBA; padding: 12px 18px; border-radius: 8px; margin-bottom: 16px;">
            ⚠️ <b>預覽版宣告：</b> 資料為單一期歷史實價登錄；C1/D1 幾何來源為臺北市都市計畫特定專用區圖層（待公報進一步校準）；距離為多邊形外緣邊界測算；<b>分級與評分尚未實作（依契約顯示「待實作」）</b>。
        </div>
        """

    # 計算統計數字
    total_count = len(candidates)
    core_count = sum(1 for c in candidates if c.distance_c1d1_m is not None and c.distance_c1d1_m <= 500)
    near_count = sum(1 for c in candidates if c.distance_c1d1_m is not None and 500 < c.distance_c1d1_m <= 700)
    manual_count = sum(1 for c in candidates if c.requires_manual_check)

    # 產生表格列
    table_rows_html = ""
    for c in candidates:
        badge_color = "#28A745" if c.candidate_grade in ("A", "A*") else ("#007BFF" if c.candidate_grade in ("B", "B*") else ("#FFC107" if c.candidate_grade == "C" else ("#DC3545" if c.candidate_grade == "D" else "#6C757D")))
        dist_str = f"{c.distance_c1d1_m:.1f} m" if c.distance_c1d1_m is not None else "未知"
        table_rows_html += f"""
        <tr style="border-bottom: 1px solid {border_color};">
            <td style="padding: 10px 12px;"><b>{c.candidate_id}</b></td>
            <td style="padding: 10px 12px;"><span style="background: {badge_color}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;">{c.candidate_grade}</span></td>
            <td style="padding: 10px 12px;">{c.total_score}</td>
            <td style="padding: 10px 12px;">{c.district}</td>
            <td style="padding: 10px 12px;">{c.address_display}</td>
            <td style="padding: 10px 12px; font-weight: bold; color: {'#5DADE2' if is_dark else '#0056B3'};">{c.property_price_w} 萬</td>
            <td style="padding: 10px 12px; font-weight: bold;">{c.land_area_ping} 坪</td>
            <td style="padding: 10px 12px;"><small>{c.land_share_confidence}</small></td>
            <td style="padding: 10px 12px;">{dist_str}</td>
            <td style="padding: 10px 12px;"><small>{c.address_precision}</small></td>
            <td style="padding: 10px 12px;">{c.road_width_m}</td>
            <td style="padding: 10px 12px;">{'⚠️ 需查核' if c.requires_manual_check else '否'}</td>
        </tr>
        """

    # 第一筆物件作為詳情展示
    first_c = candidates[0] if candidates else None
    evidence_rows_html = ""
    why_matches_html = ""
    if first_c:
        for ev in first_c.evidence_rows:
            evidence_rows_html += f"""
            <tr style="border-bottom: 1px solid {border_color};">
                <td style="padding: 8px 10px;"><b>{ev['欄位']}</b></td>
                <td style="padding: 8px 10px;">{ev['數值']}</td>
                <td style="padding: 8px 10px;"><small>{ev['狀態']}</small></td>
                <td style="padding: 8px 10px;"><small>{ev['來源']}</small></td>
                <td style="padding: 8px 10px;">{ev['驗證']}</td>
            </tr>
            """
        for cond, stat in first_c.condition_checks.items():
            icon = "✅" if stat == "PASS" else ("⚠️" if stat == "NEAR" else ("❌" if stat == "FAIL" else "❓"))
            why_matches_html += f"<li style='margin-bottom: 6px;'>{icon} <b>{cond}</b>: {stat}</li>"

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>台北雙星土地型自住房研究引擎 - {mode_title} ({theme_title})</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans TC", sans-serif;
            background-color: {bg_main};
            color: {text_color};
        }}
        .app-container {{
            display: flex;
            min-height: 100vh;
        }}
        .sidebar {{
            width: 320px;
            background-color: {bg_side};
            border-right: 1px solid {border_color};
            padding: 24px 20px;
            box-sizing: border-box;
            flex-shrink: 0;
        }}
        .content {{
            flex-grow: 1;
            padding: 24px 32px;
            overflow-y: auto;
        }}
        .metric-box {{
            background: {bg_card};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 14px 18px;
            text-align: center;
            flex: 1;
            margin-right: 12px;
        }}
        .metric-box:last-child {{ margin-right: 0; }}
        .metric-val {{ font-size: 22px; font-weight: bold; margin-top: 4px; }}
        .metric-label {{ font-size: 13px; color: {'#AAA' if is_dark else '#666'}; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13.5px;
            background: {bg_card};
            border: 1px solid {border_color};
            border-radius: 8px;
            overflow: hidden;
        }}
        th {{
            background: {th_bg};
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid {border_color};
        }}
        .tag-pill {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin-right: 4px;
        }}
    </style>
</head>
<body>
    {watermark_html}
    <div class="app-container">
        <!-- 側邊面板 -->
        <div class="sidebar">
            <h2 style="margin-top:0; font-size: 18px;">🏢 台北雙星研究引擎</h2>
            <div style="font-size: 12px; color: {'#AAA' if is_dark else '#666'}; margin-bottom: 16px;">
                土地型自住房客觀篩選 (UI-0 預覽)
            </div>
            
            <div style="margin-bottom: 20px;">
                <label style="font-weight:bold; font-size: 13px;">運行模式 (Mode)</label>
                <div style="margin-top: 6px; padding: 8px; background: {bg_card}; border: 1px solid {border_color}; border-radius: 6px; font-size: 13px;">
                    <b>{mode_title}</b>
                </div>
            </div>

            <div style="margin-bottom: 20px;">
                <label style="font-weight:bold; font-size: 13px;">主題外觀 (Theme)</label>
                <div style="margin-top: 6px; padding: 8px; background: {bg_card}; border: 1px solid {border_color}; border-radius: 6px; font-size: 13px;">
                    <b>{theme_title}</b>
                </div>
            </div>

            <hr style="border: 0; border-top: 1px solid {border_color}; margin: 20px 0;">

            <div style="font-weight:bold; font-size: 14px; margin-bottom: 12px;">圖層控制 (Layer Panel)</div>
            <div style="font-size: 13px; line-height: 1.8;">
                <div>☑ C1/D1 雙基地外緣 (官方幾何)</div>
                <div>☑ 500m / 700m 距離圈</div>
                <div>☑ 候選成交住宅標的點</div>
                <div>☑ 號碼區間外包範圍 (矩形)</div>
                <div style="color: {'#888' if is_dark else '#999'};">☐ 8米以上計畫道路 (待 2b 啟用)</div>
                <div style="color: {'#888' if is_dark else '#999'};">☐ 都市計畫使用分區 (待 2b 啟用)</div>
                <div style="color: {'#888' if is_dark else '#999'};">☐ 捷運/公車站位 (免金鑰，待 2a 啟用)</div>
                <div style="color: #E74C3C; font-weight: bold;">🔒 TDX 運輸 API (待啟用 - Phase T)</div>
            </div>

            <hr style="border: 0; border-top: 1px solid {border_color}; margin: 20px 0;">
            <div style="font-size: 11px; color: {'#888' if is_dark else '#888'};">
                依協議：UI-0 僅確認版面樣式，不實作評分/STRICT邏輯/交通外部串接。
            </div>
        </div>

        <!-- 主內容區 -->
        <div class="content">
            {banner_html}

            <!-- 頂部統計列 -->
            <div style="display: flex; margin-bottom: 24px;">
                <div class="metric-box">
                    <div class="metric-label">篩選後候選標的</div>
                    <div class="metric-val">{total_count} 筆</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">雙星核心圈 (≤500m)</div>
                    <div class="metric-val" style="color: #28A745;">{core_count} 筆</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">雙星次級圈 (500~700m)</div>
                    <div class="metric-val" style="color: #FD7E14;">{near_count} 筆</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">需人工核實 (區間/跨門檻)</div>
                    <div class="metric-val" style="color: #DC3545;">{manual_count} 筆</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">計算基準日 (as-of)</div>
                    <div class="metric-val" style="font-size: 18px;">2026-10-01</div>
                </div>
            </div>

            <!-- 地圖區域 -->
            <h3 style="margin-bottom: 8px;">生活圈空間總覽地圖 (Map View)</h3>
            <div style="font-size: 12px; color: {'#AAA' if is_dark else '#666'}; margin-bottom: 12px;">
                底圖：國土測繪圖資服務雲 (NLSC) 臺灣通用電子地圖 WMTS；點位圖徵依分級著色，A*/B* 採虛線空心圓，非精確門牌繪製外包矩形。
            </div>
            <div style="height: 500px; border-radius: 8px; overflow: hidden; border: 1px solid {border_color}; margin-bottom: 28px;">
                <iframe srcdoc="{map_html.replace('"', '&quot;')}" style="width: 100%; height: 100%; border: none;"></iframe>
            </div>

            <!-- 表格區域 -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h3 style="margin: 0;">候選標的清單 (Candidates Table)</h3>
                <div>
                    <button style="padding: 6px 14px; border-radius: 4px; border: 1px solid {border_color}; background: {bg_card}; color: {text_color}; cursor: {'not-allowed' if is_demo else 'pointer'};" {'disabled' if is_demo else ''}>
                        📥 匯出 CSV {'(示範模式停用)' if is_demo else ''}
                    </button>
                </div>
            </div>
            <div style="max-height: 380px; overflow-y: auto; margin-bottom: 28px; border-radius: 8px; border: 1px solid {border_color};">
                <table>
                    <thead>
                        <tr>
                            <th>候選編號</th>
                            <th>分級</th>
                            <th>評分</th>
                            <th>行政區</th>
                            <th>成交地址</th>
                            <th>房地淨價</th>
                            <th>土地坪數</th>
                            <th>土地信心</th>
                            <th>雙星距離</th>
                            <th>門牌精度</th>
                            <th>面臨路寬</th>
                            <th>人工核實</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html}
                    </tbody>
                </table>
            </div>

            <!-- 單筆深度診斷區域 -->
            <h3>候選標的深度診斷 (Candidate Inspection)</h3>
            <div style="display: flex; gap: 24px; background: {bg_card}; border: 1px solid {border_color}; border-radius: 8px; padding: 20px;">
                <div style="flex: 1;">
                    <h4 style="margin-top: 0;">標的總覽：<code>{first_c.candidate_id if first_c else '無'}</code></h4>
                    <p><b>門牌地址：</b> {first_c.address_display if first_c else ''}</p>
                    <p><b>建物型態：</b> {first_c.building_type if first_c else ''} | <b>屋齡：</b> {first_c.building_age_years if first_c else '未知'} 年</p>
                    <p><b>房地淨價：</b> <b style="color: {'#5DADE2' if is_dark else '#0056B3'};">{first_c.property_price_w if first_c else ''} 萬元</b> {'(車位內含)' if first_c and first_c.parking_included_flag else ''}</p>
                    <p><b>土地移轉：</b> <b>{first_c.land_area_ping if first_c else ''} 坪</b> (信心度: {first_c.land_share_confidence if first_c else ''})</p>
                    <p><b>雙星邊界距離：</b> <b>{first_c.distance_c1d1_m if first_c else ''} m</b> ({first_c.distance_threshold_status if first_c else ''})</p>
                    <p><b>地址精度：</b> {first_c.address_precision if first_c else ''}</p>
                    <hr style="border: 0; border-top: 1px solid {border_color}; margin: 16px 0;">
                    <h5 style="margin-bottom: 8px;">方案 B 條件符合度 (Why Matches)</h5>
                    <ul style="list-style: none; padding-left: 0; font-size: 13.5px;">
                        {why_matches_html}
                    </ul>
                </div>

                <div style="flex: 1.2;">
                    <h4 style="margin-top: 0;">客觀事實與衍生證據表 (Evidence Table)</h4>
                    <div style="font-size: 12px; color: {'#AAA' if is_dark else '#666'}; margin-bottom: 8px;">
                        嚴格帶狀態（OBSERVED/DERIVED/INFERRED/UNKNOWN）與來源出處：
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>欄位</th>
                                <th>數值</th>
                                <th>觀察狀態</th>
                                <th>資料來源</th>
                                <th>核實備註</th>
                            </tr>
                        </thead>
                        <tbody>
                            {evidence_rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated preview: {output_path}")


def main():
    real_cands = load_real_candidates()
    demo_cands = DEMO_CANDIDATES

    # 1. 真實模式 - 淺色
    generate_html_preview(real_cands, is_demo=False, is_dark=False, output_path="docs/previews/preview_real_light.html")
    # 2. 真實模式 - 深色
    generate_html_preview(real_cands, is_demo=False, is_dark=True, output_path="docs/previews/preview_real_dark.html")
    # 3. 示範模式 - 淺色
    generate_html_preview(demo_cands, is_demo=True, is_dark=False, output_path="docs/previews/preview_demo_light.html")
    # 4. 示範模式 - 深色
    generate_html_preview(demo_cands, is_demo=True, is_dark=True, output_path="docs/previews/preview_demo_dark.html")


if __name__ == "__main__":
    main()
