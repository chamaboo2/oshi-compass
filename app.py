import streamlit as st
import urllib.parse
import urllib.request
import urllib.error
import json


st.set_page_config(
    page_title="おしコンパス",
    page_icon="🧭"
)


# =========================================
# 場所検索
# Photon：場所名 → 緯度・経度
# =========================================

@st.cache_data(ttl=86400, show_spinner=False)
def geocode_place(place_name):

    params = urllib.parse.urlencode(
        {
            "q": place_name,
            "lang": "ja",
            "limit": 1,
        }
    )

    url = (
        "https://photon.komoot.io/api/?"
        + params
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "oshi-compass-prototype/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=15
    ) as response:

        data = json.load(response)

    features = data.get("features", [])

    if not features:
        return None

    return features[0]


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

            except urllib.error.HTTPError as e:

                st.session_state.search_result = None

                st.error(
                    f"検索サービスとの通信でエラーが発生しました。"
                    f"（HTTP {e.code}）"
                )

            except urllib.error.URLError as e:

                st.session_state.search_result = None

                st.error(
                    "検索サービスに接続できませんでした。"
                )

                st.caption(
                    f"詳細：{e.reason}"
                )

            except Exception as e:

                st.session_state.search_result = None

                st.error(
                    "場所を検索できませんでした。"
                )

                st.caption(
                    f"詳細：{e}"
                )


# =========================================
# 検索結果
# =========================================

result = st.session_state.search_result

if result:

    geometry = result.get("geometry", {})
    properties = result.get("properties", {})

    coordinates = geometry.get(
        "coordinates",
        []
    )

    if len(coordinates) >= 2:

        longitude = float(coordinates[0])
        latitude = float(coordinates[1])

        st.divider()

        st.subheader("検索結果")

        st.success(
            f"「{st.session_state.searched_name}」を見つけました"
        )

        name = properties.get(
            "name",
            st.session_state.searched_name
        )

        city = properties.get("city", "")
        district = properties.get("district", "")
        state = properties.get("state", "")
        country = properties.get("country", "")

        place_parts = [
            part
            for part in [
                name,
                district,
                city,
                state,
                country,
            ]
            if part
        ]

        st.write("**場所**")

        st.write(
            " / ".join(place_parts)
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
# データ提供元
# =========================================

st.divider()

st.caption(
    "検索データ：Photon / © OpenStreetMap contributors"
)
