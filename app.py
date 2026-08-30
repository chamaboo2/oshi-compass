import html
import json
import math
import textwrap
import urllib.error
import urllib.parse
import urllib.request

import streamlit as st
from streamlit_geolocation import streamlit_geolocation
from supabase import create_client


st.set_page_config(
    page_title="おしコンパス",
    page_icon="🧭",
    layout="centered",
)


def render_html(markup):
    st.markdown(
        textwrap.dedent(markup).strip(),
        unsafe_allow_html=True,
    )


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


for key, default in {
    "search_result": None,
    "searched_name": "",
    "selected_seichi": None,
    "current_location": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


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


render_html(
    f"""
    <style>
    .stApp {{
        background: {c["bg"]};
    }}

    .block-container {{
        max-width: 820px;
        padding-top: 1.4rem;
        padding-bottom: 3rem;
    }}

    h1,h2,h3,p,div,label {{
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
    </style>
    """
)


COMPASS_HTML = """
<div class="oshi-card">
  <div class="oshi-badge">おしの方向</div>
  <div class="oshi-title" data-role="title">目的地はこっち！</div>

  <div class="oshi-dial">
    <div class="oshi-arrow" data-role="arrow">
      <svg viewBox="0 0 100 100">
        <path
          d="M50 6 L78 40 H62 V90 H38 V40 H22 Z"
          fill="currentColor"
        ></path>
      </svg>
    </div>
  </div>

  <div class="oshi-bearing" data-role="bearing">—</div>

  <button class="oshi-start" data-role="start">
    おしコンパスを開始
  </button>

  <div class="oshi-status" data-role="status">
    スマホの向きを取得すると矢印が動きます
  </div>
</div>
"""


COMPASS_CSS = """
.oshi-card {
    width: 100%;
    box-sizing: border-box;
    background: var(--card);
    border: 1px solid var(--card-border);
    border-radius: 28px;
    padding: 28px 18px 24px;
    text-align: center;
    color: var(--text);
}

.oshi-badge {
    display: inline-block;
    background: var(--badge);
    border: 1px solid var(--line);
    color: var(--accent);
    border-radius: 999px;
    padding: 8px 16px;
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 18px;
}

.oshi-title {
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 20px;
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
    transition: transform 80ms linear;
}

.oshi-arrow svg {
    width: 100%;
    height: 100%;
}

.oshi-bearing {
    font-size: 34px;
    font-weight: 800;
    margin-top: 20px;
}

.oshi-start {
    margin-top: 18px;
    border: 1px solid var(--button-border);
    background: var(--button-bg);
    color: var(--button-text);
    border-radius: 16px;
    padding: 11px 18px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
}

.oshi-start:disabled {
    opacity: .65;
    cursor: default;
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
  card.style.setProperty("--card-border", data.card_border);
  card.style.setProperty("--text", data.text_color);
  card.style.setProperty("--sub", data.subtext_color);
  card.style.setProperty("--badge", data.badge_background);
  card.style.setProperty("--line", data.line_color);
  card.style.setProperty("--accent", data.accent_color);
  card.style.setProperty("--dial", data.compass_background);
  card.style.setProperty("--dial-border", data.compass_border);
  card.style.setProperty("--arrow", data.compass_arrow);
  card.style.setProperty("--button-bg", data.button_background);
  card.style.setProperty("--button-border", data.button_border);
  card.style.setProperty("--button-text", data.button_text);

  const targetBearing = Number(data.target_bearing);
  const targetName = String(data.target_name ?? "目的地");
  const targetDirection = String(data.target_direction ?? "");
  const targetBearingRounded = Math.round(targetBearing);

  title.textContent = `${targetName}はこっち！`;
  bearingText.textContent = `${targetDirection} ${targetBearingRounded}°`;

  // センサー開始前は、北を画面上とした絶対方位を表示
  arrow.style.transform = `rotate(${targetBearing}deg)`;

  let started = false;
  let gotEvent = false;
  let gotAbsolute = false;
  let timer = null;

  const norm = (value) => ((value % 360) + 360) % 360;

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

  function update(result) {
    if (!result) return;

    gotEvent = true;
    if (result.absolute) gotAbsolute = true;

    // 目的地の絶対方位 - スマホの絶対方位
    // 0°なら、スマホが目的地の方向を向いている
    const relative = norm(targetBearing - result.heading);
    arrow.style.transform = `rotate(${relative}deg)`;

    if (result.absolute) {
      status.textContent = "✅ おしの方向を追跡中";
      status.style.color = "#2F9B63";
    } else if (!gotAbsolute) {
      status.textContent = "⚠️ 相対方位で追跡中";
      status.style.color = "#C88724";
    }
  }

  const absoluteHandler = (event) => update(extractHeading(event));

  const relativeHandler = (event) => {
    if (!gotAbsolute) {
      update(extractHeading(event));
    }
  };

  async function startCompass() {
    if (started) return;

    if (!window.isSecureContext) {
      status.textContent = "HTTPS環境が必要です";
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
          return;
        }
      }

      started = true;
      start.disabled = true;
      start.textContent = "おしコンパス起動中";
      status.textContent = "スマホの向きを取得しています…";

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

      timer = window.setTimeout(() => {
        if (!gotEvent) {
          status.textContent = "方位情報を取得できませんでした";
        }
      }, 5000);

    } catch (error) {
      status.textContent = "おしコンパスを開始できませんでした";
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

    start.removeEventListener(
      "click",
      startCompass
    );

    if (timer !== null) {
      window.clearTimeout(timer);
    }
  };
}
"""


try:
    compass_component = st.components.v2.component(
        "oshi_compass_live",
        html=COMPASS_HTML,
        css=COMPASS_CSS,
        js=COMPASS_JS,
    )
except Exception:
    compass_component = None


render_html(
    f"""
    <div style="
        background:{c["soft"]};
        border:1px solid {c["line"]};
        border-radius:24px;
        padding:24px;
        margin-bottom:18px;
    ">
        <div style="
            font-size:48px;
            font-weight:800;
            color:{c["text"]};
        ">
            おしコンパス 🧭
        </div>

        <div style="
            margin-top:8px;
            font-size:24px;
            font-weight:700;
            color:{c["accent"]};
        ">
            好きな場所は、あっち！
        </div>
    </div>
    """
)


if not supabase_connected:
    st.error(
        "データベースに接続できませんでした"
    )


if st.session_state.selected_seichi:
    selected_name = html.escape(
        str(
            st.session_state
            .selected_seichi["name"]
        )
    )

    render_html(
        f"""
        <div style="
            background:{c["selected"]};
            border:1px solid {c["line"]};
            border-radius:18px;
            padding:14px 18px;
            margin-bottom:16px;
            font-size:20px;
            font-weight:700;
            color:{c["text"]};
        ">
            🧭 現在の目的地：{selected_name}
        </div>
        """
    )


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
    st.info(
        "現在地を取得してください"
    )


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

    if compass_component is not None:
        compass_component(
            key="live_oshi_compass",
            data={
                "target_bearing": bearing,
                "target_name": destination["name"],
                "target_direction": direction_name(bearing),
                "card_background": c["card"],
                "card_border": c["card_border"],
                "text_color": c["text"],
                "subtext_color": c["sub"],
                "badge_background": c["badge"],
                "line_color": c["line"],
                "accent_color": c["accent"],
                "compass_background": c["dial"],
                "compass_border": c["dial_border"],
                "compass_arrow": c["arrow"],
                "button_background": c["button"],
                "button_border": c["button_border"],
                "button_text": c["button_text"],
            },
            width="stretch",
            height=500,
        )
    else:
        st.warning(
            "コンパスを読み込めませんでした"
        )

elif st.session_state.current_location:
    st.info(
        "お気に入りの聖地から目的地を選んでください"
    )


st.divider()
st.subheader("聖地を探す")
st.markdown(
    "**🔎 行きたい場所・好きな場所を入力**"
)

place_name = st.text_input(
    "場所を入力",
    placeholder="ここに入力　例：東京タワー、東京駅、秋葉原",
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

                st.session_state.search_result = result
                st.session_state.searched_name = place_name.strip()

                if result is None:
                    st.warning(
                        "場所が見つかりませんでした"
                    )

            except urllib.error.HTTPError as error:
                st.session_state.search_result = None
                st.error(
                    f"検索サービスとの通信エラー（HTTP {error.code}）"
                )

            except Exception:
                st.session_state.search_result = None
                st.error(
                    "場所を検索できませんでした"
                )


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
                f"「{st.session_state.searched_name}」を見つけました"
            )

            st.markdown(
                f"### 📍 {st.session_state.searched_name}"
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
                        .eq("name", save_name)
                        .eq("latitude", latitude)
                        .eq("longitude", longitude)
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

                except Exception as error:
                    st.error(
                        "聖地を登録できませんでした"
                    )

                    st.caption(
                        f"エラー種類：{type(error).__name__}"
                    )


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
                desc=True,
            )
            .execute()
        )

        if not response.data:
            st.write(
                "まだ聖地が登録されていません。"
            )
        else:
            for seichi in response.data:
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
                        selected_now = bool(
                            st.session_state.selected_seichi
                            and st.session_state.selected_seichi.get("id")
                            == seichi["id"]
                        )

                        if st.button(
                            "選択中"
                            if selected_now
                            else "選ぶ",
                            key=f"select_{seichi['id']}",
                            use_container_width=True,
                            disabled=selected_now,
                        ):
                            st.session_state.selected_seichi = {
                                "id": seichi["id"],
                                "name": seichi["name"],
                                "latitude": seichi["latitude"],
                                "longitude": seichi["longitude"],
                            }

                            st.rerun()

    except Exception as error:
        st.error(
            "登録済みの聖地を読み込めませんでした"
        )

        st.caption(
            f"エラー種類：{type(error).__name__}"
        )


st.divider()
st.caption(
    "検索データ：Photon / © OpenStreetMap contributors"
)
