import streamlit as st
import urllib.parse
import urllib.request
import urllib.error
import json
import math
import html

from supabase import create_client
from streamlit_geolocation import streamlit_geolocation


st.set_page_config(
    page_title="おしコンパス",
    page_icon="🧭",
    layout="centered"
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
except Exception:
    supabase = None
    supabase_connected = False


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

    with urllib.request.urlopen(request, timeout=15) as response:
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

    x = math.sin(longitude_difference) * math.cos(lat2)

    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(longitude_difference)
    )

    bearing = math.degrees(math.atan2(x, y))

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

    index = int((bearing + 22.5) // 45) % 8
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
# 色設定
# =========================================
if night_mode:
    background_color = "#12182b"
    text_color = "#f5f7ff"
    subtext_color = "#c6cdea"

    accent_color = "#ff8fb1"
    accent_soft = "#2b3557"
    accent_line = "#43507b"

    input_background = "#1d2742"
    input_border = "#7081b0"

    button_background = "#294669"
    button_border = "#6f93bf"
    button_text = "#ffffff"

    card_background = "#18213a"
    card_border = "#35466f"

    compass_background = "#202b49"
    compass_border = "#7385b8"
    compass_arrow = "#ffb3c8"

    badge_background = "#2a3557"
    selected_background = "#243150"
else:
    background_color = "#fffafc"
    text_color = "#22304a"
    subtext_color = "#6e7890"

    accent_color = "#ef7da0"
    accent_soft = "#fff0f5"
    accent_line = "#f3c8d6"

    input_background = "#ffffff"
    input_border = "#aab4c8"

    button_background = "#ffffff"
    button_border = "#d7bfd0"
    button_text = "#22304a"

    card_background = "#ffffff"
    card_border = "#efd8e2"

    compass_background = "#fff7fb"
    compass_border = "#e9ccd7"
    compass_arrow = "#ef7da0"

    badge_background = "#fff0f5"
    selected_background = "#eef5ff"


# =========================================
# 共通CSS
# =========================================
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {background_color};
    }}

    .block-container {{
        max-width: 820px;
        padding-top: 1.6rem;
        padding-bottom: 3rem;
    }}

    h1, h2, h3, p, div, label {{
        color: {text_color};
    }}

    div[data-testid="stTextInput"] input {{
        background-color: {input_background} !important;
        color: {text_color} !important;
        border: 2px solid {input_border} !important;
        border-radius: 16px !important;
        padding: 0.75rem 0.9rem !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}

    div[data-testid="stTextInput"] input::placeholder {{
        color: {subtext_color} !important;
    }}

    .stButton > button {{
        background-color: {button_background} !important;
        color: {button_text} !important;
        border: 1px solid {button_border} !important;
        border-radius: 16px !important;
        font-weight: 700 !important;
        padding: 0.55rem 1.0rem !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.05);
    }}

    .stButton > button:hover {{
        border-color: {accent_color} !important;
        color: {accent_color} !important;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {card_background};
        border: 1px solid {card_border} !important;
        border-radius: 22px !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.04);
    }}

    hr {{
        border-color: {accent_line};
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================
# タイトル
# =========================================
st.markdown(
    f"""
    <div style="
        background:{accent_soft};
        border:1px solid {accent_line};
        border-radius:24px;
        padding:24px 24px 20px 24px;
        margin-bottom:18px;
    ">
        <div style="
            font-size:48px;
            font-weight:800;
            color:{text_color};
            line-height:1.2;
        ">
            おしコンパス 🧭
        </div>
        <div style="
            margin-top:8px;
            font-size:24px;
            font-weight:700;
            color:{accent_color};
        ">
            好きな場所は、あっち！
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================
# 現在選択中の聖地
# =========================================
if st.session_state.selected_seichi:
    selected_name = html.escape(st.session_state.selected_seichi["name"])

    st.markdown(
        f"""
        <div style="
            background:{selected_background};
            border:1px solid {accent_line};
            border-radius:18px;
            padding:14px 18px;
            margin-bottom:16px;
            font-size:20px;
            font-weight:700;
            color:{text_color};
        ">
            🧭 現在の目的地：{selected_name}
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================
# 現在地
# =========================================
st.divider()
st.subheader("📍 現在地")

st.caption("下のボタンを押して、ブラウザの位置情報利用を許可してください。")

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
    st.success("📍 現在地を取得できました")
else:
    st.info("まだ現在地は取得されていません")


# =========================================
# コンパス表示
# =========================================
if st.session_state.current_location and st.session_state.selected_seichi:
    current = st.session_state.current_location
    destination = st.session_state.selected_seichi

    bearing = calculate_bearing(
        current["latitude"],
        current["longitude"],
        destination["latitude"],
        destination["longitude"],
    )

    direction_name = get_direction_name(bearing)
    bearing_display = round(bearing)
    safe_name = html.escape(str(destination["name"]))

    compass_html = (
        f'<div style="'
        f'background:{card_background};'
        f'border:1px solid {card_border};'
        f'border-radius:28px;'
        f'padding:30px 18px 28px 18px;'
        f'margin:24px 0 10px 0;'
        f'text-align:center;'
        f'box-shadow:0 8px 22px rgba(0,0,0,0.05);'
        f'">'
        f'<div style="'
        f'display:inline-block;'
        f'background:{badge_background};'
        f'border:1px solid {accent_line};'
        f'border-radius:999px;'
        f'padding:8px 16px;'
        f'font-size:16px;'
        f'font-weight:700;'
        f'color:{accent_color};'
        f'margin-bottom:18px;'
        f'">'
        f'おしの方向'
        f'</div>'
        f'<div style="'
        f'font-size:28px;'
        f'font-weight:800;'
        f'color:{text_color};'
        f'margin-bottom:20px;'
        f'">'
        f'{safe_name}はこっち！'
        f'</div>'
        f'<div style="'
        f'width:230px;'
        f'height:230px;'
        f'margin:0 auto;'
        f'border-radius:50%;'
        f'background:{compass_background};'
        f'border:4px solid {compass_border};'
        f'display:flex;'
        f'justify-content:center;'
        f'align-items:center;'
        f'box-shadow:inset 0 0 0 10px rgba(255,255,255,0.15);'
        f'">'
        f'<div style="'
        f'font-size:126px;'
        f'line-height:1;'
        f'color:{compass_arrow};'
        f'transform:rotate({bearing:.2f}deg);'
        f'transform-origin:center center;'
        f'display:inline-block;'
        f'">'
        f'➜'
        f'</div>'
        f'</div>'
        f'<div style="'
        f'font-size:34px;'
        f'font-weight:800;'
        f'color:{text_color};'
        f'margin-top:22px;'
        f'">'
        f'{direction_name}　{bearing_display}°'
        f'</div>'
        f'</div>'
    )

    st.markdown(compass_html, unsafe_allow_html=True)

elif st.session_state.selected_seichi and not st.session_state.current_location:
    st.info("目的地は選ばれています。次は現在地を取得してください。")

elif st.session_state.current_location and not st.session_state.selected_seichi:
    st.info("現在地は取得できています。次はお気に入りの聖地を選んでください。")


# =========================================
# 聖地検索
# =========================================
st.divider()
st.subheader("聖地を探す")
st.markdown("**🔎 行きたい場所・好きな場所を入力**")

place_name = st.text_input(
    "場所を入力",
    placeholder="ここに入力　例：東京タワー、東京駅、秋葉原",
    label_visibility="collapsed"
)

if st.button("検索", key="search_button"):
    if not place_name.strip():
        st.warning("場所の名前を入力してください")
    else:
        with st.spinner("場所を探しています..."):
            try:
                result = geocode_place(place_name.strip())
                st.session_state.search_result = result
                st.session_state.searched_name = place_name.strip()

                if result is None:
                    st.warning("場所が見つかりませんでした")
            except urllib.error.HTTPError as e:
                st.session_state.search_result = None
                st.error(f"検索サービスとの通信でエラーが発生しました（HTTP {e.code}）")
            except Exception:
                st.session_state.search_result = None
                st.error("場所を検索できませんでした")


# =========================================
# 検索結果
# =========================================
result = st.session_state.search_result

if result:
    geometry = result.get("geometry", {})
    properties = result.get("properties", {})
    coordinates = geometry.get("coordinates", [])

    if len(coordinates) >= 2:
        longitude = float(coordinates[0])
        latitude = float(coordinates[1])

        result_name = properties.get("name", st.session_state.searched_name)
        district = properties.get("district", "")
        city = properties.get("city", "")
        state = properties.get("state", "")
        country = properties.get("country", "")

        place_parts = [
            part for part in [result_name, district, city, state, country] if part
        ]

        st.divider()
        st.subheader("検索結果")

        with st.container(border=True):
            st.success(f"「{st.session_state.searched_name}」を見つけました")

            st.markdown(
                f"### 📍 {st.session_state.searched_name}"
            )

            st.caption(" / ".join(place_parts))

            if supabase_connected:
                if st.button("♡ 聖地に登録", type="primary", key="register_button"):
                    try:
                        save_name = st.session_state.searched_name

                        existing = (
                            supabase
                            .table("seichi")
                            .select("id")
                            .eq("name", save_name)
                            .eq("latitude", latitude)
                            .eq("longitude", longitude)
                            .limit(1)
                            .execute()
                        )

                        if existing.data:
                            st.info("この聖地はすでに登録されています ♡")
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

                            st.success(f"♡ 「{save_name}」を聖地に登録しました")
                    except Exception as e:
                        st.error("聖地を登録できませんでした")
                        st.caption(f"エラー種類：{type(e).__name__}")
            else:
                st.error("Supabaseに接続できないため登録できません")


# =========================================
# お気に入り一覧
# =========================================
st.divider()
st.subheader("♡ お気に入りの聖地")

if supabase_connected:
    try:
        response = (
            supabase
            .table("seichi")
            .select("id,name,latitude,longitude,created_at")
            .order("created_at", desc=True)
            .execute()
        )

        seichi_list = response.data

        if not seichi_list:
            st.write("まだ聖地が登録されていません。")
        else:
            for seichi in seichi_list:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(f"### ♡ {seichi['name']}")
                        st.caption("タップして目的地にできます")

                    with col2:
                        selected_now = bool(
                            st.session_state.selected_seichi
                            and st.session_state.selected_seichi.get("id") == seichi["id"]
                        )

                        button_label = "選択中" if selected_now else "選ぶ"

                        if st.button(
                            button_label,
                            key=f"select_{seichi['id']}",
                            use_container_width=True,
                            disabled=selected_now
                        ):
                            st.session_state.selected_seichi = {
                                "id": seichi["id"],
                                "name": seichi["name"],
                                "latitude": seichi["latitude"],
                                "longitude": seichi["longitude"],
                            }
                            st.rerun()

    except Exception as e:
        st.error("登録済みの聖地を読み込めませんでした")
        st.caption(f"エラー種類：{type(e).__name__}")


# =========================================
# データ提供元
# =========================================
st.divider()
st.caption("検索データ：Photon / © OpenStreetMap contributors")
