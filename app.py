import streamlit as st
import pandas as pd
import random

# 設定網頁標題
st.set_page_config(page_title="抽獎系統", page_icon="🎉")

# 初始化 Session State (用來記住跨按鈕點擊時的狀態與變數)
if "participants" not in st.session_state:
    st.session_state.participants = []
if "locked" not in st.session_state:
    st.session_state.locked = False
if "current_winners" not in st.session_state:
    st.session_state.current_winners = []
if "prize_list" not in st.session_state:
    # 預設的獎項清單 (List 格式，可設定複數數量)
    st.session_state.prize_list = pd.DataFrame([
        {"獎項名稱": "特獎", "數量": 1, "狀態": "待抽"},
        {"獎項名稱": "頭獎", "數量": 2, "狀態": "待抽"},
        {"獎項名稱": "普獎", "數量": 5, "狀態": "待抽"}
    ])

st.title("🎉 抽獎系統")

# --- 區塊 1: 匯入 Excel 名單 ---
st.subheader("1. 匯入抽獎名單")
uploaded_file = st.file_uploader("請上傳 Excel 檔案 (程式會自動抓取第一欄作為名單)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    if st.button("載入名單"):
        # 抓取第一欄，移除空值並轉成字串清單
        st.session_state.participants = df.iloc[:, 0].dropna().astype(str).tolist()
        st.success(f"✅ 成功載入 {len(st.session_state.participants)} 筆名單！")

st.write(f"**目前池內剩餘可抽獎人數：{len(st.session_state.participants)} 人**")
st.divider()

# --- 區塊 2: 獎項清單管理 ---
st.subheader("2. 獎項清單 (可編輯)")
st.write("你可以直接在下方的表格新增、修改獎項名稱與要抽出的數量：")
# 讓使用者可以動態編輯清單 (最小心力，最大效益的 UI)
edited_prizes = st.data_editor(
    st.session_state.prize_list,
    num_rows="dynamic",
    use_container_width=True,
    disabled=["狀態"] # 狀態欄位鎖定不給手動改，由程式控制
)
st.session_state.prize_list = edited_prizes
st.divider()

# --- 區塊 3: 抽獎與鎖定機制 ---
st.subheader("3. 進行抽獎")

# 找出表格中第一個狀態為「待抽」的獎項
pending_prizes = edited_prizes[edited_prizes["狀態"] == "待抽"]

if pending_prizes.empty:
    st.info("🎈 所有獎項都已經抽完囉！")
else:
    # 取出目前要抽的獎項資訊
    current_prize = pending_prizes.iloc[0]
    prize_name = current_prize["獎項名稱"]
    prize_count = current_prize["數量"]
    prize_idx = pending_prizes.index[0]

    st.markdown(f"### 目前正在抽取的獎項：**{prize_name}** (共 {prize_count} 名)")

    col1, col2 = st.columns(2)

    with col1:
        # 抽獎按鈕 (只要狀態被 locked，按鈕就會禁用)
        if st.button("🎯 抽出得獎者", disabled=st.session_state.locked, use_container_width=True):
            if len(st.session_state.participants) < prize_count:
                st.error("剩餘人數不足以抽出此獎項！請確認名單。")
            else:
                # 隨機抽出不重複的得獎者
                winners = random.sample(st.session_state.participants, prize_count)
                st.session_state.current_winners = winners

                # 將得獎者從名單中移除，避免下一個獎項重複中獎
                for w in winners:
                    st.session_state.participants.remove(w)

                # 更新該獎項狀態為已抽出
                st.session_state.prize_list.at[prize_idx, "狀態"] = "已抽出"

                # 鎖定系統，要求必須按取消/下一組
                st.session_state.locked = True
                st.rerun()

    with col2:
        # 解鎖按鈕
        if st.button("解鎖並進行下一組", disabled=not st.session_state.locked, use_container_width=True):
            st.session_state.locked = False
            st.session_state.current_winners = []
            st.rerun()

    # --- 區塊 4: 顯示結果 ---
    if st.session_state.locked:
        st.success("🎉 抽獎結果出爐！畫面已鎖定，請點擊右方按鈕進行下一組。")
        st.balloons() # 觸發慶祝動畫
        for i, winner in enumerate(st.session_state.current_winners):
            st.markdown(f"#### 🏆 得獎者 {i+1}: **{winner}**")