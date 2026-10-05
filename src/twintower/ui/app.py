"""
台北雙星土地型自住房研究引擎 - Streamlit 互動預覽介面 (UI-0)
規範：
1. 嚴格遵守 docs/UI_SPEC.md 定義之契約與版面。
2. 雙模式支援：真實資料模式 (DuckDB 唯讀) 與 合成示範模式 (記憶體假資料，禁止寫入與匯出)。
3. 未實作欄位在真實模式下一律顯示「待實作」，嚴禁捏造任何假數值。
4. TDX 圖層明確標記「待啟用（NOT_ENABLED）」。
"""

from datetime import date
import json
import os
import duckdb
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from twintower.constants import AddressPrecision, CandidateGrade, ConditionStatus
from twintower.ui.fixtures import DEMO_CANDIDATES
from twintower.ui.map_views import build_overview_map
from twintower.ui.view_model import CandidateViewModel

# 設定 Streamlit 頁面屬性
st.set_page_config(
    page_title="台北雙星土地型自住房研究引擎 (UI-0 預覽)",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_real_data(db_path: str = "data/processed/twintower.duckdb") -> list[CandidateViewModel]:
    """從 DuckDB 讀取真實 Phase 1a 資料"""
    if not os.path.exists(db_path):
        return []
    try:
        con = duckdb.connect(db_path, read_only=True)
        # 關聯 candidate_properties, locations, transactions
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

        view_models = []
        for _, row in df.iterrows():
            vm = CandidateViewModel.from_real_duckdb_row(row.to_dict())
            view_models.append(vm)
        return view_models
    except Exception as e:
        st.error(f"讀取 DuckDB 失敗: {e}")
        return []


def inject_custom_css(is_dark: bool):
    """注入淺色/深色主題自訂 CSS"""
    if is_dark:
        bg_main = "#121212"
        bg_card = "#1E1E1E"
        text_color = "#E0E0E0"
        border_color = "#333333"
    else:
        bg_main = "#FFFFFF"
        bg_card = "#F8F9FA"
        text_color = "#212529"
        border_color = "#E9ECEF"

    st.markdown(
        f"""
        <style>
        .main {{
            background-color: {bg_main};
            color: {text_color};
        }}
        .metric-card {{
            background-color: {bg_card};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 12px 16px;
            text-align: center;
        }}
        .banner-real {{
            background-color: #FFF3CD;
            color: #856404;
            border: 1px solid #FFEEBA;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 14px;
            margin-bottom: 12px;
        }}
        .banner-demo {{
            background-color: #F8D7DA;
            color: #721C24;
            border: 1px solid #F5C6CB;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 12px;
        }}
        .watermark-demo {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(220, 53, 69, 0.85);
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 12px;
            z-index: 9999;
            pointer-events: none;
        }}
        .badge-pass {{
            background-color: #D4EDDA; color: #155724; padding: 2px 8px; border-radius: 4px; font-weight: bold;
        }}
        .badge-near {{
            background-color: #FFEBAA; color: #856404; padding: 2px 8px; border-radius: 4px; font-weight: bold;
        }}
        .badge-fail {{
            background-color: #F8D7DA; color: #721C24; padding: 2px 8px; border-radius: 4px; font-weight: bold;
        }}
        .badge-unknown {{
            background-color: #E2E3E5; color: #383D41; padding: 2px 8px; border-radius: 4px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    # 1. 側邊面板設定
    with st.sidebar:
        st.title("雙星研究引擎")
        st.caption("Taipei Twin Towers Land-Oriented Residential Research Engine (UI-0)")

        # (A) 模式切換
        app_mode = st.radio(
            "運行模式 (Mode)",
            options=["真實資料模式 (Phase 1a)", "合成示範模式 (Demo Fixtures)"],
            index=0,
            help="真實模式讀取本機 DuckDB；示範模式展示完整分級與異常情境",
        )
        is_demo = "示範" in app_mode

        # (B) 主題切換
        theme_choice = st.radio("介面主題 (Theme)", options=["淺色主題 (Light)", "深色主題 (Dark)"], index=0)
        is_dark = "Dark" in theme_choice

        inject_custom_css(is_dark)

        st.divider()

        # (C) 候選篩選面板
        st.subheader("篩選條件 (Filters)")
        districts_selected = st.multiselect(
            "行政區",
            options=["中正區", "大同區", "萬華區", "中山區"],
            default=["中正區", "大同區", "萬華區", "中山區"],
        )

        price_range = st.slider("房地淨價範圍 (萬元)", min_value=0, max_value=4000, value=(0, 2500), step=50)
        land_min = st.slider("土地面積下限 (坪)", min_value=0.0, max_value=30.0, value=0.0, step=0.5)
        dist_max_slider = st.slider("雙星距離上限 (公尺)", min_value=100, max_value=1500, value=1200, step=50)

        st.divider()

        # (D) 圖層面板 (Layer Panel)
        st.subheader("圖層控制 (Layer Panel)")
        st.checkbox("C1/D1 基地多邊形", value=True, help="臺北車站特定專用區 C1/D1 官方邊界")
        st.checkbox("500m / 700m 距離圈", value=True, help="方案 B 核心半徑 500m 與次級半徑 700m 緩衝圈")
        st.checkbox("候選成交標的點", value=True, help="成交住宅點位")
        st.checkbox("號碼區間外包範圍", value=True, help="非精確門牌之外包矩形")

        st.caption("計畫與環境圖層 (Phase 2)")
        st.checkbox("8米以上計畫道路 (待 2b 啟用)", value=False, disabled=True)
        st.checkbox("都市計畫使用分區 (待 2b 啟用)", value=False, disabled=True)
        st.checkbox("捷運出入口 (免金鑰，待 2a 啟用)", value=False, disabled=True)
        st.checkbox("公車站位點 (免金鑰，待 2a 啟用)", value=False, disabled=True)

        st.caption("TDX 整合運輸圖層 (Phase T)")
        st.checkbox("🔒 TDX 運輸 API (待啟用 - 延後至 Phase T)", value=False, disabled=True,
                    help="依指令所有 TDX 取用延後至 Phase T 評估額度後啟用")

    # 2. 資料載入
    if is_demo:
        all_candidates = DEMO_CANDIDATES
        as_of_date = "2026-10-01 (示範)"
    else:
        all_candidates = load_real_data()
        as_of_date = "2026-10-01"

    # 3. 條件篩選過濾
    filtered_candidates = [
        c for c in all_candidates
        if (c.district in districts_selected if districts_selected else True)
        and (price_range[0] <= c.property_price_w <= price_range[1])
        and (c.land_area_ping >= land_min)
        and (c.distance_c1d1_m is None or c.distance_c1d1_m <= dist_max_slider)
    ]

    # 4. 常駐橫幅宣告
    if is_demo:
        st.markdown(
            """
            <div class="banner-demo">
                🧪 <b>【合成示範資料，非真實成交】</b>
                此模式所有物件均為合成假資料（依規格第 13 節之 A/A*/B/B*/C/D/X 等情境建構），僅供驗證版面配置、視覺著色與互動流程。示範資料不存入資料庫，匯出功能已停用。
            </div>
            <div class="watermark-demo">合成示範資料，非真實成交</div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="banner-real">
                ⚠️ <b>預覽版宣告：</b>
                資料為單一期歷史實價登錄；C1/D1 幾何來源為臺北市都市計畫主要計畫特定專用區圖層（待公報進一步校準）；距離為多邊形外緣邊界測算；<b>分級與評分尚未實作（依規範顯示「待實作」）</b>。
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 5. 頂部摘要指標列 (Metrics Row)
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    with m_col1:
        st.metric("篩選後候選筆數", f"{len(filtered_candidates)} 筆", delta=f"總數 {len(all_candidates)}")
    with m_col2:
        core_cnt = sum(1 for c in filtered_candidates if c.distance_c1d1_m is not None and c.distance_c1d1_m <= 500)
        st.metric("雙星核心範圍 (≤500m)", f"{core_cnt} 筆")
    with m_col3:
        near_cnt = sum(1 for c in filtered_candidates if c.distance_c1d1_m is not None and 500 < c.distance_c1d1_m <= 700)
        st.metric("雙星次級範圍 (500~700m)", f"{near_cnt} 筆")
    with m_col4:
        manual_cnt = sum(1 for c in filtered_candidates if c.requires_manual_check)
        st.metric("需人工查核 (未精確驗證)", f"{manual_cnt} 筆")
    with m_col5:
        st.metric("計算基準日", as_of_date)

    st.write("")

    # 6. 主畫面上半部：總覽地圖
    st.subheader("生活圈空間總覽地圖 (Map View)")
    st.caption("底圖：國土測繪圖資服務雲 (NLSC) 臺灣通用電子地圖 WMTS；點位顏色：依分級著色 (A*/B* 為虛線空心圓，非精確門牌繪製外包矩形)")

    # 選擇目前要聚焦查看的候選 ID
    cand_options = ["(無選取，檢視全區)"] + [f"[{c.candidate_grade}] {c.candidate_id} - {c.address_display}" for c in filtered_candidates]
    selected_option = st.selectbox("在地圖與詳情中選取標的 (Select Candidate)", options=cand_options, index=0)
    selected_id = selected_option.split(" - ")[0].split("] ")[-1] if selected_option != "(無選取，檢視全區)" else None

    # 建構並渲染 Folium 地圖
    f_map = build_overview_map(
        candidates=filtered_candidates,
        is_demo_mode=is_demo,
        is_dark_theme=is_dark,
        selected_candidate_id=selected_id,
    )
    # 以 Streamlit HTML 元件呈現
    components.html(f_map.get_root().render(), height=500, scrolling=False)

    st.divider()

    # 7. 主畫面下半部：候選清單資料表 (Table View)
    st.subheader("候選標的清單 (Candidates Table)")

    table_data = []
    for c in filtered_candidates:
        table_data.append({
            "候選編號": c.candidate_id,
            "分級": c.candidate_grade,
            "綜合評分": c.total_score,
            "行政區": c.district,
            "成交地址": c.address_display,
            "房地淨價(萬)": c.property_price_w,
            "土地坪數": c.land_area_ping,
            "土地信心": c.land_share_confidence,
            "雙星距離(m)": f"{c.distance_c1d1_m:.1f}" if c.distance_c1d1_m else "未知",
            "距離狀態": c.distance_threshold_status,
            "門牌精度": c.address_precision,
            "臨路路寬": c.road_width_m,
            "需人工核實": "⚠️ 是" if c.requires_manual_check else "否",
        })

    df_table = pd.DataFrame(table_data)
    st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True,
        height=320,
    )

    # 匯出按鈕 (示範模式強制禁用)
    exp_col1, exp_col2 = st.columns([1, 4])
    with exp_col1:
        if is_demo:
            st.button("📥 匯出候選 CSV (示範模式停用)", disabled=True)
        else:
            csv_bytes = df_table.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label="📥 匯出候選清單 CSV",
                data=csv_bytes,
                file_name="twintower_candidates_filtered.csv",
                mime="text/csv",
            )

    st.divider()

    # 8. 候選物件深度診斷與證據表 (Candidate Details & Evidence)
    st.subheader("候選標的深度診斷 (Candidate Inspection)")

    # 找出當前選取物件
    selected_vm = None
    if selected_id:
        for c in filtered_candidates:
            if c.candidate_id == selected_id:
                selected_vm = c
                break

    if selected_vm is None and len(filtered_candidates) > 0:
        selected_vm = filtered_candidates[0]

    if selected_vm:
        det_col1, det_col2 = st.columns([1, 1])

        with det_col1:
            st.markdown(f"#### 標的總覽：`{selected_vm.candidate_id}`")
            st.write(f"**門牌地址：** {selected_vm.address_display}")
            st.write(f"**建物型態：** {selected_vm.building_type} | **屋齡：** {f'{selected_vm.building_age_years:.1f} 年' if selected_vm.building_age_years else '未知'}")
            st.write(f"**登記總價：** {selected_vm.total_price_w} 萬元 | **車位價格：** {selected_vm.parking_price_w} 萬元")
            st.write(f"**房地淨價：** **{selected_vm.property_price_w} 萬元** {'(車位價格內含未拆分)' if selected_vm.parking_included_flag else ''}")
            st.write(f"**土地移轉坪數：** **{selected_vm.land_area_ping} 坪** (持份信心度: `{selected_vm.land_share_confidence}`) | **建物：** {selected_vm.building_area_ping} 坪")
            st.write(f"**雙星邊界距離：** **{f'{selected_vm.distance_c1d1_m:.1f} m' if selected_vm.distance_c1d1_m else '未知'}** (門檻狀態: `{selected_vm.distance_threshold_status}`)")
            st.write(f"**地址精度：** `{selected_vm.address_precision}` {'(已由人工查證覆蓋)' if selected_vm.is_location_overridden else ''}")

            st.write("---")
            st.markdown("##### 方案 B 核心條件符合度檢視 (Why Matches)")
            for cond_name, cond_stat in selected_vm.condition_checks.items():
                if cond_stat == ConditionStatus.PASS:
                    st.markdown(f"- ✅ **{cond_name}**: 符合核心條件 (`PASS`)")
                elif cond_stat == ConditionStatus.NEAR:
                    st.markdown(f"- ⚠️ **{cond_name}**: 符合寬鬆/接近條件 (`NEAR`)")
                elif cond_stat == ConditionStatus.FAIL:
                    st.markdown(f"- ❌ **{cond_name}**: 不符合 (`FAIL`)")
                else:
                    st.markdown(f"- ❓ **{cond_name}**: **{cond_stat}**")

        with det_col2:
            st.markdown("#### 客觀事實與衍生證據表 (Evidence Table)")
            st.caption("每個欄位均帶有原始觀察狀態（OBSERVED/DERIVED/INFERRED/UNKNOWN）與查證出處：")
            ev_df = pd.DataFrame(selected_vm.evidence_rows)
            st.dataframe(ev_df, use_container_width=True, hide_index=True)

            st.info(
                f"**空間備註：** {selected_vm.address_display}\n\n"
                f"- 坐標：WGS84 ({selected_vm.lat_wgs84 or '未知'}, {selected_vm.lon_wgs84 or '未知'})\n"
                f"- 面臨路寬：{selected_vm.road_width_m} | 使用分區：{selected_vm.zoning_code}\n"
                f"- 重大建設與交通：{selected_vm.urban_renewal_status}；{selected_vm.station_distances}"
            )


if __name__ == "__main__":
    main()
