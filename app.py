import html
import json
import math
import urllib.error
import urllib.parse
import urllib.request

import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="おしコンパス",
    page_icon="🧭",
    layout="centered",
)


# =========================================
# Supabase
# =========================================
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


try:
    supabase = get_supabase()
    supabase.table("seichi").select("id").limit(1).execute()
    supabase_connected = True
except Exception:
    supabase = None
    supabase_connected = False


# =========================================
# 場所名 → 緯度経度
# =========================================
@st.cache_data(ttl=86400, show_spinner=False)
def geocode_place(place_name):
    params = urllib.parse.urlencode(
        {
            "q": place_name,
            "limit": 1,
        }
    )

    request = urllib.request.Request(
        "https://photon.komoot.io/api/?" + params,
        headers={
            "User-Agent": "oshi-compass-prototype/1.0",
            "Accept-Language": "ja,en;q=0.8",
        },
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.load(response)

    features = data.get("features", [])
    return features[0] if features else None


# =========================================
# 方位計算
# 北=0 / 東=90 / 南=180 / 西=270
# =========================================
def calculate_bearing(lat1, lon1, lat2, lon2):
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dl = math.radians(lon2 - lon1)

    x = math.sin(dl) * math.cos(p2)

    y = (
        math.cos(p1) * math.sin(p2)
        - math.sin(p1) * math.cos(p2) * math.cos(dl)
    )

    return (math.degrees(math.atan2(x, y)) + 360) % 360


def direction_name(bearing):
    names = [
        "北",
        "北東",
        "東",
        "南東",
        "南",
        "南西",
        "西",
        "北西",
    ]

    return names[int((bearing + 22.5) // 45) % 8]


# =========================================
# セッション状態
# =========================================
for key, default in {
    "search_result": None,
    "searched_name": "",
    "selected_seichi": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# =========================================
# 夜モード
# =========================================
night_mode = st.toggle("🌙 夜モード")


if night_mode:
    c = {
        "bg": "#12182B",
        "text": "#F5F7FF",
        "sub": "#C6CDEA",
        "accent": "#FF8FB1",
        "soft": "#2B3557",
        "line": "#43507B",
        "input": "#1D2742",
        "input_border": "#7081B0",
        "button": "#294669",
        "button_border": "#6F93BF",
        "button_text": "#FFFFFF",
        "card": "#18213A",
        "card_border": "#35466F",
        "dial": "#202B49",
        "dial_border": "#7385B8",
        "arrow": "#FFB3C8",
        "badge": "#2A3557",
        "selected": "#243150",
    }
else:
    c = {
        "bg": "#FFFAFC",
        "text": "#22304A",
        "sub": "#6E7890",
        "accent": "#EF7DA0",
        "soft": "#FFF0F5",
        "line": "#F3C8D6",
        "input": "#FFFFFF",
        "input_border": "#AAB4C8",
        "button": "#FFFFFF",
        "button_border": "#D7BFD0",
        "button_text": "#22304A",
        "card": "#FFFFFF",
        "card_border": "#EFD8E2",
        "dial": "#FFF7FB",
        "dial_border": "#E9CCD7",
        "arrow": "#EF7DA0",
        "badge": "#FFF0F5",
        "selected": "#EEF5FF",
    }


# =========================================
# 共通デザイン
# =========================================
st.markdown(
    f"""<style>
.stApp {{
    background-color: {c["bg"]};
}}
.block-container {{
    max-width: 820px;
    padding-top: 1.6rem;
    padding-bottom: 3rem;
}}
h1,h2,h3,p,label {{
    color: {c["text"]};
}}
div[data-testid="stTextInput"] input {{
    background: {c["input"]} !important;
    color: {c["text"]} !important;
    border: 2px solid {c["input_border"]} !important;
    border-radius: 16px !important;
}}
div[data-testid="stTextInput"] input::placeholder {{
    color: {c["sub"]} !important;
}}
.stButton > button {{
    background: {c["button"]} !important;
    color: {c["button_text"]} !important;
    border: 1px solid {c["button_border"]} !important;
    border-radius: 16px !important;
    font-weight: 700 !important;
}}
.stButton > button:hover {{
    border-color: {c["accent"]} !important;
    color: {c["accent"]} !important;
}}
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {c["card"]};
    border: 1px solid {c["card_border"]} !important;
    border-radius: 22px !important;
}}

@media (max-width: 600px) {{
    .block-container {{
        max-width: 100%;
        padding-top: 0.8rem;
        padding-left: 0.9rem;
        padding-right: 0.9rem;
        padding-bottom: 2rem;
    }}

    div[data-testid="stVerticalBlock"] {{
        gap: 0.55rem;
    }}

    .stButton > button {{
        min-height: 44px;
        font-size: 15px;
    }}

    div[data-testid="stTextInput"] input {{
        min-height: 46px;
        font-size: 16px;
    }}
}}

</style>""",
    unsafe_allow_html=True,
)


# =========================================
# リアルタイムおしコンパス
# 1つのコンパスだけ表示
# =========================================
COMPASS_HTML = """
<div class="oshi-card">
  <div class="oshi-badge">おしの方向</div>

  <div class="oshi-title" data-role="title">
    目的地はこっち！
  </div>

  <div class="oshi-dial">
    <div class="oshi-arrow" data-role="arrow">
      <svg viewBox="0 0 100 100">
        <path
          d="M50 5 L79 39 H63 V91 H37 V39 H21 Z"
          fill="currentColor"
        ></path>
      </svg>
    </div>
  </div>

  <div class="oshi-bearing" data-role="bearing">
    —
  </div>

  <button class="oshi-start" data-role="start">
    おしコンパスを開始
  </button>

  <div class="oshi-status" data-role="status">
    スマホを水平に持って開始してください
  </div>
</div>
"""


COMPASS_CSS = """
.oshi-card {
    width: 100%;
    box-sizing: border-box;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 28px;
    padding: 30px 18px 24px 18px;
    text-align: center;
    color: var(--text);
}

.oshi-badge {
    display: inline-block;
    background: var(--badge);
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 8px 16px;
    color: var(--accent);
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 18px;
}

.oshi-title {
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 22px;
}

.oshi-dial {
    width: 230px;
    height: 230px;
    margin: 0 auto;
    border-radius: 50%;
    background: var(--dial);
    border: 4px solid var(--dial-border);
    display: flex;
    justify-content: center;
    align-items: center;
}

.oshi-arrow {
    width: 145px;
    height: 145px;
    color: var(--arrow);
    transform: rotate(0deg);
    transform-origin: 50% 50%;
    transition: transform 70ms linear;
}

.oshi-arrow svg {
    width: 100%;
    height: 100%;
}

.oshi-bearing {
    font-size: 32px;
    font-weight: 800;
    margin-top: 20px;
}

.oshi-start {
    margin-top: 20px;
    border: 1px solid var(--button-border);
    background: var(--button);
    color: var(--button-text);
    border-radius: 16px;
    padding: 11px 18px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
}

.oshi-start:disabled {
    opacity: .7;
}

.oshi-status {
    min-height: 22px;
    margin-top: 10px;
    font-size: 13px;
    color: var(--sub);
}
"""


COMPASS_JS = r"""
export default function(component) {
  const { parentElement, data } = component;

  const q = (selector) => parentElement.querySelector(selector);

  const card = q(".oshi-card");
  const title = q('[data-role="title"]');
  const arrow = q('[data-role="arrow"]');
  const bearingText = q('[data-role="bearing"]');
  const start = q('[data-role="start"]');
  const status = q('[data-role="status"]');

  if (!card || !title || !arrow || !bearingText || !start || !status) {
    return;
  }

  card.style.setProperty("--card", data.card_background);
  card.style.setProperty("--border", data.card_border);
  card.style.setProperty("--text", data.text_color);
  card.style.setProperty("--sub", data.subtext_color);
  card.style.setProperty("--accent", data.accent_color);
  card.style.setProperty("--badge", data.badge_background);
  card.style.setProperty("--line", data.accent_line);
  card.style.setProperty("--dial", data.compass_background);
  card.style.setProperty("--dial-border", data.compass_border);
  card.style.setProperty("--arrow", data.compass_arrow);
  card.style.setProperty("--button", data.button_background);
  card.style.setProperty("--button-border", data.button_border);
  card.style.setProperty("--button-text", data.button_text);

  const destinationName = String(data.destination_name || "目的地");
  const destinationLat = Number(data.destination_latitude);
  const destinationLon = Number(data.destination_longitude);

  title.textContent = `${destinationName}はこっち！`;
  bearingText.textContent = "現在地を取得すると方角を表示";

  let started = false;
  let gotOrientation = false;
  let gotAbsolute = false;
  let gotLocation = false;
  let currentHeading = null;
  let destinationBearing = null;
  let watchId = null;
  let timer = null;

  const norm = (value) => ((value % 360) + 360) % 360;
  const toRad = (value) => value * Math.PI / 180;
  const toDeg = (value) => value * 180 / Math.PI;

  const directions = [
    "北", "北東", "東", "南東",
    "南", "南西", "西", "北西"
  ];

  function direction(value) {
    return directions[Math.floor((value + 22.5) / 45) % 8];
  }

  function calculateBearing(lat1Deg, lon1Deg, lat2Deg, lon2Deg) {
    const lat1 = toRad(lat1Deg);
    const lat2 = toRad(lat2Deg);
    const dLon = toRad(lon2Deg - lon1Deg);

    const x = Math.sin(dLon) * Math.cos(lat2);
    const y =
      Math.cos(lat1) * Math.sin(lat2)
      - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);

    return norm(toDeg(Math.atan2(x, y)));
  }

  function applyCompass() {
    if (destinationBearing === null) {
      return;
    }

    bearingText.textContent =
      `目的地：${direction(destinationBearing)} ${Math.round(destinationBearing)}°`;

    if (currentHeading === null) {
      arrow.style.transform = `rotate(${destinationBearing}deg)`;
      return;
    }

    const relativeBearing = norm(destinationBearing - currentHeading);
    arrow.style.transform = `rotate(${relativeBearing}deg)`;
  }

  function refreshStatus() {
    if (!gotLocation && !gotOrientation) {
      status.textContent = "現在地と方位を取得しています…";
      status.style.color = "";
      return;
    }

    if (!gotLocation) {
      status.textContent = "現在地を取得しています…";
      status.style.color = "";
      return;
    }

    if (!gotOrientation) {
      status.textContent = "スマホの向きを取得しています…";
      status.style.color = "";
      return;
    }

    if (gotAbsolute) {
      status.textContent = "✓ おしの方向を追跡中";
      status.style.color = "#2F9B63";
    } else {
      status.textContent =
        "方位は取得中ですが、北基準ではない可能性があります";
      status.style.color = "#C88724";
    }
  }

  function extractHeading(event) {
    if (
      typeof event.webkitCompassHeading === "number"
      && Number.isFinite(event.webkitCompassHeading)
    ) {
      return {
        heading: norm(event.webkitCompassHeading),
        absolute: true
      };
    }

    if (
      typeof event.alpha !== "number"
      || !Number.isFinite(event.alpha)
    ) {
      return null;
    }

    const absolute =
      event.absolute === true
      || event.type === "deviceorientationabsolute";

    return {
      heading: norm(360 - event.alpha),
      absolute
    };
  }

  function updateOrientation(result) {
    if (!result) return;

    gotOrientation = true;
    currentHeading = result.heading;

    if (result.absolute) {
      gotAbsolute = true;
    }

    applyCompass();
    refreshStatus();
  }

  const absoluteHandler = (event) => {
    updateOrientation(extractHeading(event));
  };

  const relativeHandler = (event) => {
    if (!gotAbsolute) {
      updateOrientation(extractHeading(event));
    }
  };

  function positionSuccess(position) {
    const latitude = position.coords.latitude;
    const longitude = position.coords.longitude;

    destinationBearing = calculateBearing(
      latitude,
      longitude,
      destinationLat,
      destinationLon
    );

    gotLocation = true;
    applyCompass();
    refreshStatus();
  }

  function positionError(error) {
    if (error && error.code === 1) {
      status.textContent = "位置情報の利用が許可されませんでした";
    } else {
      status.textContent = "現在地を取得できませんでした";
    }

    status.style.color = "#C54B4B";
  }

  async function startCompass() {
    if (started) return;

    if (!window.isSecureContext) {
      status.textContent = "HTTPS環境が必要です";
      return;
    }

    if (!navigator.geolocation) {
      status.textContent = "この端末では位置情報を利用できません";
      return;
    }

    if (typeof DeviceOrientationEvent === "undefined") {
      status.textContent = "この端末では方位センサーを利用できません";
      return;
    }

    try {
      if (typeof DeviceOrientationEvent.requestPermission === "function") {
        let permission;

        try {
          permission = await DeviceOrientationEvent.requestPermission(true);
        } catch (error) {
          permission = await DeviceOrientationEvent.requestPermission();
        }

        if (permission !== "granted") {
          status.textContent = "方位センサーの利用が許可されませんでした";
          status.style.color = "#C54B4B";
          return;
        }
      }

      started = true;
      start.style.display = "none";
      status.textContent = "現在地と方位を取得しています…";

      window.addEventListener(
        "deviceorientationabsolute",
        absoluteHandler,
        true
      );

      window.addEventListener(
        "deviceorientation",
        relativeHandler,
        true
      );

      watchId = navigator.geolocation.watchPosition(
        positionSuccess,
        positionError,
        {
          enableHighAccuracy: true,
          timeout: 12000,
          maximumAge: 3000
        }
      );

      timer = window.setTimeout(() => {
        if (!gotLocation || !gotOrientation) {
          refreshStatus();
        }
      }, 6000);

    } catch (error) {
      status.textContent = "おしコンパスを開始できませんでした";
      status.style.color = "#C54B4B";
    }
  }

  start.addEventListener("click", startCompass);

  return () => {
    window.removeEventListener(
      "deviceorientationabsolute",
      absoluteHandler,
      true
    );

    window.removeEventListener(
      "deviceorientation",
      relativeHandler,
      true
    );

    start.removeEventListener("click", startCompass);

    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
    }

    if (timer !== null) {
      window.clearTimeout(timer);
    }
  };
}
"""


try:
    realtime_compass = st.components.v2.component(
        "oshi_compass_realtime",
        html=COMPASS_HTML,
        css=COMPASS_CSS,
        js=COMPASS_JS,
    )
except Exception:
    realtime_compass = None


# =========================================
# タイトル
# =========================================
title_html = (
    f'<div style="background:{c["soft"]};'
    f'border:1px solid {c["line"]};'
    f'border-radius:22px;'
    f'padding:18px 20px;'
    f'margin-bottom:10px;">'
    f'<div style="font-size:38px;'
    f'line-height:1.15;'
    f'font-weight:800;'
    f'color:{c["text"]};">'
    f'おしコンパス 🧭'
    f'</div>'
    f'<div style="margin-top:6px;'
    f'font-size:17px;'
    f'font-weight:700;'
    f'color:{c["accent"]};">'
    f'足を向けて寝ちゃだめな場所、みっけ！'
    f'</div>'
    f'</div>'
)

st.markdown(
    title_html,
    unsafe_allow_html=True,
)


if not supabase_connected:
    st.error(
        "データベースに接続できませんでした"
    )


# =========================================
# 現在の目的地
# =========================================
if st.session_state.selected_seichi:
    selected_name = html.escape(
        str(
            st.session_state
            .selected_seichi["name"]
        )
    )

    selected_html = (
        f'<div style="background:{c["selected"]};'
        f'border:1px solid {c["line"]};'
        f'border-radius:18px;'
        f'padding:10px 14px;'
        f'margin-bottom:8px;'
        f'font-size:16px;'
        f'font-weight:700;'
        f'color:{c["text"]};">'
        f'🧭 現在の目的地：{selected_name}'
        f'</div>'
    )

    st.markdown(
        selected_html,
        unsafe_allow_html=True,
    )


# =========================================
# おしコンパス本体
# =========================================
if st.session_state.selected_seichi:
    destination = st.session_state.selected_seichi

    if realtime_compass is not None:
        realtime_compass(
            key=f"realtime_compass_{destination['id']}",
            data={
                "destination_name": destination["name"],
                "destination_latitude": destination["latitude"],
                "destination_longitude": destination["longitude"],
                "card_background": c["card"],
                "card_border": c["card_border"],
                "text_color": c["text"],
                "subtext_color": c["sub"],
                "accent_color": c["accent"],
                "accent_line": c["line"],
                "badge_background": c["badge"],
                "compass_background": c["dial"],
                "compass_border": c["dial_border"],
                "compass_arrow": c["arrow"],
                "button_background": c["button"],
                "button_border": c["button_border"],
                "button_text": c["button_text"],
            },
            width="stretch",
            height="content",
        )
    else:
        st.error("おしコンパスを読み込めませんでした")
else:
    st.info("お気に入りの聖地から目的地を選んでください")


# =========================================
# 聖地検索
# =========================================
st.markdown("<div style=\"height:4px\"></div>", unsafe_allow_html=True)

st.markdown("### 🔎 聖地を探す")

st.caption("行きたい場所・好きな場所を入力")

place_name = st.text_input(
    "場所を入力",
    placeholder=
        "ここに入力　例：東京タワー、東京駅、秋葉原",
    label_visibility="collapsed",
)


if st.button(
    "検索",
    key="search_button",
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
                result = geocode_place(
                    place_name.strip()
                )

                st.session_state.search_result = (
                    result
                )

                st.session_state.searched_name = (
                    place_name.strip()
                )

                if result is None:
                    st.warning(
                        "場所が見つかりませんでした"
                    )

            except urllib.error.HTTPError as error:
                st.session_state.search_result = None

                st.error(
                    f"検索サービスとの通信エラー"
                    f"（HTTP {error.code}）"
                )

            except Exception:
                st.session_state.search_result = None

                st.error(
                    "場所を検索できませんでした"
                )


# =========================================
# 検索結果
# =========================================
result = st.session_state.search_result

if result:
    geometry = result.get(
        "geometry",
        {},
    )

    properties = result.get(
        "properties",
        {},
    )

    coordinates = geometry.get(
        "coordinates",
        [],
    )

    if len(coordinates) >= 2:
        longitude = float(
            coordinates[0]
        )

        latitude = float(
            coordinates[1]
        )

        result_name = properties.get(
            "name",
            st.session_state.searched_name,
        )

        place_parts = [
            part
            for part in [
                result_name,
                properties.get("district", ""),
                properties.get("city", ""),
                properties.get("state", ""),
                properties.get("country", ""),
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
                f"「"
                f"{st.session_state.searched_name}"
                f"」を見つけました"
            )

            st.markdown(
                f"### 📍 "
                f"{st.session_state.searched_name}"
            )

            st.caption(
                " / ".join(
                    place_parts
                )
            )

            if (
                supabase_connected
                and st.button(
                    "♡ 聖地に登録",
                    type="primary",
                    key="register_button",
                )
            ):
                try:
                    save_name = (
                        st.session_state
                        .searched_name
                    )

                    existing = (
                        supabase
                        .table("seichi")
                        .select("id")
                        .eq("latitude", latitude)
                        .eq("longitude", longitude)
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
                                    "name": save_name,
                                    "latitude": latitude,
                                    "longitude": longitude,
                                }
                            )
                            .execute()
                        )

                        st.success(
                            f"♡ 「{save_name}」を"
                            f"聖地に登録しました"
                        )

                except Exception as error:
                    st.error(
                        "聖地を登録できませんでした"
                    )

                    st.caption(
                        f"エラー種類："
                        f"{type(error).__name__}"
                    )


# =========================================
# お気に入り
# =========================================
st.divider()

st.markdown("### ♡ お気に入りの聖地")

if supabase_connected:
    try:
        response = (
            supabase
            .table("seichi")
            .select("id,name,latitude,longitude,created_at")
            .order("created_at", desc=True)
            .execute()
        )

        seichi_list = response.data or []

        if not seichi_list:
            st.info("まだ聖地が登録されていません。")
        else:
            for seichi in seichi_list:
                selected_now = bool(
                    st.session_state.selected_seichi
                    and st.session_state.selected_seichi.get("id") == seichi["id"]
                )

                with st.container(border=True):
                    if selected_now:
                        st.markdown(f"#### ♡ {seichi['name']}　✓ 選択中")
                    else:
                        st.markdown(f"#### ♡ {seichi['name']}")

                    if not selected_now:
                        if st.button(
                            "この場所を選ぶ",
                            key=f"favorite_{seichi['id']}",
                            use_container_width=True,
                        ):
                            st.session_state.selected_seichi = {
                                "id": seichi["id"],
                                "name": seichi["name"],
                                "latitude": seichi["latitude"],
                                "longitude": seichi["longitude"],
                            }
                            st.rerun()

                    with st.expander("✏️ 名前を変更"):
                        with st.form(
                            key=f"rename_form_{seichi['id']}",
                            clear_on_submit=False,
                        ):
                            new_name = st.text_input(
                                "新しい名前",
                                value=seichi["name"],
                                key=f"rename_input_{seichi['id']}",
                            )

                            rename_submitted = st.form_submit_button(
                                "名前を保存",
                                use_container_width=True,
                            )

                        if rename_submitted:
                            cleaned_name = new_name.strip()

                            if not cleaned_name:
                                st.warning("新しい名前を入力してください。")
                            elif cleaned_name == seichi["name"]:
                                st.info("名前は変更されていません。")
                            else:
                                try:
                                    (
                                        supabase
                                        .table("seichi")
                                        .update({"name": cleaned_name})
                                        .eq("id", seichi["id"])
                                        .execute()
                                    )

                                    if selected_now:
                                        st.session_state.selected_seichi = {
                                            "id": seichi["id"],
                                            "name": cleaned_name,
                                            "latitude": seichi["latitude"],
                                            "longitude": seichi["longitude"],
                                        }

                                    st.success(
                                        f"「{seichi['name']}」を「{cleaned_name}」に変更しました。"
                                    )
                                    st.rerun()

                                except Exception as error:
                                    st.error("名前を変更できませんでした。")
                                    st.caption(
                                        "SupabaseのRLSでUPDATEが許可されているかも確認してください。"
                                    )
                                    st.caption(
                                        f"エラー種類：{type(error).__name__}"
                                    )

    except Exception as error:
        st.error("登録済みの聖地を読み込めませんでした")
        st.caption(f"エラー種類：{type(error).__name__}")


st.divider()

st.caption(
    "検索データ：Photon / © OpenStreetMap contributors"
)
