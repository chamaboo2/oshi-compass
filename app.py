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
    "night_mode": False,
    "editing_seichi_id": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# =========================================
# 夜モード
# =========================================
night_mode = bool(st.session_state.night_mode)


if night_mode:
    c = {
        "bg": "#111827",
        "text": "#F7F4F2",
        "sub": "#B8BBC6",
        "accent": "#D6A0AE",
        "soft": "#1B2435",
        "line": "#354057",
        "input": "#182235",
        "input_border": "#5B667E",
        "button": "#26344D",
        "button_border": "#66748F",
        "button_text": "#FFFFFF",
        "card": "#171F30",
        "card_border": "#303B50",
        "dial": "#202A3D",
        "dial_border": "#59667E",
        "arrow": "#D79AAD",
        "badge": "#2A2635",
        "selected": "#252E42",
        "success": "#7CB596",
    }
else:
    c = {
        "bg": "#FAF7F5",
        "text": "#263247",
        "sub": "#777681",
        "accent": "#B86B7D",
        "soft": "#F3E9EB",
        "line": "#E4D7DA",
        "input": "#FFFEFD",
        "input_border": "#CFC6C8",
        "button": "#FFFFFF",
        "button_border": "#D8CCCF",
        "button_text": "#263247",
        "card": "#FFFFFF",
        "card_border": "#E9E0E2",
        "dial": "#FCF8F8",
        "dial_border": "#DDC9CF",
        "arrow": "#B76078",
        "badge": "#F4E7EA",
        "selected": "#F1EBE9",
        "success": "#4F8B6A",
    }


