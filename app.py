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
    if "locked" not in st.session_state:
        st.session_state.locked = False
    if "latest_winners" not in st.session_state:
        # Changed to dictionary to support multiple prizes drawn at once
        st.session_state.latest_winners = {}
    if "winners_record" not in st.session_state:
        st.session_state.winners_record = {} 
    if "confirm_reset" not in st.session_state:
        st.session_state.confirm_reset = False
    if "enable_animation" not in st.session_state:
        st.session_state.enable_animation = True
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
                    if st.button("📥 載入 Excel 名單", use_container_width=True):
                        excel_list = df[target].dropna().astype(str).tolist()
                        st.session_state.participants.extend(excel_list)
                        st.session_state.participants = list(set(st.session_state.participants))
                        st.success("✅ 成功載入！請看左側欄確認名單。")
                else:
                    target = st.selectbox("請選擇名單所在的「列數 (Index)」", df.index)
                    if st.button("📥 載入 Excel 名單", use_container_width=True):
                        excel_list = df.iloc[target, :].dropna().astype(str).tolist()
                        st.session_state.participants.extend(excel_list)
                        st.session_state.participants = list(set(st.session_state.participants))
                        st.success("✅ 成功載入！請看左側欄確認名單。")
            except Exception as e:
                st.error("❌ 讀取 Excel 失敗，請確認檔案格式是否正確。")

    with tab2:
        manual_input = st.text_area("請手動輸入名單 (每行一個名字)：", height=150, placeholder="例如：\n王小明\n陳大麻\n李阿花")
        if st.button("➕ 加入手動名單", use_container_width=True):
            if manual_input.strip():
                manual_list = [name.strip() for name in manual_input.split('\n') if name.strip()]
                st.session_state.participants.extend(manual_list)
                st.session_state.participants = list(set(st.session_state.participants))
                st.success(f"✅ 成功加入 {len(manual_list)} 筆手動名單！請看左側欄確認。")
            else:
                st.warning("請先輸入內容喔！")
    st.divider()

# ==========================================
# 3. Prize Settings Module
# ==========================================
def render_prize_section():
    st.subheader("2. 獎項清單 (可編輯)")
    st.write("你可以直接在下方的表格新增、修改獎項名稱與要抽出的數量：")
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
# 4. Core Draw Module (Upgraded for Multi-select & Custom Qty)
# ==========================================
def render_draw_section():
    st.subheader("3. 進行抽獎")
    edited_prizes = st.session_state.prize_list
    available_prizes = []
    prize_status_map = {} # Store remaining count for logic use
    
    # Calculate available prizes
    for index, row in edited_prizes.iterrows():
        p_name = row["獎項名稱"]
        try:
            p_count = int(float(row["數量"]))
        except (ValueError, TypeError):
            p_count = 0 

        if pd.isna(p_name) or str(p_name).strip() == "" or p_count <= 0: 
            continue
        
        drawn_count = len(st.session_state.winners_record.get(p_name, []))
        remain_count = max(0, p_count - drawn_count)
        
        if remain_count > 0:
            display_text = f"{p_name} (剩餘 {remain_count} 名)"
            available_prizes.append(display_text)
            prize_status_map[display_text] = {"name": p_name, "remain": remain_count}

    if not available_prizes:
        st.info("🎈 所有獎項都已經抽完囉！可以看下方總得獎名單。")
    else:
        # UI: Multi-select with Select All checkbox
        container = st.container()
        all_options = st.checkbox("☑️ 全選所有可用獎項", disabled=st.session_state.locked)
        
        if all_options:
            selected_prize_strs = container.multiselect(
                "請選擇要抽的獎項 (可多選)：", 
                available_prizes, 
                available_prizes, 
                disabled=st.session_state.locked
            )
        else:
            selected_prize_strs = container.multiselect(
                "請選擇要抽的獎項 (可多選)：", 
                available_prizes, 
                disabled=st.session_state.locked
            )

        # UI: Draw Mode and Custom Quantity
        if selected_prize_strs:
            col_mode, col_qty = st.columns(2)
            with col_mode:
                draw_mode = st.radio(
                    "抽獎模式：", 
                    ["⚡ 抽出所選獎項的「全部剩餘名額」", "🔢 指定抽出數量"], 
                    horizontal=True, 
                    disabled=st.session_state.locked
                )
            
            custom_qty = 1
            if draw_mode == "🔢 指定抽出數量":
                with col_qty:
                    custom_qty = st.number_input(
                        "每個獎項抽出數量：", 
                        min_value=1, value=1, step=1, 
                        disabled=st.session_state.locked
                    )

            # Build Draw Plan
            draw_plan = {}
            total_needed = 0
            for p_str in selected_prize_strs:
                info = prize_status_map[p_str]
                p_name = info["name"]
                remain = info["remain"]
                
                if draw_mode == "⚡ 抽出所選獎項的「全部剩餘名額」":
                    qty_to_draw = remain
                else:
                    qty_to_draw = min(remain, custom_qty) # Cap at remaining
                    
                draw_plan[p_name] = qty_to_draw
                total_needed += qty_to_draw

            st.markdown(f"### 即將抽出 **{len(draw_plan)}** 種獎項，共計 `{total_needed}` 名得主")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🎯 抽出得獎者", type="primary", disabled=st.session_state.locked, use_container_width=True):
                    if len(st.session_state.participants) < total_needed:
                        st.error(f"剩餘人數 ({len(st.session_state.participants)}) 不足以抽出所需數量 ({total_needed})！請確認名單。")
                    elif total_needed <= 0:
                        st.warning("請選擇有效的抽獎數量！")
                    else:
                        # Execute draw for each selected prize
                        st.session_state.latest_winners = {}
                        for p_name, qty in draw_plan.items():
                            if qty > 0:
                                winners = random.sample(st.session_state.participants, qty)
                                st.session_state.latest_winners[p_name] = winners
                                st.session_state.winners_record[p_name].extend(winners)
                                for w in winners:
                                    st.session_state.participants.remove(w)
                        
                        st.session_state.locked = True
                        st.rerun()

            with col2:
                if st.button("🔓 解鎖並繼續抽獎", disabled=not st.session_state.locked, use_container_width=True):
                    st.session_state.locked = False
                    st.session_state.latest_winners = {}
                    st.rerun()

            # Result Display
            if st.session_state.locked:
                st.success("🎉 抽獎結果出爐！畫面已鎖定，請點擊右方按鈕繼續。")
                if st.session_state.enable_animation:
                    st.balloons()
                
                # Display winners grouped by prize
                for p_name, winners in st.session_state.latest_winners.items():
                    if winners:
                        st.markdown(f"#### 🏆 {p_name} 得主:")
                        st.markdown("> " + "、".join(winners))
        else:
            st.info("👆 請先在上方選單選擇至少一個獎項，才能進行抽獎。")

    st.divider()

