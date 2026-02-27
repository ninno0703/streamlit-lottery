import streamlit as st
import pandas as pd
import random
import io

# ==========================================
# 1. State Initialization Module
# ==========================================
def init_session_state():
    if "participants" not in st.session_state:
        st.session_state.participants = []
    if "latest_winners" not in st.session_state:
        st.session_state.latest_winners = {}
    if "winners_record" not in st.session_state:
        st.session_state.winners_record = {} 
    if "confirm_reset" not in st.session_state:
        st.session_state.confirm_reset = False
    if "enable_animation" not in st.session_state:
        st.session_state.enable_animation = True
    # 新增一個狀態，用來控制是否要顯示「全螢幕發表畫面」
    if "show_result_screen" not in st.session_state:
        st.session_state.show_result_screen = False
    if "prize_list" not in st.session_state:
        st.session_state.prize_list = pd.DataFrame([
            {"獎項名稱": "特獎", "數量": 1},
            {"獎項名稱": "頭獎", "數量": 2},
            {"獎項名稱": "普獎", "數量": 5}
        ])

# ==========================================
# 2. Import Participants Module
# ==========================================
def render_import_section():
    st.subheader("1. 匯入抽獎名單")
    tab1, tab2 = st.tabs(["📁 Excel 匯入", "✍️ 手動輸入"])

    with tab1:
        uploaded_file = st.file_uploader("請上傳 Excel 檔案", type=["xlsx"])
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                st.write("📄 **資料預覽 (前 3 筆)：**")
                st.dataframe(df.head(3), use_container_width=True)
                read_mode = st.radio("請問名單是直的還是橫的？", ["按欄讀取 (直向 ↓)", "按列讀取 (橫向 →)"], horizontal=True)
                
                if read_mode == "按欄讀取 (直向 ↓)":
                    target = st.selectbox("請選擇名單所在的「欄位名稱」", df.columns)
                    if st.button("📥 載入 Excel 名單", key="load_excel_col", use_container_width=True):
                        excel_list = df[target].dropna().astype(str).tolist()
                        st.session_state.participants.extend(excel_list)
                        st.session_state.participants = list(set(st.session_state.participants))
                        st.success("✅ 成功載入！")
                else:
                    target = st.selectbox("請選擇名單所在的「列數 (Index)」", df.index)
                    if st.button("📥 載入 Excel 名單", key="load_excel_row", use_container_width=True):
                        excel_list = df.iloc[target, :].dropna().astype(str).tolist()
                        st.session_state.participants.extend(excel_list)
                        st.session_state.participants = list(set(st.session_state.participants))
                        st.success("✅ 成功載入！")
            except Exception as e:
                st.error("❌ 讀取 Excel 失敗，請確認檔案格式。")

    with tab2:
        manual_input = st.text_area("請手動輸入名單 (每行一個名字)：", height=150)
        if st.button("➕ 加入手動名單", use_container_width=True):
            if manual_input.strip():
                manual_list = [name.strip() for name in manual_input.split('\n') if name.strip()]
                st.session_state.participants.extend(manual_list)
                st.session_state.participants = list(set(st.session_state.participants))
                st.success(f"✅ 成功加入 {len(manual_list)} 筆名單！")
    st.divider()

# ==========================================
# 3. Prize Settings Module
# ==========================================
def render_prize_section():
    st.subheader("2. 獎項清單 (可編輯)")
    edited_prizes = st.data_editor(
        st.session_state.prize_list,
        num_rows="dynamic",
        use_container_width=True
    )
    st.session_state.prize_list = edited_prizes

    current_prize_names = edited_prizes["獎項名稱"].dropna().tolist()
    for p in current_prize_names:
        if str(p).strip() != "" and p not in st.session_state.winners_record:
            st.session_state.winners_record[p] = []
    st.divider()

# ==========================================
# 4. Core Draw Module
# ==========================================
def render_draw_section():
    st.subheader("3. 進行抽獎")
    edited_prizes = st.session_state.prize_list
    available_prizes = []
    prize_status_map = {}
    
    for index, row in edited_prizes.iterrows():
        p_name = row["獎項名稱"]
        try: p_count = int(float(row["數量"]))
        except: p_count = 0 

        if pd.isna(p_name) or str(p_name).strip() == "" or p_count <= 0: continue
        
        drawn_count = len(st.session_state.winners_record.get(p_name, []))
        remain_count = max(0, p_count - drawn_count)
        
        if remain_count > 0:
            display_text = f"{p_name} (剩餘 {remain_count} 名)"
            available_prizes.append(display_text)
            prize_status_map[display_text] = {"name": p_name, "remain": remain_count}

    if not available_prizes:
        st.info("🎈 所有獎項都已經抽完囉！")
    else:
        all_options = st.checkbox("☑️ 全選所有可用獎項")
        selected_prize_strs = st.multiselect(
            "請選擇要抽的獎項：", 
            available_prizes, 
            default=available_prizes if all_options else None
        )

        if selected_prize_strs:
            col_mode, col_qty = st.columns(2)
            with col_mode:
                draw_mode = st.radio("抽獎模式：", ["⚡ 抽出全部剩餘名額", "🔢 指定抽出數量"], horizontal=True)
            
            custom_qty = 1
            if draw_mode == "🔢 指定抽出數量":
                with col_qty:
                    custom_qty = st.number_input("每個獎項抽出數量：", min_value=1, value=1)

            if st.button("🎯 抽出得獎者", type="primary", use_container_width=True):
                draw_plan = {}
                total_needed = 0
                for p_str in selected_prize_strs:
                    info = prize_status_map[p_str]
                    qty = info["remain"] if draw_mode == "⚡ 抽出全部剩餘名額" else min(info["remain"], custom_qty)
                    draw_plan[info["name"]] = qty
                    total_needed += qty

                if len(st.session_state.participants) < total_needed:
                    st.error(f"池內人數不足！需要 {total_needed} 人，目前僅剩 {len(st.session_state.participants)} 人。")
                elif total_needed > 0:
                    # 執行抽獎邏輯
                    st.session_state.latest_winners = {}
                    for p_name, qty in draw_plan.items():
                        if qty > 0:
                            winners = random.sample(st.session_state.participants, qty)
                            st.session_state.latest_winners[p_name] = winners
                            st.session_state.winners_record[p_name].extend(winners)
                            for w in winners:
                                st.session_state.participants.remove(w)
                    
                    # 觸發全螢幕顯示狀態
                    st.session_state.show_result_screen = True
                    st.rerun()

        else:
            st.info("👆 請先選擇獎項。")
    st.divider()