# =========================================
# 共通デザイン
# =========================================
st.markdown(
    f"""<style>
html, body {{
    background: {c["bg"]} !important;
}}

.stApp {{
    background-color: {c["bg"]};
}}

/* Streamlitの上部クロームを消して、タイトル切れと黒い余白を防ぐ */
header[data-testid="stHeader"] {{
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
}}

[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stDeployButton {{
    display: none !important;
}}

#MainMenu, footer {{
    visibility: hidden !important;
}}

div[data-testid="stAppViewContainer"] {{
    padding-top: 0 !important;
}}

.block-container {{
    max-width: 760px;
    padding-top: calc(0.72rem + env(safe-area-inset-top));
    padding-bottom: calc(1.8rem + env(safe-area-inset-bottom));
}}

h1, h2, h3, p, label {{
    color: {c["text"]};
}}

div[data-testid="stTextInput"] input {{
    background: {c["input"]} !important;
    color: {c["text"]} !important;
    border: 1px solid {c["input_border"]} !important;
    border-radius: 13px !important;
    box-shadow: none !important;
}}

div[data-testid="stTextInput"] input:focus {{
    border-color: {c["accent"]} !important;
    box-shadow: 0 0 0 2px {c["soft"]} !important;
}}

div[data-testid="stTextInput"] input::placeholder {{
    color: {c["sub"]} !important;
}}

.stButton > button,
.stFormSubmitButton > button {{
    background: {c["button"]} !important;
    color: {c["button_text"]} !important;
    border: 1px solid {c["button_border"]} !important;
    border-radius: 13px !important;
    font-weight: 700 !important;
    min-height: 42px;
}}

.stButton > button:hover,
.stFormSubmitButton > button:hover {{
    border-color: {c["accent"]} !important;
    color: {c["accent"]} !important;
}}

/* 主ボタンはアクセント色 */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {{
    background: {c["accent"]} !important;
    color: #FFFFFF !important;
    border-color: {c["accent"]} !important;
}}

div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {c["card"]};
    border: 1px solid {c["card_border"]} !important;
    border-radius: 16px !important;
}}

/* アコーディオンは開閉状態に関係なく高コントラスト */
details {{
    background: {c["card"]} !important;
    border: 1px solid {c["card_border"]} !important;
    border-radius: 15px !important;
    overflow: hidden;
}}

details > summary {{
    background: {c["card"]} !important;
    color: {c["text"]} !important;
    font-weight: 700 !important;
    padding: 0.62rem 0.78rem !important;
}}

details[open] > summary,
details > summary:hover {{
    background: {c["soft"]} !important;
    color: {c["text"]} !important;
}}

details > summary *,
details[open] > summary * {{
    color: {c["text"]} !important;
    fill: {c["text"]} !important;
}}

/* 夜モードが操作できることを見せる */
div[data-testid="stToggle"] {{
    width: fit-content;
    background: {c["card"]};
    border: 1px solid {c["card_border"]};
    border-radius: 999px;
    padding: 0.25rem 0.62rem;
    margin-bottom: 0.15rem;
}}

div[data-testid="stToggle"] p {{
    color: {c["text"]} !important;
    font-weight: 700 !important;
}}

hr {{
    border-color: {c["line"]} !important;
    margin: 0.65rem 0 !important;
}}

.favorite-name {{
    color: {c["text"]};
    font-size: 0.98rem;
    line-height: 1.25;
    font-weight: 750;
    padding-top: 0.48rem;
    overflow-wrap: anywhere;
}}

.favorite-edit-note {{
    color: {c["sub"]};
    font-size: 0.78rem;
}}

@media (max-width: 600px) {{
    .block-container {{
        max-width: 100%;
        padding-top: calc(0.58rem + env(safe-area-inset-top));
        padding-left: 0.72rem;
        padding-right: 0.72rem;
        padding-bottom: calc(1.35rem + env(safe-area-inset-bottom));
    }}

    div[data-testid="stVerticalBlock"] {{
        gap: 0.34rem;
    }}

    div[data-testid="stTextInput"] input {{
        min-height: 43px;
        font-size: 16px;
    }}

    .stButton > button,
    .stFormSubmitButton > button {{
        min-height: 42px;
        padding: 0.34rem 0.5rem !important;
        font-size: 0.88rem !important;
    }}

    details > summary {{
        padding: 0.54rem 0.68rem !important;
        min-height: 40px !important;
    }}

    .favorite-name {{
        font-size: 0.92rem;
        padding-top: 0.46rem;
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
    目的地はこっち
  </div>

  <div class="oshi-dial">
    <div class="oshi-arrow" data-role="arrow">
      <svg viewBox="0 0 100 100" aria-hidden="true">
        <path
          d="M50 5 L69 39 L58 36 L58 91 L42 91 L42 36 L31 39 Z"
          fill="currentColor"
        ></path>
      </svg>
    </div>
  </div>

  <div class="oshi-bearing" data-role="bearing">
    現在地を確認中…
  </div>

  <div class="oshi-distance" data-role="distance"></div>

  <button class="oshi-start" data-role="start">
    コンパスをひらく
  </button>

  <div class="oshi-status" data-role="status">
    位置情報とスマホの向きを使います
  </div>
</div>
"""


COMPASS_CSS = """
.oshi-card {
    width: 100%;
    box-sizing: border-box;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 26px;
    padding: 26px 18px 20px;
    text-align: center;
    color: var(--text);
}

.oshi-badge {
    display: inline-block;
    background: var(--badge);
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 7px 14px;
    color: var(--accent);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: .04em;
    margin-bottom: 14px;
}

.oshi-title {
    font-size: 27px;
    line-height: 1.35;
    font-weight: 800;
    margin-bottom: 20px;
}

.oshi-dial {
    width: min(58vw, 230px);
    height: min(58vw, 230px);
    margin: 0 auto;
    border-radius: 50%;
    background: var(--dial);
    border: 2px solid var(--dial-border);
    display: flex;
    justify-content: center;
    align-items: center;
    box-shadow: inset 0 0 0 9px rgba(255,255,255,.10);
}

.oshi-arrow {
    width: 62%;
    height: 62%;
    color: var(--arrow);
    transform: rotate(0deg);
    transform-origin: 50% 50%;
    transition: transform 80ms linear;
}

.oshi-arrow svg {
    width: 100%;
    height: 100%;
}

.oshi-bearing {
    font-size: 24px;
    font-weight: 800;
    margin-top: 18px;
}

.oshi-distance {
    min-height: 20px;
    margin-top: 4px;
    color: var(--sub);
    font-size: 13px;
}

.oshi-start {
    margin-top: 16px;
    width: min(100%, 260px);
    border: 1px solid var(--button-border);
    background: var(--button);
    color: var(--button-text);
    border-radius: 999px;
    padding: 12px 18px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
}

.oshi-start:disabled {
    opacity: .7;
}

.oshi-status {
    min-height: 20px;
    margin-top: 10px;
    font-size: 12px;
    color: var(--sub);
}

@media (max-width: 480px) {
    .oshi-card {
        border-radius: 22px;
        padding: 18px 12px 14px;
    }

    .oshi-badge {
        padding: 6px 12px;
        margin-bottom: 10px;
    }

    .oshi-title {
        font-size: 23px;
        margin-bottom: 14px;
    }

    .oshi-dial {
        width: min(54vw, 210px);
        height: min(54vw, 210px);
    }

    .oshi-bearing {
        font-size: 21px;
        margin-top: 13px;
    }

    .oshi-start {
        margin-top: 12px;
        padding: 10px 16px;
    }

    .oshi-status {
        margin-top: 7px;
    }
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
  const distanceText = q('[data-role="distance"]');

  if (!card || !title || !arrow || !bearingText || !start || !status || !distanceText) {
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

  title.textContent = `${destinationName}はこっち`;
  bearingText.textContent = "現在地を確認中…";
  distanceText.textContent = "";

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

  function formatBearingGuide(value) {
    const bearing = norm(value);
    const cardinals = ["北", "東", "南", "西"];
    const clockwise = ["東", "南", "西", "北"];
    const counterClockwise = ["西", "北", "東", "南"];

    let index = Math.round(bearing / 90) % 4;
    let base = index * 90;
    let diff = ((bearing - base + 540) % 360) - 180;
    const amount = Math.round(Math.abs(diff));

    if (amount <= 1) {
      return `${cardinals[index]}方向`;
    }

    const toward = diff > 0
      ? clockwise[index]
      : counterClockwise[index];

    return `${cardinals[index]}から${toward}へ${amount}°`;
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

  function calculateDistance(lat1Deg, lon1Deg, lat2Deg, lon2Deg) {
    const earthRadiusKm = 6371;
    const dLat = toRad(lat2Deg - lat1Deg);
    const dLon = toRad(lon2Deg - lon1Deg);
    const lat1 = toRad(lat1Deg);
    const lat2 = toRad(lat2Deg);

    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2)
      + Math.cos(lat1) * Math.cos(lat2)
      * Math.sin(dLon / 2) * Math.sin(dLon / 2);

    const distanceKm =
      earthRadiusKm * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return distanceKm;
  }

  function formatDistance(distanceKm) {
    if (distanceKm < 1) {
      return `約 ${Math.max(1, Math.round(distanceKm * 1000))} m`;
    }

    if (distanceKm < 10) {
      return `約 ${distanceKm.toFixed(1)} km`;
    }

    return `約 ${Math.round(distanceKm)} km`;
  }

  function applyCompass() {
    if (destinationBearing === null) {
      return;
    }

    bearingText.textContent =
      `方位 ${Math.round(destinationBearing)}°`;

    if (currentHeading === null) {
      arrow.style.transform = `rotate(${destinationBearing}deg)`;
      return;
    }

    const relativeBearing = norm(destinationBearing - currentHeading);
    arrow.style.transform = `rotate(${relativeBearing}deg)`;
  }

  function refreshStatus() {
    if (!gotLocation && !gotOrientation) {
      status.textContent = "現在地と向きを確認しています…";
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
      status.textContent = "✓ 方向を追跡中";
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

    const distanceKm = calculateDistance(
      latitude,
      longitude,
      destinationLat,
      destinationLon
    );

    distanceText.textContent =
      `${formatBearingGuide(destinationBearing)} ・ ${formatDistance(distanceKm)}`;

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
      status.textContent = "現在地と向きを確認しています…";

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
# =========================================
# タイトル
# =========================================
title_html = (
    f'<div style="padding:10px 2px 10px;">'
    f'<div style="font-size:13px;'
    f'font-weight:700;'
    f'letter-spacing:.12em;'
    f'color:{c["accent"]};'
    f'margin-bottom:5px;">OSHI COMPASS</div>'
    f'<div style="font-size:36px;'
    f'line-height:1.15;'
    f'font-weight:800;'
    f'color:{c["text"]};">'
    f'おしコンパス 🧭'
    f'</div>'
    f'<div style="margin-top:8px;'
    f'font-size:15px;'
    f'line-height:1.6;'
    f'font-weight:600;'
    f'color:{c["sub"]};">'
    f'足を向けて寝ちゃだめな場所、みっけ！'
    f'</div>'
    f'</div>'
)

st.markdown(
    title_html,
    unsafe_allow_html=True,
)

# 夜モードはトップ画面でもコンパス画面でも常に見える位置に置く
st.toggle(
    "🌙 夜モード　ON / OFF",
    key="night_mode",
)

if not supabase_connected:
    st.error("データベースに接続できませんでした")


# =========================================
# コンパス画面
# =========================================
if st.session_state.selected_seichi:
    if st.button(
        "← トップに戻る",
        key="back_to_top",
    ):
        st.session_state.selected_seichi = None
        st.session_state.search_result = None
        st.rerun()

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


# =========================================
# トップ画面
# =========================================
else:
    st.info(
        "下の「♡ 好きな場所」から、コンパスで指したい場所を選んでください。"
    )

    st.markdown(
        '<div style="height:6px"></div>',
        unsafe_allow_html=True,
    )

    # -----------------------------------------
    # 好きな場所を追加
    # -----------------------------------------
    with st.expander("＋ 好きな場所を追加", expanded=False):
        with st.form("place_search_form", clear_on_submit=False):
            place_name = st.text_input(
                "場所の名前",
                placeholder="例：東京タワー、東京駅、代々木公園",
            )
            search_submitted = st.form_submit_button(
                "場所を探す",
                use_container_width=True,
            )

        if search_submitted:
            if not place_name.strip():
                st.warning("場所の名前を入力してください。")
            else:
                with st.spinner("探しています…"):
                    try:
                        result = geocode_place(place_name.strip())
                        st.session_state.search_result = result
                        st.session_state.searched_name = place_name.strip()

                        if result is None:
                            st.warning("場所が見つかりませんでした。")
                    except urllib.error.HTTPError as error:
                        st.session_state.search_result = None
                        st.error(
                            f"検索サービスとの通信エラー（HTTP {error.code}）"
                        )
                    except Exception:
                        st.session_state.search_result = None
                        st.error("場所を検索できませんでした。")

        result = st.session_state.search_result

        if result:
            geometry = result.get("geometry", {})
            properties = result.get("properties", {})
            coordinates = geometry.get("coordinates", [])

            if len(coordinates) >= 2:
                longitude = float(coordinates[0])
                latitude = float(coordinates[1])

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

                with st.container(border=True):
                    st.markdown(
                        f"**📍 {st.session_state.searched_name}**"
                    )
                    st.caption(" / ".join(place_parts))

                    if supabase_connected:
                        if st.button(
                            "♡ 好きな場所に追加",
                            key="register_button",
                            use_container_width=True,
                        ):
                            try:
                                existing = (
                                    supabase
                                    .table("seichi")
                                    .select("id,name,latitude,longitude")
                                    .eq("latitude", latitude)
                                    .eq("longitude", longitude)
                                    .limit(1)
                                    .execute()
                                )

                                if existing.data:
                                    row = existing.data[0]
                                    st.session_state.selected_seichi = {
                                        "id": row["id"],
                                        "name": row["name"],
                                        "latitude": row["latitude"],
                                        "longitude": row["longitude"],
                                    }
                                    st.session_state.search_result = None
                                    st.rerun()

                                save_name = st.session_state.searched_name

                                inserted = (
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

                                if inserted.data:
                                    row = inserted.data[0]
                                    st.session_state.selected_seichi = {
                                        "id": row["id"],
                                        "name": row["name"],
                                        "latitude": row["latitude"],
                                        "longitude": row["longitude"],
                                    }

                                st.session_state.search_result = None
                                st.rerun()

                            except Exception as error:
                                st.error("好きな場所に追加できませんでした。")
                                st.caption(
                                    f"エラー種類：{type(error).__name__}"
                                )

    # -----------------------------------------
    # 好きな場所
    # -----------------------------------------
    st.markdown(
        '<div style="height:2px"></div>',
        unsafe_allow_html=True,
    )

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

            with st.expander(
                f"♡ 好きな場所（{len(seichi_list)}）",
                expanded=True,
            ):
                if not seichi_list:
                    st.caption(
                        "まだ登録がありません。「＋ 好きな場所を追加」から追加できます。"
                    )
                else:
                    for seichi in seichi_list:
                        with st.container(border=True):
                            name_col, compass_col, edit_col = st.columns(
                                [4.5, 3.4, 1.2],
                                gap="small",
                            )

                            with name_col:
                                safe_name = html.escape(str(seichi["name"]))
                                st.markdown(
                                    f'<div class="favorite-name">♡ {safe_name}</div>',
                                    unsafe_allow_html=True,
                                )

                            with compass_col:
                                if st.button(
                                    "コンパスで見る",
                                    key=f"favorite_{seichi['id']}",
                                    use_container_width=True,
                                    type="primary",
                                ):
                                    st.session_state.selected_seichi = {
                                        "id": seichi["id"],
                                        "name": seichi["name"],
                                        "latitude": seichi["latitude"],
                                        "longitude": seichi["longitude"],
                                    }
                                    st.session_state.editing_seichi_id = None
                                    st.rerun()

                            with edit_col:
                                if st.button(
                                    "✎",
                                    key=f"edit_{seichi['id']}",
                                    use_container_width=True,
                                    help="名前を編集",
                                ):
                                    if (
                                        st.session_state.editing_seichi_id
                                        == seichi["id"]
                                    ):
                                        st.session_state.editing_seichi_id = None
                                    else:
                                        st.session_state.editing_seichi_id = seichi["id"]
                                    st.rerun()

                            if (
                                st.session_state.editing_seichi_id
                                == seichi["id"]
                            ):
                                st.markdown(
                                    '<div class="favorite-edit-note">表示名を変更</div>',
                                    unsafe_allow_html=True,
                                )

                                with st.form(
                                    key=f"rename_form_{seichi['id']}",
                                    clear_on_submit=False,
                                ):
                                    new_name = st.text_input(
                                        "表示する名前",
                                        value=seichi["name"],
                                        key=f"rename_input_{seichi['id']}",
                                        label_visibility="collapsed",
                                    )

                                    save_col, close_col = st.columns(
                                        [1, 1],
                                        gap="small",
                                    )

                                    with save_col:
                                        rename_submitted = st.form_submit_button(
                                            "保存",
                                            use_container_width=True,
                                            type="primary",
                                        )

                                    with close_col:
                                        close_submitted = st.form_submit_button(
                                            "閉じる",
                                            use_container_width=True,
                                        )

                                if close_submitted:
                                    st.session_state.editing_seichi_id = None
                                    st.rerun()

                                if rename_submitted:
                                    cleaned_name = new_name.strip()

                                    if not cleaned_name:
                                        st.warning("名前を入力してください。")
                                    elif cleaned_name == seichi["name"]:
                                        st.session_state.editing_seichi_id = None
                                        st.rerun()
                                    else:
                                        try:
                                            (
                                                supabase
                                                .table("seichi")
                                                .update({"name": cleaned_name})
                                                .eq("id", seichi["id"])
                                                .execute()
                                            )
                                            st.session_state.editing_seichi_id = None
                                            st.rerun()

                                        except Exception as error:
                                            st.error("名前を変更できませんでした。")
                                            st.caption(
                                                "SupabaseのRLSでUPDATEが許可されているか確認してください。"
                                            )
                                            st.caption(
                                                f"エラー種類：{type(error).__name__}"
                                            )

        except Exception as error:
            st.error("好きな場所を読み込めませんでした。")
            st.caption(f"エラー種類：{type(error).__name__}")


st.markdown(
    '<div style="height:8px"></div>',
    unsafe_allow_html=True,
)
st.caption("地図データ：Photon / © OpenStreetMap contributors")
