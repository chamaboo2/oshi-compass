import streamlit as st
import urllib.parse
import urllib.request
import urllib.error
import json
import math

from supabase import create_client
from streamlit_geolocation import streamlit_geolocation


st.set_page_config(
    page_title="おしコンパス",
    page_icon="🧭"
)


# =========================================
# Supabase接続
# =========================================

@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


try:
    supabase = get_supabase()

    supabase.table("seichi").select("id").limit(1).execute()

    supabase_connected = True
    supabase_error_type = ""

except Exception as e:
    supabase = None
    supabase_connected = False
    supabase_error_type = type(e).__name__


# =========================================
# 場所検索
# =========================================

@st.cache_data(ttl=86400, show_spinner=False)
def geocode_place(place_name):

    params = urllib.parse.urlencode(
        {
            "q": place_name,
            "limit": 1,
        }
    )

    url = "https://photon.komoot.io/api/?" + params

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "oshi-compass-prototype/1.0",
            "Accept-Language": "ja,en;q=0.8",
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
# 方位角計算
# =========================================

def calculate_bearing(
    start_latitude,
    start_longitude,
    destination_latitude,
    destination_longitude
):

    lat1 = math.radians(start_latitude)
    lat2 = math.radians(destination_latitude)

    longitude_difference = math.radians(
        destination_longitude - start_longitude
    )

    x = (
        math.sin(longitude_difference)
        * math.cos(lat2)
    )

    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1)
        * math.cos(lat2)
        * math.cos(longitude_difference)
    )

    bearing = math.degrees(
        math.atan2(x, y)
    )

    return (bearing + 360) % 360


# =========================================
# 方角名
# =========================================

def get_direction_name(bearing):

    directions = [
        "北",
        "北東",
        "東",
        "南東",
        "南",
        "南西",
        "西",
        "北西",
    ]

    index = int(
        (bearing + 22.5) // 45
    ) % 8

    return directions[index]


# =========================================
# セッション状態
# =========================================

if "search_result" not in st.session_state:
    st.session_state.search_result = None

if "searched_name" not in st.session_state:
    st.session_state.searched_name = ""

if "selected_seichi" not in st.session_state:
    st.session_state.selected_seichi = None

if "current_location" not in st.session_state:
    st.session_state.current_location = None


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
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #1C2437 !important;
            border-radius: 16px !important;
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
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FAFAFC !important;
            border-radius: 16px !important;
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


# =========================================
# Supabase接続確認
# 最終UI整理時に削除
# =========================================

if supabase_connected:
    st.success("✅ Supabase接続OK")

else:
    st.error("Supabaseに接続できませんでした")

    if supabase_error_type:
        st.caption(
            f"エラー種類：{supabase_error_type}"
        )


# =========================================
# 現在地
# =========================================

st.divider()

st.subheader("📍 現在地")

location = streamlit_geolocation()


if (
    isinstance(location, dict)
    and location.get("latitude") is not None
    and location.get("longitude") is not None
):

    st.session_state.current_location = {
        "latitude": float(location["latitude"]),
        "longitude": float(location["longitude"]),
        "accuracy": location.get("accuracy"),
    }


if st.session_state.current_location:

    st.success(
        "📍 現在地を取得できました"
    )

else:

    st.caption(
        "現在地を取得してください。"
    )


# =========================================
# コンパス表示
# =========================================