# ==========================================
# 5. Winners Record Module
# ==========================================
def render_winners_section():
    st.subheader("4. 🏆 目前得獎總名單")
    has_any_winner = False
    export_data = [] 

    for p_name, winners in st.session_state.winners_record.items():
        if winners:
            has_any_winner = True
            st.markdown(f"**{p_name}** ({len(winners)} 名): " + "、".join(winners))
            for w in winners:
                export_data.append({"獎項名稱": p_name, "得獎者": w})

    if has_any_winner:
        col_dl, col_reset = st.columns(2)
        with col_dl:
            df_export = pd.DataFrame(export_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False)
            st.download_button("📥 下載得獎名單 (Excel)", data=output.getvalue(), file_name="得獎名單.xlsx", use_container_width=True)
            
        with col_reset:
            if st.button("🔄 退回獎池 (重新抽獎)", use_container_width=True):
                st.session_state.confirm_reset = True
                
        if st.session_state.confirm_reset:
            st.warning("⚠️ 確定清空紀錄並將得獎者退回獎池？")
            c1, c2 = st.columns(2)
            if c1.button("✔️ 確定", type="primary", use_container_width=True):
                all_winners = [w for ws in st.session_state.winners_record.values() for w in ws]
                st.session_state.participants.extend(all_winners)
                st.session_state.participants = list(set(st.session_state.participants))
                for p in st.session_state.winners_record: st.session_state.winners_record[p] = []
                st.session_state.latest_winners = {}
                st.session_state.confirm_reset = False
                st.rerun()
            if c2.button("❌ 取消", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()

# ==========================================
# 6. Sidebar Module
# ==========================================
def render_sidebar():
    with st.sidebar:
        st.header("📝 獎池名單")
        st.write(f"剩餘：**{len(st.session_state.participants)}** 人")
        if st.session_state.participants:
            st.dataframe(pd.DataFrame({"名單": st.session_state.participants}), hide_index=True)
        
        st.divider()
        st.session_state.enable_animation = st.toggle("🎈 抽獎動畫", value=st.session_state.enable_animation)
        
        if st.button("🗑️ 徹底重置系統", use_container_width=True):
            st.session_state.participants = []
            st.session_state.winners_record = {} 
            st.session_state.latest_winners = {}
            st.session_state.confirm_reset = False 
            st.rerun()

# ==========================================
# 7. Full-Screen Result Module (全新！全螢幕發表模組)
# ==========================================
def render_full_screen_result():
    # 這裡直接觸發動畫，因為沒有緊接著 rerun，所以動畫一定會噴發
    if st.session_state.enable_animation:
        st.balloons()
        
    st.markdown("<h1 style='text-align: center; font-size: 3.5rem; margin-top: 2rem;'>🎉 恭喜得獎 🎉</h1>", unsafe_allow_html=True)
    st.write("---")
    
    # 置中顯示每一項獎品與得獎者
    for p_name, winners in st.session_state.latest_winners.items():
        if winners:
            st.markdown(f"<h2 style='text-align: center; color: #FF4B4B;'>🏆 {p_name}</h2>", unsafe_allow_html=True)
            winners_str = " 、 ".join(winners)
            st.markdown(f"<h3 style='text-align: center; font-weight: normal;'>{winners_str}</h3>", unsafe_allow_html=True)
            st.write("<br>", unsafe_allow_html=True) # 增加一些留白

    st.write("---")
    
    # 製作一個大按鈕用來返回
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔙 返回抽獎系統並繼續", type="primary", use_container_width=True):
            st.session_state.show_result_screen = False
            st.rerun()

# ==========================================
# 🚀 Main Application Entry Point
# ==========================================
def main():
    st.set_page_config(page_title="抽獎系統", page_icon="🎉", layout="wide")
    init_session_state()
    
    # 根據狀態決定要渲染「主畫面」還是「全螢幕結果畫面」
    if st.session_state.show_result_screen:
        render_full_screen_result()
    else:
        st.title("🎉 抽獎系統")
        render_import_section()
        render_prize_section()
        render_draw_section()
        render_winners_section()
        render_sidebar()

if __name__ == "__main__":
    main()