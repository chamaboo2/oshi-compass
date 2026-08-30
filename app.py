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
# 現在地 → 聖地の方位角
# 北0° / 東90° / 南180° / 西270°
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
# 色設定
# =========================================

if night_mode:

    background_color = "#12182B"
    text_color = "#F5F7FF"
    subtext_color = "#C6CDEA"

    accent_color = "#FF8FB1"
    accent_soft = "#2B3557"
    accent_line = "#43507B"

    input_background = "#1D2742"
    input_border = "#7081B0"

    button_background = "#294669"
    button_border = "#6F93BF"
    button_text = "#FFFFFF"

    card_background = "#18213A"
    card_border = "#35466F"

    compass_background = "#202B49"
    compass_border = "#7385B8"
    compass_arrow = "#FFB3C8"

    badge_background = "#2A3557"
    selected_background = "#243150"

else:

    background_color = "#FFFAFC"
    text_color = "#22304A"
    subtext_color = "#6E7890"

    accent_color = "#EF7DA0"
    accent_soft = "#FFF0F5"
    accent_line = "#F3C8D6"

    input_background = "#FFFFFF"
    input_border = "#AAB4C8"

    button_background = "#FFFFFF"
    button_border = "#D7BFD0"
    button_text = "#22304A"

    card_background = "#FFFFFF"
    card_border = "#EFD8E2"

    compass_background = "#FFF7FB"
    compass_border = "#E9CCD7"
    compass_arrow = "#EF7DA0"

    badge_background = "#FFF0F5"
    selected_background = "#EEF5FF"


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
    }}

    .stButton > button:hover {{
        border-color: {accent_color} !important;
        color: {accent_color} !important;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {card_background};
        border: 1px solid {card_border} !important;
        border-radius: 22px !important;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================
# STEP 12
# スマートフォン方位センサー Component
# =========================================

ORIENTATION_HTML = """
<div class="sensor-card">

    <div class="sensor-title">
        📱 方位センサー
    </div>

    <div class="sensor-description">
        スマートフォンの上側が向いている方角
    </div>

    <button class="sensor-start" data-role="start">
        方位センサーを開始
    </button>

    <div class="sensor-status" data-role="status">
        まだ開始していません
    </div>

    <div class="sensor-dial">

        <div class="north-label">
            N
        </div>

        <div class="sensor-needle" data-role="needle">

            <svg viewBox="0 0 100 100">
                <path
                    d="M50 6 L78 40 H62 V90 H38 V40 H22 Z"
                    fill="currentColor"
                />
            </svg>

        </div>

    </div>

    <div class="sensor-heading" data-role="heading">
        —°
    </div>

    <div class="sensor-source" data-role="source">
    </div>

</div>
"""


ORIENTATION_CSS = """
.sensor-card {
    background: var(--sensor-card-bg);
    border: 1px solid var(--sensor-border);
    border-radius: 24px;
    padding: 24px;
    text-align: center;
    color: var(--sensor-text);
    box-sizing: border-box;
    width: 100%;
}

.sensor-title {
    font-size: 24px;
    font-weight: 800;
    margin-bottom: 4px;
}

.sensor-description {
    font-size: 14px;
    opacity: 0.75;
    margin-bottom: 18px;
}

.sensor-start {
    border: 1px solid var(--sensor-border);
    background: var(--sensor-button-bg);
    color: var(--sensor-button-text);
    border-radius: 14px;
    padding: 11px 18px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
}

.sensor-status {
    min-height: 24px;
    margin: 14px 0;
    font-size: 14px;
    font-weight: 600;
}

.sensor-dial {
    width: 180px;
    height: 180px;
    position: relative;
    margin: 10px auto;
    border-radius: 50%;
    border: 3px solid var(--sensor-border);
    background: var(--sensor-dial-bg);
}

.north-label {
    position: absolute;
    top: 7px;
    left: 0;
    right: 0;
    font-weight: 800;
    font-size: 15px;
}

.sensor-needle {
    position: absolute;
    width: 110px;
    height: 110px;
    left: 35px;
    top: 35px;
    color: var(--sensor-arrow);
    transform: rotate(0deg);
    transform-origin: 50% 50%;
    transition: transform 80ms linear;
}

.sensor-needle svg {
    width: 100%;
    height: 100%;
}

.sensor-heading {
    font-size: 30px;
    font-weight: 800;
    margin-top: 12px;
}

.sensor-source {
    margin-top: 5px;
    font-size: 12px;
    opacity: 0.7;
}
"""


ORIENTATION_JS = """
export default function(component) {

    const {
        data,
        parentElement
    } = component;

    const card =
        parentElement.querySelector(".sensor-card");

    const startButton =
        parentElement.querySelector('[data-role="start"]');

    const status =
        parentElement.querySelector('[data-role="status"]');

    const headingDisplay =
        parentElement.querySelector('[data-role="heading"]');

    const sourceDisplay =
        parentElement.querySelector('[data-role="source"]');

    const needle =
        parentElement.querySelector('[data-role="needle"]');


    if (!card || !startButton) {
        return;
    }


    card.style.setProperty(
        "--sensor-card-bg",
        data.card_background
    );

    card.style.setProperty(
        "--sensor-border",
        data.card_border
    );

    card.style.setProperty(
        "--sensor-text",
        data.text_color
    );

    card.style.setProperty(
        "--sensor-button-bg",
        data.button_background
    );

    card.style.setProperty(
        "--sensor-button-text",
        data.button_text
    );

    card.style.setProperty(
        "--sensor-dial-bg",
        data.compass_background
    );

    card.style.setProperty(
        "--sensor-arrow",
        data.compass_arrow
    );


    let started = false;
    let receivedAnyEvent = false;
    let receivedAbsolute = false;
    let timeoutId = null;


    function normalizeHeading(value) {

        return (
            (value % 360) + 360
        ) % 360;

    }


    function directionName(value) {

        const directions = [
            "北",
            "北東",
            "東",
            "南東",
            "南",
            "南西",
            "西",
            "北西"
        ];

        const index =
            Math.floor(
                (value + 22.5) / 45
            ) % 8;

        return directions[index];
    }


    function extractHeading(event) {

        // iPhone / Safari系
        if (
            typeof event.webkitCompassHeading === "number"
            &&
            Number.isFinite(event.webkitCompassHeading)
        ) {

            return {
                heading:
                    normalizeHeading(
                        event.webkitCompassHeading
                    ),

                absolute: true,

                source:
                    "絶対方位"
            };
        }


        if (
            typeof event.alpha === "number"
            &&
            Number.isFinite(event.alpha)
        ) {

            const isAbsolute =
                event.absolute === true
                ||
                event.type ===
                    "deviceorientationabsolute";


            // DeviceOrientationのalphaは
            // コンパス方位と回転方向が逆なので
            // 360 - alpha にする
            const heading =
                normalizeHeading(
                    360 - event.alpha
                );


            return {
                heading: heading,
                absolute: isAbsolute,
                source:
                    isAbsolute
                    ? "絶対方位"
                    : "相対方位"
            };
        }


        return null;
    }


    function updateDisplay(result) {

        if (!result) {
            return;
        }


        receivedAnyEvent = true;


        if (result.absolute) {
            receivedAbsolute = true;
        }


        const heading =
            result.heading;


        needle.style.transform =
            `rotate(${heading}deg)`;


        headingDisplay.textContent =
            `${directionName(heading)} ${Math.round(heading)}°`;


        if (result.absolute) {

            status.textContent =
                "✅ 方位を取得しています";

            status.style.color =
                "#2f9b63";

            sourceDisplay.textContent =
                "地磁気を使った絶対方位";

        }

        else if (!receivedAbsolute) {

            status.textContent =
                "⚠️ 相対方位を取得中";

            status.style.color =
                "#c88724";

            sourceDisplay.textContent =
                "実際の北基準ではないため、まだ試験値です";

        }

    }


    function absoluteHandler(event) {

        const result =
            extractHeading(event);

        updateDisplay(result);

    }


    function orientationHandler(event) {

        if (receivedAbsolute) {
            return;
        }

        const result =
            extractHeading(event);

        updateDisplay(result);

    }


    async function startSensor() {

        if (started) {
            return;
        }


        if (!window.isSecureContext) {

            status.textContent =
                "HTTPS環境が必要です";

            return;
        }


        if (
            typeof DeviceOrientationEvent ===
            "undefined"
        ) {

            status.textContent =
                "この端末では方位センサーを利用できません";

            return;
        }


        try {

            if (
                typeof DeviceOrientationEvent
                    .requestPermission
                === "function"
            ) {

                let permission;


                try {

                    permission =
                        await DeviceOrientationEvent
                            .requestPermission(true);

                }

                catch (firstError) {

                    permission =
                        await DeviceOrientationEvent
                            .requestPermission();

                }


                if (permission !== "granted") {

                    status.textContent =
                        "方位センサーの利用が許可されませんでした";

                    return;
                }

            }


            started = true;

            startButton.disabled = true;

            startButton.textContent =
                "方位センサー起動中";


            status.textContent =
                "センサーを待っています…";


            window.addEventListener(
                "deviceorientationabsolute",
                absoluteHandler,
                true
            );


            window.addEventListener(
                "deviceorientation",
                orientationHandler,
                true
            );


            timeoutId =
                window.setTimeout(
                    () => {

                        if (!receivedAnyEvent) {

                            status.textContent =
                                "センサー情報を取得できません。スマートフォンで試してください。";

                        }

                    },
                    4000
                );

        }

        catch (error) {

            status.textContent =
                "方位センサーを開始できませんでした";

        }

    }


    startButton.onclick =
        startSensor;


    return () => {

        window.removeEventListener(
            "deviceorientationabsolute",
            absoluteHandler,
            true
        );

        window.removeEventListener(
            "deviceorientation",
            orientationHandler,
            true
        );


        if (timeoutId !== null) {

            clearTimeout(timeoutId);

        }


        startButton.onclick = null;

    };

}
"""


orientation_component = None


try:

    orientation_component = (
        st.components.v2.component(
            "oshi_compass_orientation_sensor",
            html=ORIENTATION_HTML,
            css=ORIENTATION_CSS,
            js=ORIENTATION_JS,
        )
    )

except Exception:

    orientation_component = None


# =========================================
# タイトル
# =========================================

st.markdown(
    f"""
    <div style="
        background:{accent_soft};
        border:1px solid {accent_line};
        border-radius:24px;
        padding:24px;
        margin-bottom:18px;
    ">

        <div style="
            font-size:48px;
            font-weight:800;
            color:{text_color};
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
# 現在選択中
# =========================================

if st.session_state.selected_seichi:

    selected_name = html.escape(
        st.session_state.selected_seichi["name"]
    )

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

location = streamlit_geolocation()


if (
    isinstance(location, dict)
    and location.get("latitude") is not None
    and location.get("longitude") is not None
):

    st.session_state.current_location = {
        "latitude":
            float(location["latitude"]),

        "longitude":
            float(location["longitude"]),

        "accuracy":
            location.get("accuracy"),
    }


if st.session_state.current_location:

    st.success(
        "📍 現在地を取得できました"
    )

else:

    st.info(
        "現在地を取得してください"
    )


# =========================================
# 聖地方向
# =========================================

if (
    st.session_state.current_location
    and
    st.session_state.selected_seichi
):

    current =
        st.session_state.current_location

    destination =
        st.session_state.selected_seichi


    bearing = calculate_bearing(
        current["latitude"],
        current["longitude"],
        destination["latitude"],
        destination["longitude"],
    )


    direction_name =
        get_direction_name(bearing)


    bearing_display =
        round(bearing)


    safe_name =
        html.escape(
            str(destination["name"])
        )


    # -----------------------------
    # 正しい矢印
    # SVGそのものは真上を向いている
    # 0° = 北
    # 90° = 東
    # -----------------------------

    arrow_svg = (
        f'<svg '
        f'viewBox="0 0 100 100" '
        f'style="'
        f'width:145px;'
        f'height:145px;'
        f'transform:rotate({bearing:.2f}deg);'
        f'transform-origin:50% 50%;'
        f'">'
        f'<path '
        f'd="M50 6 L78 40 H62 V90 H38 V40 H22 Z" '
        f'fill="{compass_arrow}"'
        f'/>'
        f'</svg>'
    )


    compass_html = (
        f'<div style="'
        f'background:{card_background};'
        f'border:1px solid {card_border};'
        f'border-radius:28px;'
        f'padding:30px 18px;'
        f'margin:24px 0;'
        f'text-align:center;'
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
        f'">'
        f'{arrow_svg}'
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


    st.markdown(
        compass_html,
        unsafe_allow_html=True
    )


# =========================================
# STEP 12 方位センサー
# =========================================

st.divider()

st.subheader(
    "STEP 12　スマートフォンの向き"
)

st.caption(
    "スマートフォンでは、まず画面を縦向きにして試してください。"
)


if orientation_component is not None:

    orientation_component(
        key="orientation_sensor",
        data={
            "card_background":
                card_background,

            "card_border":
                card_border,

            "text_color":
                text_color,

            "button_background":
                button_background,

            "button_text":
                button_text,

            "compass_background":
                compass_background,

            "compass_arrow":
                compass_arrow,
        },
        height=410,
    )

else:

    st.warning(
        "方位センサー用Componentを読み込めませんでした。"
    )


# =========================================
# 聖地検索
# =========================================

st.divider()

st.subheader(
    "聖地を探す"
)

st.markdown(
    "**🔎 行きたい場所・好きな場所を入力**"
)


place_name = st.text_input(
    "場所を入力",
    placeholder=
        "ここに入力　例：東京タワー、東京駅、秋葉原",
    label_visibility="collapsed"
)


if st.button(
    "検索",
    key="search_button"
):

    if not place_name.strip():

        st.warning(
            "場所の名前を入力してください"
        )

    else:

        with st.spinner(
            "場所を探しています..."
        ):

            try:

                result =
                    geocode_place(
                        place_name.strip()
                    )

                st.session_state.search_result =
                    result

                st.session_state.searched_name =
                    place_name.strip()


                if result is None:

                    st.warning(
                        "場所が見つかりませんでした"
                    )


            except urllib.error.HTTPError as e:

                st.session_state.search_result = None

                st.error(
                    f"検索サービスとの通信で"
                    f"エラーが発生しました"
                    f"（HTTP {e.code}）"
                )


            except Exception:

                st.session_state.search_result = None

                st.error(
                    "場所を検索できませんでした"
                )


# =========================================
# 検索結果
# =========================================

result =
    st.session_state.search_result


if result:

    geometry =
        result.get(
            "geometry",
            {}
        )

    properties =
        result.get(
            "properties",
            {}
        )

    coordinates =
        geometry.get(
            "coordinates",
            []
        )


    if len(coordinates) >= 2:

        longitude =
            float(coordinates[0])

        latitude =
            float(coordinates[1])


        result_name =
            properties.get(
                "name",
                st.session_state.searched_name
            )


        district =
            properties.get(
                "district",
                ""
            )

        city =
            properties.get(
                "city",
                ""
            )

        state =
            properties.get(
                "state",
                ""
            )

        country =
            properties.get(
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


        st.divider()

        st.subheader(
            "検索結果"
        )


        with st.container(
            border=True
        ):

            st.success(
                f"「{st.session_state.searched_name}」"
                f"を見つけました"
            )


            st.markdown(
                f"### 📍 "
                f"{st.session_state.searched_name}"
            )


            st.caption(
                " / ".join(place_parts)
            )


            if supabase_connected:

                if st.button(
                    "♡ 聖地に登録",
                    type="primary",
                    key="register_button"
                ):

                    try:

                        save_name =
                            st.session_state.searched_name


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
                                "この聖地はすでに"
                                "登録されています ♡"
                            )


                        else:

                            (
                                supabase
                                .table("seichi")
                                .insert(
                                    {
                                        "name":
                                            save_name,

                                        "latitude":
                                            latitude,

                                        "longitude":
                                            longitude,
                                    }
                                )
                                .execute()
                            )


                            st.success(
                                f"♡ 「{save_name}」を"
                                f"聖地に登録しました"
                            )


                    except Exception as e:

                        st.error(
                            "聖地を登録できませんでした"
                        )

                        st.caption(
                            f"エラー種類："
                            f"{type(e).__name__}"
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
                "id,name,latitude,"
                "longitude,created_at"
            )
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )


        seichi_list =
            response.data


        if not seichi_list:

            st.write(
                "まだ聖地が登録されていません。"
            )


        else:

            for seichi in seichi_list:

                with st.container(
                    border=True
                ):

                    col1, col2 =
                        st.columns(
                            [3, 1]
                        )


                    with col1:

                        st.markdown(
                            f"### ♡ "
                            f"{seichi['name']}"
                        )


                    with col2:

                        selected_now =
                            bool(
                                st.session_state
                                .selected_seichi
                                and
                                st.session_state
                                .selected_seichi
                                .get("id")
                                ==
                                seichi["id"]
                            )


                        button_label = (
                            "選択中"
                            if selected_now
                            else "選ぶ"
                        )


                        if st.button(
                            button_label,
                            key=
                                f"select_"
                                f"{seichi['id']}",
                            use_container_width=True,
                            disabled=selected_now
                        ):

                            st.session_state.selected_seichi = {
                                "id":
                                    seichi["id"],

                                "name":
                                    seichi["name"],

                                "latitude":
                                    seichi["latitude"],

                                "longitude":
                                    seichi["longitude"],
                            }

                            st.rerun()


    except Exception as e:

        st.error(
            "登録済みの聖地を"
            "読み込めませんでした"
        )

        st.caption(
            f"エラー種類："
            f"{type(e).__name__}"
        )


# =========================================
# データ提供元
# =========================================

st.divider()

st.caption(
    "検索データ：Photon / © OpenStreetMap contributors"
)
