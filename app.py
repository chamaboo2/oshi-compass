import streamlit as st

st.set_page_config(
    page_title="おしコンパス",
    page_icon="🧭"
)

# -------------------------
# 夜モード切り替え
# -------------------------
night_mode = st.toggle("🌙 夜モード")


# -------------------------
# デザイン
# -------------------------
if night_mode:
    st.markdown(
        """
        <style>

        /* 全体背景 */
        .stApp {
            background-color: #141827 !important;
            color: #F5F7FF !important;
        }

        /* 見出し・通常文字 */
        h1, h2, h3, p, label {
            color: #F5F7FF !important;
        }

        /* 区切り線 */
        hr {
            border-color: #303A55 !important;
        }

        /* 入力欄 */
        div[data-testid="stTextInput"] input {
            background-color: #20283D !important;
            color: #FFFFFF !important;
            border: 2px solid #71809E !important;
            border-radius: 12px !important;
        }

        /* 入力欄の例文 */
        div[data-testid="stTextInput"] input::placeholder {
            color: #AEB9CC !important;
        }

        /* 入力中の枠 */
        div[data-testid="stTextInput"] input:focus {
            border: 2px solid #9FC5FF !important;
            box-shadow: 0 0 0 1px #9FC5FF !important;
        }

        /* 検索ボタン */
        .stButton button {
            background-color: #294669 !important;
            color: #FFFFFF !important;
            border: 1px solid #7795BA !important;
            border-radius: 12px !important;
        }

        /* ボタン内の文字 */
        .stButton button p,
        .stButton button span {
            color: #FFFFFF !important;
        }

        /* マウスを乗せた検索ボタン */
        .stButton button:hover {
            background-color: #365A84 !important;
            color: #FFFFFF !important;
            border-color: #A3C2E6 !important;
        }

        /* ボタンを押した時 */
        .stButton button:active {
            background-color: #203A59 !important;
            color: #FFFFFF !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

else:
    st.markdown(
        """
        <style>

        /* 入力欄 */
        div[data-testid="stTextInput"] input {
            background-color: #FFFFFF !important;
            color: #222222 !important;
            border: 2px solid #A0A6B2 !important;
            border-radius: 12px !important;
        }

        /* 入力欄の例文 */
        div[data-testid="stTextInput"] input::placeholder {
            color: #8B91A0 !important;
        }

        /* 入力中の枠 */
        div[data-testid="stTextInput"] input:focus {
            border: 2px solid #607DA5 !important;
            box-shadow: 0 0 0 1px #607DA5 !important;
        }

        /* 検索ボタン */
        .stButton button {
            background-color: #FFFFFF !important;
            color: #222222 !important;
            border: 1px solid #CDD1D8 !important;
            border-radius: 12px !important;
        }

        .stButton button p,
        .stButton button span {
            color: #222222 !important;
        }

        /* マウスを乗せた検索ボタン */
        .stButton button:hover {
            background-color: #F3F5F8 !important;
            border-color: #8D98A8 !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


# -------------------------
# メイン画面
# -------------------------
st.title("おしコンパス 🧭")
st.write("好きな場所は、あっち！")

st.divider()

st.subheader("聖地を探す")

st.markdown("**🔍 行きたい場所・好きな場所を入力**")

place_name = st.text_input(
    "場所を入力",
    placeholder="ここに入力　例：東京タワー、東京駅、秋葉原",
    label_visibility="collapsed"
)

if st.button("検索"):
    if place_name:
        st.write(f"検索する場所：{place_name}")
    else:
        st.warning("場所の名前を入力してください")