# ==========================================
# 5. Winners List and Operations Module
# ==========================================
def render_winners_section():
    st.subheader("4. 🏆 目前得獎總名單")
    has_any_winner = False
    export_data = [] 

    for p_name, winners in st.session_state.winners_record.items():
        if winners:
            has_any_winner = True
            st.markdown(f"**{p_name}** (共 {len(winners)} 名): " + "、".join(winners))
            for w in winners:
                export_data.append({"獎項名稱": p_name, "得獎者": w})

    if not has_any_winner:
        st.write("目前還沒有人得獎喔！")
    else:
        st.write("")
        col_dl, col_reset = st.columns(2)
        
        with col_dl:
            df_export = pd.DataFrame(export_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='得獎名單')
            
            st.download_button(
                label="📥 下載得獎名單 (Excel)",
                data=output.getvalue(),
                file_name="得獎名單.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        with col_reset:
            if st.button("🔄 將所有得獎者退回獎池 (重新抽獎)", use_container_width=True):
                st.session_state.confirm_reset = True
                
        if st.session_state.confirm_reset:
            st.warning("⚠️ 確定要將所有人退回獎池並清空目前的得獎紀錄嗎？這項操作無法復原。")
            col_y, col_n = st.columns(2)
            if col_y.button("✔️ 確定執行", type="primary", use_container_width=True):
                all_past_winners = [w for winners in st.session_state.winners_record.values() for w in winners]
                st.session_state.participants.extend(all_past_winners)
                st.session_state.participants = list(set(st.session_state.participants))
                
                for p in st.session_state.winners_record:
                    st.session_state.winners_record[p] = []
                st.session_state.latest_winners = {}
                st.session_state.locked = False
                st.session_state.confirm_reset = False
                st.rerun()
                
            if col_n.button("❌ 取消", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()

# ==========================================
# 6. Sidebar Module (Added Animation Toggle)
# ==========================================
def render_sidebar():
    with st.sidebar:
        st.header("📝 目前抽獎名單")
        st.write(f"總共剩餘：**{len(st.session_state.participants)}** 人")
        
        if st.session_state.participants:
            df_participants = pd.DataFrame({"參賽者": st.session_state.participants})
            st.dataframe(df_participants, hide_index=True, use_container_width=True)
        else:
            st.info("目前名單是空的喔！")
            
        st.divider()
        
        # Animation Toggle Switch
        st.session_state.enable_animation = st.toggle("🎈 開啟抽獎慶祝動畫", value=st.session_state.enable_animation)
        
        st.divider()
        if st.button("🗑️ 清空所有名單與紀錄 (徹底重置)", use_container_width=True):
            st.session_state.participants = []
            st.session_state.winners_record = {} 
            st.session_state.latest_winners = {}
            st.session_state.locked = False
            st.session_state.confirm_reset = False 
            st.rerun()

# ==========================================
# 🚀 Main Application Entry Point
# ==========================================
def main():
    st.set_page_config(page_title="抽獎系統", page_icon="🎉", layout="wide")
    init_session_state()
    
    st.title("🎉 抽獎系統")
    
    render_import_section()
    render_prize_section()
    render_draw_section()
    render_winners_section()
    render_sidebar()

if __name__ == "__main__":
    main()