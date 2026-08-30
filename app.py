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

st.set_page_config(page_title="おしコンパス", page_icon="🧭", layout="centered")


def render_html(markup):
    st.markdown(textwrap.dedent(markup).strip(), unsafe_allow_html=True)


@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


try:
    supabase = get_supabase()
    supabase.table("seichi").select("id").limit(1).execute()
    supabase_connected = True
except Exception:
    supabase = None
    supabase_connected = False


@st.cache_data(ttl=86400, show_spinner=False)
def geocode_place(place_name):
    params = urllib.parse.urlencode({"q": place_name, "limit": 1})
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
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def direction_name(bearing):
    names = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
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
    .stApp {{ background-color: {c['bg']}; }}
    .block-container {{ max-width: 820px; padding-top: 1.6rem; padding-bottom: 3rem; }}
    h1,h2,h3,p,div,label {{ color: {c['text']}; }}
    div[data-testid="stTextInput"] input {{
        background: {c['input']} !important;
        color: {c['text']} !important;
        border: 2px solid {c['input_border']} !important;
        border-radius: 16px !important;
    }}
    div[data-testid="stTextInput"] input::placeholder {{ color: {c['sub']} !important; }}
    .stButton > button {{
        background: {c['button']} !important;
        color: {c['button_text']} !important;
        border: 1px solid {c['button_border']} !important;
        border-radius: 16px !important;
        font-weight: 700 !important;
    }}
    .stButton > button:hover {{ border-color: {c['accent']} !important; color: {c['accent']} !important; }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {c['card']};
        border: 1px solid {c['card_border']} !important;
        border-radius: 22px !important;
    }}
    </style>
    """
)


ORIENTATION_HTML = """
<div class="sensor-card">
  <div class="sensor-title">📱 方位センサー</div>
  <div class="sensor-description">スマートフォンが向いている方角を確認します</div>
  <button class="sensor-start" data-role="start">方位センサーを開始</button>
  <div class="sensor-status" data-role="status">まだ開始していません</div>
  <div class="sensor-dial">
    <div class="north-label">N</div>
    <div class="sensor-needle" data-role="needle">
      <svg viewBox="0 0 100 100">
        <path d="M50 6 L78 40 H62 V90 H38 V40 H22 Z" fill="currentColor"></path>
      </svg>
    </div>
  </div>
  <div class="sensor-heading" data-role="heading">—°</div>
  <div class="sensor-source" data-role="source"></div>
