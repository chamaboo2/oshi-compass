import streamlit as st
import urllib.parse
import urllib.request
import json
import time
import threading


st.set_page_config(
    page_title="おしコンパス",
    page_icon="🧭"
)


# =========================================
# ジオコーディング
# 場所名 → 緯度・経度
# =========================================

class RateLimiter:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_request_time = 0.0


@st.cache_resource
def get_rate_limiter():
    return RateLimiter()


@st.cache_data(ttl=86400, show_spinner=False)
def geocode_place(place_name):

    limiter = get_rate_limiter()

    with limiter.lock:

        # Nominatimの利用制限に合わせて
        # リクエスト間隔を最低1秒あける
        elapsed = time.time() - limiter.last_request_time

        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        params = urllib.parse.urlencode(
            {
                "q": place_name,
                "format": "jsonv2",
                "limit": 1,
                "accept-language": "ja",
            }
        )

        url = (
            "https://nominatim.openstreetmap.org/search?"
            + params
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "oshi-compass-prototype/1.0",
                "Accept-Language": "ja",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:

            data = json.load(response)

        limiter.last_request_time = time.time()

    if data:
        return data[0]

    return None


# =========================================
# 検索結果を保持
# =========================================

if "search_result" not in st.session_state:
    st.session_state.search_result = None

if "searched_name" not in st.session_state:
    st.session_state.searched_name = ""


# =========================================
# 夜モード
# =========================================

night_mode = st.toggle("🌙 夜モード")


# =========================================
# デザイン
# =========================================

if night_mode:

    st.markdown(
        """
        <style>

        .stApp {
            background-color: #141827 !important;
            color: #F5F7FF !important;
        }

        h1, h2, h3, p, label {
            color: #F5F7FF !important;
        }

        hr {
            border-color: #303A55 !important;
        }

        div[data-testid="stTextInput"] input {
            background-color: #20283D !important;
            color: #FFFFFF !important;
            border: 2px solid #71809E !important;
            border-radius: 12px !important;
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: #AEB9CC !important;
        }

        div[data-testid="stTextInput"] input:focus {
            border: 2px solid #9FC5FF !important;
            box-shadow: 0 0 0 1px #9FC5FF !important;
        }

        .stButton button {
            background-color: #294669 !important;
            color: #FFFFFF !important;
            border: 1px solid #7795BA !important;
            border-radius: 12px !important;
        }

        .stButton button p,
        .stButton button span {
            color: #FFFFFF !important;
        }

        .stButton button:hover {
            background-color: #365A84 !important;
            color: #FFFFFF !important;
            border-color: #A3C2E6 !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

else:

    st.markdown(
        """
        <style>

        div[data-testid="stTextInput"] input {
            background-color: #FFFFFF !important;
            color: #222222 !important;
            border: 2px solid #A0A6B2 !important;
            border-radius: 12px !important;
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: #8B91A0 !important;
        }

        div[data-testid="stTextInput"] input:focus {
            border: 2px solid #607DA5 !important;
            box-shadow: 0 0 0 1px #607DA5 !important;
        }

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

        .stButton button:hover {
            background-color: #F3F5F8 !important;
            border-color: #8D98A8 !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


# =========================================
# メイン画面
# =========================================

st.title("おしコンパス 🧭")

st.write("好きな場所は、あっち！")

st.divider()

st.subheader("聖地を探す")

st.markdown(
    "**🔍 行きたい場所・好きな場所を入力**"
)

place_name = st.text_input(
    "場所を入力",
    placeholder="ここに入力　例：東京タワー、東京駅、秋葉原",
    label_visibility="collapsed"
)


# =========================================
# 検索
# =========================================

if st.button("検索"):

    if not place_name.strip():

        st.warning(
            "場所の名前を入力してください"
        )

    else:

        with st.spinner("場所を探しています..."):

            try:

                result = geocode_place(
                    place_name.strip()
                )

                st.session_state.search_result = result
                st.session_state.searched_name = place_name.strip()

            except Exception:

                st.session_state.search_result = None

                st.error(
                    "場所を検索できませんでした。"
                    "少し時間をおいて、もう一度試してください。"
                )


# =========================================
# 検索結果
# =========================================

result = st.session_state.search_result

if result:

    st.divider()

    st.subheader("検索結果")

    st.success(
        f"「{st.session_state.searched_name}」を見つけました"
    )

    st.write("**場所**")

    st.write(
        result["display_name"]
    )

    latitude = float(
        result["lat"]
    )

    longitude = float(
        result["lon"]
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "緯度",
            f"{latitude:.6f}"
        )

    with col2:
        st.metric(
            "経度",
            f"{longitude:.6f}"
        )


# =========================================
# OpenStreetMap表記
# =========================================

st.divider()

st.caption(
    "検索データ © OpenStreetMap contributors"
)
