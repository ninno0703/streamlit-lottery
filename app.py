import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="抽獎系統", page_icon="🎉", layout="wide")

# 初始化 Session State
if "participants" not in st.session_state:
    st.session_state.participants = []
if "locked" not in st.session_state:
    st.session_state.locked = False
if "current_winners" not in st.session_state:
    st.session_state.current_winners = []
if "prize_list" not in st.session_state:
    st.session_state.prize_list = pd.DataFrame([
        {"獎項名稱": "特獎", "數量": 1, "狀態": "待抽"},
        {"獎項名稱": "頭獎", "數量": 2, "狀態": "待抽"},
        {"獎項名稱": "普獎", "數量": 5, "狀態": "待抽"}
    ])

# ==========================================
# 側邊欄 (Sidebar) - 名單監控區
# ==========================================
with st.sidebar:
    st.header("📝 目前抽獎名單")
    st.write(f"總共：**{len(st.session_state.participants)}** 人")
    
    # 顯示目前名單的表格
    if st.session_state.participants:
        df_participants = pd.DataFrame({"參賽者": st.session_state.participants})
        st.dataframe(df_participants, hide_index=True, use_container_width=True)
    else:
        st.info("目前名單是空的喔！")
        
    st.divider()
    if st.button("🗑️ 清空所有名單", use_container_width=True):
        st.session_state.participants = []
        st.rerun()

# ==========================================
# 主畫面
# ==========================================
st.title("🎉 抽獎系統")

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
            st.success(f"✅ 成功加入 {len(manual_list)} 筆手動名單！")
        else:
            st.warning("請先輸入內容喔！")

st.divider()

st.subheader("2. 獎項清單 (可編輯)")
st.write("你可以直接在下方的表格新增、修改獎項名稱與要抽出的數量：")
edited_prizes = st.data_editor(
    st.session_state.prize_list,
    num_rows="dynamic",
    use_container_width=True,
    disabled=["狀態"]
)
st.session_state.prize_list = edited_prizes
st.divider()

st.subheader("3. 進行抽獎")

pending_prizes = edited_prizes[edited_prizes["狀態"] == "待抽"]

if pending_prizes.empty:
    st.info("🎈 所有獎項都已經抽完囉！")
else:
    current_prize = pending_prizes.iloc[0]
    prize_name = current_prize["獎項名稱"]
    prize_count = current_prize["數量"]
    prize_idx = pending_prizes.index[0]

    st.markdown(f"### 目前正在抽取的獎項：**{prize_name}** (共 {prize_count} 名)")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🎯 抽出得獎者", disabled=st.session_state.locked, use_container_width=True):
            if len(st.session_state.participants) < prize_count:
                st.error("剩餘人數不足以抽出此獎項！請確認名單。")
            else:
                winners = random.sample(st.session_state.participants, prize_count)
                st.session_state.current_winners = winners

                for w in winners:
                    st.session_state.participants.remove(w)

                st.session_state.prize_list.at[prize_idx, "狀態"] = "已抽出"
                st.session_state.locked = True
                st.rerun()

    with col2:
        if st.button("🔓 解鎖並進行下一組", disabled=not st.session_state.locked, use_container_width=True):
            st.session_state.locked = False
            st.session_state.current_winners = []
            st.rerun()

    if st.session_state.locked:
        st.success("🎉 抽獎結果出爐！畫面已鎖定，請點擊右方按鈕進行下一組。")
        st.balloons()
        for i, winner in enumerate(st.session_state.current_winners):
            st.markdown(f"#### 🏆 得獎者 {i+1}: **{winner}**")