</div>
"""

ORIENTATION_CSS = """
.sensor-card {
    width:100%; height:100%; box-sizing:border-box;
    background:var(--card); border:1px solid var(--border);
    border-radius:24px; padding:22px; text-align:center; color:var(--text);
}
.sensor-title { font-size:23px; font-weight:800; margin-bottom:4px; }
.sensor-description { font-size:14px; opacity:.75; margin-bottom:16px; }
.sensor-start {
    border:1px solid var(--border); background:var(--button-bg); color:var(--button-text);
    border-radius:14px; padding:11px 18px; font-size:15px; font-weight:700; cursor:pointer;
}
.sensor-start:disabled { opacity:.65; }
.sensor-status { min-height:24px; margin:13px 0 8px; font-size:14px; font-weight:700; }
.sensor-dial {
    width:170px; height:170px; position:relative; margin:8px auto;
    border-radius:50%; border:3px solid var(--border); background:var(--dial-bg);
}
.north-label { position:absolute; top:7px; left:0; right:0; font-weight:800; font-size:14px; }
.sensor-needle {
    position:absolute; width:106px; height:106px; left:32px; top:32px; color:var(--arrow);
    transform:rotate(0deg); transform-origin:50% 50%;
}
.sensor-needle svg { width:100%; height:100%; }
.sensor-heading { font-size:29px; font-weight:800; margin-top:8px; }
.sensor-source { margin-top:4px; font-size:12px; opacity:.72; }
"""

ORIENTATION_JS = r"""
export default function(component) {
  const { parentElement, data } = component;
  const q = (selector) => parentElement.querySelector(selector);
  const card = q(".sensor-card");
  const start = q('[data-role="start"]');
  const status = q('[data-role="status"]');
  const headingText = q('[data-role="heading"]');
  const source = q('[data-role="source"]');
  const needle = q('[data-role="needle"]');

  if (!card || !start || !status || !headingText || !needle) return;

  card.style.setProperty("--card", data.card_background);
  card.style.setProperty("--border", data.card_border);
  card.style.setProperty("--text", data.text_color);
  card.style.setProperty("--button-bg", data.button_background);
  card.style.setProperty("--button-text", data.button_text);
  card.style.setProperty("--dial-bg", data.compass_background);
  card.style.setProperty("--arrow", data.compass_arrow);

  let started = false;
  let gotEvent = false;
  let gotAbsolute = false;
  let timer = null;

  const norm = (value) => ((value % 360) + 360) % 360;
  const directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"];
  const direction = (value) => directions[Math.floor((value + 22.5) / 45) % 8];

  function extract(event) {
    if (typeof event.webkitCompassHeading === "number" && Number.isFinite(event.webkitCompassHeading)) {
      return { heading: norm(event.webkitCompassHeading), absolute: true };
    }

    if (typeof event.alpha !== "number" || !Number.isFinite(event.alpha)) return null;

    const absolute = event.absolute === true || event.type === "deviceorientationabsolute";
    return { heading: norm(360 - event.alpha), absolute };
  }

  function show(result) {
    if (!result) return;
    gotEvent = true;
    if (result.absolute) gotAbsolute = true;

    const heading = result.heading;
    needle.style.transform = `rotate(${heading}deg)`;
    headingText.textContent = `${direction(heading)} ${Math.round(heading)}°`;

    if (result.absolute) {
      status.textContent = "✅ 方位を取得しています";
      status.style.color = "#2F9B63";
      source.textContent = "絶対方位";
    } else if (!gotAbsolute) {
      status.textContent = "⚠️ 相対方位を取得中";
      status.style.color = "#C88724";
      source.textContent = "北基準ではない可能性があるため参考値です";
    }
  }

  const absoluteHandler = (event) => show(extract(event));
  const relativeHandler = (event) => { if (!gotAbsolute) show(extract(event)); };

  async function startSensor() {
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
      start.textContent = "方位センサー起動中";
      status.textContent = "センサーを待っています…";

      window.addEventListener("deviceorientationabsolute", absoluteHandler, true);
      window.addEventListener("deviceorientation", relativeHandler, true);

      timer = window.setTimeout(() => {
        if (!gotEvent) status.textContent = "方位情報を取得できません。スマートフォンで確認してください。";
      }, 5000);
    } catch (error) {
      status.textContent = "方位センサーを開始できませんでした";
    }
  }

  start.addEventListener("click", startSensor);

  return () => {
    window.removeEventListener("deviceorientationabsolute", absoluteHandler, true);
    window.removeEventListener("deviceorientation", relativeHandler, true);
    start.removeEventListener("click", startSensor);
    if (timer !== null) window.clearTimeout(timer);
  };
}
"""

try:
    orientation_component = st.components.v2.component(
        "oshi_compass_orientation_sensor",
        html=ORIENTATION_HTML,
        css=ORIENTATION_CSS,
        js=ORIENTATION_JS,
    )
except Exception:
    orientation_component = None


render_html(
    f"""
    <div style="background:{c['soft']};border:1px solid {c['line']};border-radius:24px;padding:24px;margin-bottom:18px;">
        <div style="font-size:48px;font-weight:800;color:{c['text']};">おしコンパス 🧭</div>
        <div style="margin-top:8px;font-size:24px;font-weight:700;color:{c['accent']};">好きな場所は、あっち！</div>
    </div>
    """
)

if not supabase_connected:
    st.error("データベースに接続できませんでした")


if st.session_state.selected_seichi:
    selected_name = html.escape(str(st.session_state.selected_seichi["name"]))
    render_html(
        f"""
        <div style="background:{c['selected']};border:1px solid {c['line']};border-radius:18px;padding:14px 18px;margin-bottom:16px;font-size:20px;font-weight:700;color:{c['text']};">
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
    st.success("📍 現在地を取得できました")
else:
    st.info("現在地を取得してください")