if (
    st.session_state.current_location
    and st.session_state.selected_seichi
):

    current = st.session_state.current_location
    destination = st.session_state.selected_seichi

    bearing = calculate_bearing(
        current["latitude"],
        current["longitude"],
        destination["latitude"],
        destination["longitude"],
    )

    direction_name = get_direction_name(
        bearing
    )

    bearing_display = round(bearing)

    st.divider()

    st.markdown(
        f"""
        <div style="
            text-align:center;
            padding:25px 10px 35px 10px;
        ">

            <div style="
                font-size:26px;
                font-weight:700;
                margin-bottom:15px;
            ">
                {destination["name"]}はこっち！
            </div>

            <div style="
                font-size:110px;
                line-height:1;
                transform:rotate({bearing}deg);
                display:inline-block;
                margin:15px;
            ">
                ↑
            </div>

            <div style="
                font-size:28px;
                font-weight:700;
                margin-top:15px;
            ">
                {direction_name}　{bearing_display}°
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


elif st.session_state.current_location:

    st.info(
        "♡ お気に入りの聖地から目的地を選んでください"
    )


# =========================================
# 聖地検索
# =========================================

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


if st.button("検索"):

    if not place_name.strip():

        st.warning(
            "場所の名前を入力してください"
        )

    else:

        with st.spinner(
            "場所を探しています..."
        ):

            try:

                result = geocode_place(
                    place_name.strip()
                )

                st.session_state.search_result = result
                st.session_state.searched_name = place_name.strip()

                if result is None:
                    st.warning(
                        "場所が見つかりませんでした。"
                    )

            except urllib.error.HTTPError as e:

                st.session_state.search_result = None

                st.error(
                    f"検索サービスとの通信でエラーが発生しました。"
                    f"（HTTP {e.code}）"
                )

            except Exception:

                st.session_state.search_result = None

                st.error(
                    "場所を検索できませんでした。"
                )


# =========================================
# 検索結果
# =========================================

result = st.session_state.search_result

if result:

    geometry = result.get(
        "geometry",
        {}
    )

    properties = result.get(
        "properties",
        {}
    )

    coordinates = geometry.get(
        "coordinates",
        []
    )

    if len(coordinates) >= 2:

        longitude = float(
            coordinates[0]
        )

        latitude = float(
            coordinates[1]
        )

        st.divider()

        st.subheader(
            "検索結果"
        )

        st.success(
            f"「{st.session_state.searched_name}」を見つけました"
        )

        result_name = properties.get(
            "name",
            st.session_state.searched_name
        )

        district = properties.get(
            "district",
            ""
        )

        city = properties.get(
            "city",
            ""
        )

        state = properties.get(
            "state",
            ""
        )

        country = properties.get(
            "country",
            ""
        )

        place_parts = [
            part
            for part in [
                result_name,
                district,
                city,
                state,
                country,
            ]
            if part
        ]

        st.write(
            "**場所**"
        )

        st.write(
            " / ".join(place_parts)
        )


        if supabase_connected:

            if st.button(
                "♡ 聖地に登録",
                type="primary"
            ):

                try:

                    save_name = (
                        st.session_state.searched_name
                    )

                    existing = (
                        supabase
                        .table("seichi")
                        .select("id")
                        .eq(
                            "name",
                            save_name
                        )
                        .eq(
                            "latitude",
                            latitude
                        )
                        .eq(
                            "longitude",
                            longitude
                        )
                        .limit(1)
                        .execute()
                    )

                    if existing.data:

                        st.info(
                            "この聖地はすでに登録されています ♡"
                        )

                    else:

                        (
                            supabase
                            .table("seichi")
                            .insert(
                                {
                                    "name": save_name,
                                    "latitude": latitude,
                                    "longitude": longitude,
                                }
                            )
                            .execute()
                        )

                        st.success(
                            f"♡ 「{save_name}」を聖地に登録しました"
                        )

                        st.rerun()

                except Exception as e:

                    st.error(
                        "聖地を登録できませんでした"
                    )

                    st.caption(
                        f"エラー種類：{type(e).__name__}"
                    )


# =========================================
# お気に入り
# =========================================

st.divider()

st.subheader(
    "♡ お気に入りの聖地"
)


if supabase_connected:

    try:

        response = (
            supabase
            .table("seichi")
            .select(
                "id,name,latitude,longitude,created_at"
            )
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        seichi_list = response.data

        if not seichi_list:

            st.write(
                "まだ聖地が登録されていません。"
            )

        else:

            for seichi in seichi_list:

                with st.container(
                    border=True
                ):

                    col1, col2 = st.columns(
                        [3, 1]
                    )

                    with col1:

                        st.markdown(
                            f"### ♡ {seichi['name']}"
                        )

                    with col2:

                        if st.button(
                            "この聖地を選ぶ",
                            key=f"select_{seichi['id']}",
                            use_container_width=True
                        ):

                            st.session_state.selected_seichi = {
                                "id": seichi["id"],
                                "name": seichi["name"],
                                "latitude": seichi["latitude"],
                                "longitude": seichi["longitude"],
                            }

                            st.rerun()

    except Exception as e:

        st.error(
            "登録済みの聖地を読み込めませんでした"
        )

        st.caption(
            f"エラー種類：{type(e).__name__}"
        )


# =========================================
# データ提供元
# =========================================

st.divider()

st.caption(
    "検索データ：Photon / © OpenStreetMap contributors"
)
