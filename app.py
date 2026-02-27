import streamlit as st
import pandas as pd
import random
import io

# ==========================================
# 1. 狀態初始化模組
# ==========================================
def init_session_state():
    if "participants" not in st.session_state:
        st.session_state.participants = []
    if "locked" not in st.session_state:
        st.session_state.locked = False
    if "latest_winners" not in st.session_state:
        st.session_state.latest_winners = []
    if "winners_record" not in st.session_state:
        st.session_state.winners_record = {} 
    if "prize_list" not in st.session_state:
        st.session_state.prize_list = pd.DataFrame([
            {"獎項名稱": "特獎", "數量": 1},
            {"獎項名稱": "頭獎", "數量": 2},
            {"獎項名稱": "普獎", "數量": 5}
        ])

# ==========================================
# 2. 匯入名單區塊模組
# ==========================================
def render_import_section():
    st.subheader("1. 匯入抽獎名單")
    tab1, tab2 = st.tabs(["📁 Excel 匯入", "✍️ 手動輸入"])

    with tab1:
        uploaded_file = st.file_uploader("請上傳 Excel 檔案", type=["xlsx"])
        if uploaded_file:
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
# 3. 獎項設定區塊模組
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
        if p not in st.session_state.winners_record:
            st.session_state.winners_record[p] = []
    st.divider()

# ==========================================
# 4. 抽獎核心區塊模組
# ==========================================
def render_draw_section():
    st.subheader("3. 進行抽獎")
    edited_prizes = st.session_state.prize_list
    available_prizes = []
    
    for index, row in edited_prizes.iterrows():
        p_name = row["獎項名稱"]
        p_count = row["數量"]
        if pd.isna(p_name) or p_name == "": continue
        
        drawn_count = len(st.session_state.winners_record.get(p_name, []))
        if drawn_count < p_count:
            available_prizes.append(f"{p_name} (剩餘 {p_count - drawn_count} 名)")

    if not available_prizes:
        st.info("🎈 所有獎項都已經抽完囉！可以看下方總得獎名單。")
    else:
        col_prize, col_mode = st.columns(2)
        with col_prize:
            selected_prize_str = st.selectbox("請選擇要抽的獎項 (決定順序)：", available_prizes, disabled=st.session_state.locked)
        with col_mode:
            draw_mode = st.radio("請選擇抽獎模式：", ["一次抽出剩餘名額", "單抽 (一次抽出 1 名)"], horizontal=True, disabled=st.session_state.locked)

        selected_prize_name = selected_prize_str.split(" (剩餘")[0]
        target_count = int(edited_prizes[edited_prizes["獎項名稱"] == selected_prize_name]["數量"].iloc[0])
        current_drawn = len(st.session_state.winners_record[selected_prize_name])
        remain_count = target_count - current_drawn

        num_to_draw = remain_count if draw_mode == "一次抽出剩餘名額" else 1

        st.markdown(f"### 即將抽出：**{selected_prize_name}** x `{num_to_draw}` 名")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🎯 抽出得獎者", disabled=st.session_state.locked, use_container_width=True):
                if len(st.session_state.participants) < num_to_draw:
                    st.error("剩餘人數不足以抽出此數量！請確認名單。")
                else:
                    winners = random.sample(st.session_state.participants, num_to_draw)
                    st.session_state.latest_winners = winners
                    st.session_state.winners_record[selected_prize_name].extend(winners)
                    for w in winners:
                        st.session_state.participants.remove(w)
                    st.session_state.locked = True
                    st.rerun()

        with col2:
            if st.button("🔓 解鎖並繼續抽獎", disabled=not st.session_state.locked, use_container_width=True):
                st.session_state.locked = False
                st.session_state.latest_winners = []
                st.rerun()

        if st.session_state.locked:
            st.success("🎉 抽獎結果出爐！畫面已鎖定，請點擊右方按鈕繼續。")
            st.balloons()
            for i, winner in enumerate(st.session_state.latest_winners):
                st.markdown(f"#### 🏆 {selected_prize_name} 得主: **{winner}**")
    st.divider()

# ==========================================
# 5. 總得獎名單與操作模組
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
        
        # 製作 Excel 下載按鈕
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
            
        # 製作退回獎池按鈕
        with col_reset:
            if st.button("🔄 將所有得獎者退回獎池 (重新抽獎)", use_container_width=True):
                # 把所有人加回池子裡並去重
                all_past_winners = [w for winners in st.session_state.winners_record.values() for w in winners]
                st.session_state.participants.extend(all_past_winners)
                st.session_state.participants = list(set(st.session_state.participants))
                
                # 清空紀錄與解鎖
                for p in st.session_state.winners_record:
                    st.session_state.winners_record[p] = []
                st.session_state.latest_winners = []
                st.session_state.locked = False
                st.rerun()

# ==========================================
# 6. 側邊欄模組
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
        if st.button("🗑️ 清空所有名單與紀錄 (徹底重置)", use_container_width=True):
            st.session_state.participants = []
            st.session_state.winners_record = {} 
            st.session_state.latest_winners = []
            st.session_state.locked = False
            st.rerun()

# ==========================================
# 🚀 應用程式主進入點
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