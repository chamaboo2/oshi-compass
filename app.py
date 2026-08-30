import streamlit as st

st.set_page_config(
    page_title="おしコンパス",
    page_icon="🧭"
)

# -------------------------
# 夜モード
# -------------------------
night_mode = st.toggle("🌙 夜モード")

if night_mode:
    st.markdown("""
    <style>
    .stApp {
        background-color: #171724;
        color: #f5f3ff;
    }

    h1, h2, h3, p, label {
        color: #f5f3ff !important;
    }

    div[data-testid="stTextInput"] input {
        background-color: #272738 !important;
        color: #ffffff !important;
        border: 2px solid #77738f !important;
        border-radius: 12px !important;
    }

    div[data-testid="stTextInput"] input::placeholder {
        color: #aaa7ba !important;
    }

    div[data-testid="stTextInput"] input:focus {
        border: 2px solid #b5a7ff !important;
    }

    div[data-testid="stButton"] button {
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <style>
    div[data-testid="stTextInput"] input {
        background-color: #ffffff !important;
        color: #222222 !important;
        border: 2px solid #9b9ba6 !important;
        border-radius: 12px !important;
    }

    div[data-testid="stTextInput"] input::placeholder {
        color: #8b8b96 !important;
    }

    div[data-testid="stTextInput"] input:focus {
        border: 2px solid #6750a4 !important;
    }

    div[data-testid="stButton"] button {
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)


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