if st.session_state.current_location and st.session_state.selected_seichi:
    current = st.session_state.current_location
    destination = st.session_state.selected_seichi

    bearing = calculate_bearing(
        current["latitude"],
        current["longitude"],
        destination["latitude"],
        destination["longitude"],
    )

    safe_name = html.escape(str(destination["name"]))

    arrow_svg = (
        f'<svg viewBox="0 0 100 100" style="width:145px;height:145px;transform:rotate({bearing:.2f}deg);transform-origin:50% 50%;">'
        f'<path d="M50 6 L78 40 H62 V90 H38 V40 H22 Z" fill="{c["arrow"]}"></path>'
        f'</svg>'
    )

    compass_html = (
        f'<div style="background:{c["card"]};border:1px solid {c["card_border"]};border-radius:28px;padding:30px 18px;margin:24px 0;text-align:center;">'
        f'<div style="display:inline-block;background:{c["badge"]};border:1px solid {c["line"]};border-radius:999px;padding:8px 16px;font-size:16px;font-weight:700;color:{c["accent"]};margin-bottom:18px;">おしの方向</div>'
        f'<div style="font-size:28px;font-weight:800;color:{c["text"]};margin-bottom:20px;">{safe_name}はこっち！</div>'
        f'<div style="width:230px;height:230px;margin:0 auto;border-radius:50%;background:{c["dial"]};border:4px solid {c["dial_border"]};display:flex;justify-content:center;align-items:center;">{arrow_svg}</div>'
        f'<div style="font-size:34px;font-weight:800;color:{c["text"]};margin-top:22px;">{direction_name(bearing)}　{round(bearing)}°</div>'
        f'</div>'
    )

    render_html(compass_html)


st.divider()
st.subheader("STEP 12　スマートフォンの向き")
st.caption("Androidでは画面を縦向きにして、スマートフォンを水平に持って試してください。")

if orientation_component is not None:
    orientation_component(
        key="orientation_sensor",
        data={
            "card_background": c["card"],
            "card_border": c["card_border"],
            "text_color": c["text"],
            "button_background": c["button"],
            "button_text": c["button_text"],
            "compass_background": c["dial"],
            "compass_arrow": c["arrow"],
        },
        width="stretch",
        height=390,
    )
else:
    st.warning("方位センサー用Componentを読み込めませんでした。")


st.divider()
st.subheader("聖地を探す")
st.markdown("**🔎 行きたい場所・好きな場所を入力**")

place_name = st.text_input(
    "場所を入力",
    placeholder="ここに入力　例：東京タワー、東京駅、秋葉原",
    label_visibility="collapsed",
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
            except urllib.error.HTTPError as error:
                st.session_state.search_result = None
                st.error(f"検索サービスとの通信エラー（HTTP {error.code}）")
            except Exception:
                st.session_state.search_result = None
                st.error("場所を検索できませんでした")


result = st.session_state.search_result

if result:
    geometry = result.get("geometry", {})
    properties = result.get("properties", {})
    coordinates = geometry.get("coordinates", [])

    if len(coordinates) >= 2:
        longitude = float(coordinates[0])
        latitude = float(coordinates[1])
        result_name = properties.get("name", st.session_state.searched_name)

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
        st.subheader("検索結果")

        with st.container(border=True):
            st.success(f"「{st.session_state.searched_name}」を見つけました")
            st.markdown(f"### 📍 {st.session_state.searched_name}")
            st.caption(" / ".join(place_parts))

            if supabase_connected and st.button(
                "♡ 聖地に登録",
                type="primary",
                key="register_button",
            ):
                try:
                    save_name = st.session_state.searched_name

                    existing = (
                        supabase.table("seichi")
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
                            supabase.table("seichi")
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
                except Exception as error:
                    st.error("聖地を登録できませんでした")
                    st.caption(f"エラー種類：{type(error).__name__}")


st.divider()
st.subheader("♡ お気に入りの聖地")

if supabase_connected:
    try:
        response = (
            supabase.table("seichi")
            .select("id,name,latitude,longitude,created_at")
            .order("created_at", desc=True)
            .execute()
        )

        if not response.data:
            st.write("まだ聖地が登録されていません。")
        else:
            for seichi in response.data:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(f"### ♡ {seichi['name']}")

                    with col2:
                        selected_now = bool(
                            st.session_state.selected_seichi
                            and st.session_state.selected_seichi.get("id") == seichi["id"]
                        )

                        if st.button(
                            "選択中" if selected_now else "選ぶ",
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
        st.error("登録済みの聖地を読み込めませんでした")
        st.caption(f"エラー種類：{type(error).__name__}")


st.divider()
st.caption("検索データ：Photon / © OpenStreetMap contributors")
