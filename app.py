import streamlit as st
import urllib.parse
import urllib.request
import urllib.error
import json
import math
import html

from supabase import create_client
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(page_title="おしコンパス", page_icon="🧭", layout="centered")


# Supabase
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


# 場所検索
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


# 現在地 → 目的地の方位角
# 北0 / 東90 / 南180 / 西270
def calculate_bearing(
    lat1_deg,
    lon1_deg,
    lat2_deg,
    lon2_deg,
):
    lat1 = math.radians(lat1_deg)
    lat2 = math.radians(lat2_deg)

    dlon = math.radians(
        lon2_deg - lon1_deg
    )

    x = math.sin(dlon) * math.cos(lat2)

    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1)
        * math.cos(lat2)
        * math.cos(dlon)
    )

    return (
        math.degrees(
            math.atan2(x, y)
        )
        + 360
    ) % 360


def get_direction_name(bearing):

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

    return names[
        int((bearing + 22.5) // 45) % 8
    ]


# 状態
for key, default in {
    "search_result": None,
    "searched_name": "",
    "selected_seichi": None,
    "current_location": None,
}.items():

    if key not in st.session_state:
        st.session_state[key] = default


# 夜モード
night_mode = st.toggle("🌙 夜モード")


if night_mode:

    colors = {
        "bg": "#12182B",
        "text": "#F5F7FF",
        "subtext": "#C6CDEA",
        "accent": "#FF8FB1",
        "accent_soft": "#2B3557",
        "accent_line": "#43507B",
        "input_bg": "#1D2742",
        "input_border": "#7081B0",
        "button_bg": "#294669",
        "button_border": "#6F93BF",
        "button_text": "#FFFFFF",
        "card_bg": "#18213A",
        "card_border": "#35466F",
        "compass_bg": "#202B49",
        "compass_border": "#7385B8",
        "arrow": "#FFB3C8",
        "badge_bg": "#2A3557",
        "selected_bg": "#243150",
    }

else:

    colors = {
        "bg": "#FFFAFC",
        "text": "#22304A",
        "subtext": "#6E7890",
        "accent": "#EF7DA0",
        "accent_soft": "#FFF0F5",
        "accent_line": "#F3C8D6",
        "input_bg": "#FFFFFF",
        "input_border": "#AAB4C8",
        "button_bg": "#FFFFFF",
        "button_border": "#D7BFD0",
        "button_text": "#22304A",
        "card_bg": "#FFFFFF",
        "card_border": "#EFD8E2",
        "compass_bg": "#FFF7FB",
        "compass_border": "#E9CCD7",
        "arrow": "#EF7DA0",
        "badge_bg": "#FFF0F5",
        "selected_bg": "#EEF5FF",
    }


st.markdown(
    f"""
    <style>

    .stApp {{
        background-color:{colors["bg"]};
    }}

    .block-container {{
        max-width:820px;
        padding-top:1.6rem;
        padding-bottom:3rem;
    }}

    h1,h2,h3,p,div,label {{
        color:{colors["text"]};
    }}

    div[data-testid="stTextInput"] input {{
        background:{colors["input_bg"]} !important;
        color:{colors["text"]} !important;
        border:2px solid {colors["input_border"]} !important;
        border-radius:16px !important;
        padding:.75rem .9rem !important;
    }}

    div[data-testid="stTextInput"] input::placeholder {{
        color:{colors["subtext"]} !important;
    }}

    .stButton > button {{
        background:{colors["button_bg"]} !important;
        color:{colors["button_text"]} !important;
        border:1px solid {colors["button_border"]} !important;
        border-radius:16px !important;
        font-weight:700 !important;
    }}

    .stButton > button:hover {{
        border-color:{colors["accent"]} !important;
        color:{colors["accent"]} !important;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background:{colors["card_bg"]};
        border:1px solid {colors["card_border"]} !important;
        border-radius:22px !important;
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# STEP 12 方位センサー

ORIENTATION_HTML = """
<div class="sensor-card">

  <div class="sensor-title">
    📱 方位センサー
  </div>

  <div class="sensor-description">
    スマートフォンが向いている方角を確認します
  </div>

  <button
    class="sensor-start"
    data-role="start"
  >
    方位センサーを開始
  </button>

  <div
    class="sensor-status"
    data-role="status"
  >
    まだ開始していません
  </div>

  <div class="sensor-dial">

    <div class="north-label">
      N
    </div>

    <div
      class="sensor-needle"
      data-role="needle"
    >

      <svg viewBox="0 0 100 100">

        <path
          d="M50 6 L78 40 H62 V90 H38 V40 H22 Z"
          fill="currentColor"
        />

      </svg>

    </div>

  </div>

  <div
    class="sensor-heading"
    data-role="heading"
  >
    —°
  </div>

  <div
    class="sensor-source"
    data-role="source"
  ></div>

</div>
"""


ORIENTATION_CSS = """
.sensor-card {
    width:100%;
    height:100%;
    box-sizing:border-box;
    background:var(--card);
    border:1px solid var(--border);
    border-radius:24px;
    padding:22px;
    text-align:center;
    color:var(--text);
}

.sensor-title {
    font-size:23px;
    font-weight:800;
    margin-bottom:4px;
}

.sensor-description {
    font-size:14px;
    opacity:.75;
    margin-bottom:16px;
}

.sensor-start {
    border:1px solid var(--border);
    background:var(--button-bg);
    color:var(--button-text);
    border-radius:14px;
    padding:11px 18px;
    font-size:15px;
    font-weight:700;
    cursor:pointer;
}

.sensor-start:disabled {
    opacity:.65;
    cursor:default;
}

.sensor-status {
    min-height:24px;
    margin:13px 0 8px;
    font-size:14px;
    font-weight:700;
}

.sensor-dial {
    width:170px;
    height:170px;
    position:relative;
    margin:8px auto;
    border-radius:50%;
    border:3px solid var(--border);
    background:var(--dial-bg);
}

.north-label {
    position:absolute;
    top:7px;
    left:0;
    right:0;
    font-weight:800;
    font-size:14px;
}

.sensor-needle {
    position:absolute;
    width:106px;
    height:106px;
    left:32px;
    top:32px;
    color:var(--arrow);
    transform:rotate(0deg);
    transform-origin:50% 50%;
}

.sensor-needle svg {
    width:100%;
    height:100%;
}

.sensor-heading {
    font-size:29px;
    font-weight:800;
    margin-top:8px;
}

.sensor-source {
    margin-top:4px;
    font-size:12px;
    opacity:.72;
}
"""


ORIENTATION_JS = r"""
export default function({
    parentElement,
    data
}) {

  const card =
    parentElement.querySelector(
      ".sensor-card"
    );

  const start =
    parentElement.querySelector(
      '[data-role="start"]'
    );

  const status =
    parentElement.querySelector(
      '[data-role="status"]'
    );

  const headingText =
    parentElement.querySelector(
      '[data-role="heading"]'
    );

  const source =
    parentElement.querySelector(
      '[data-role="source"]'
    );

  const needle =
    parentElement.querySelector(
      '[data-role="needle"]'
    );


  if (
    !card ||
    !start ||
    !status ||
    !headingText ||
    !needle
  ) {
    return;
  }


  card.style.setProperty(
    "--card",
    data.card_background
  );

  card.style.setProperty(
    "--border",
    data.card_border
  );

  card.style.setProperty(
    "--text",
    data.text_color
  );

  card.style.setProperty(
    "--button-bg",
    data.button_background
  );

  card.style.setProperty(
    "--button-text",
    data.button_text
  );

  card.style.setProperty(
    "--dial-bg",
    data.compass_background
  );

  card.style.setProperty(
    "--arrow",
    data.compass_arrow
  );


  let started = false;
  let gotEvent = false;
  let gotAbsolute = false;
  let timer = null;


  const norm = value =>
    (
      (value % 360)
      + 360
    ) % 360;


  function direction(value) {

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

    return directions[
      Math.floor(
        (value + 22.5) / 45
      ) % 8
    ];
  }


  function headingFromAngles(
    alpha,
    beta,
    gamma
  ) {

    const safeBeta =
      beta ?? 0;

    const safeGamma =
      gamma ?? 0;


    if (
      Math.abs(safeBeta) < 0.001
      &&
      Math.abs(safeGamma) < 0.001
    ) {

      return norm(
        360 - alpha
      );
    }


    const r =
      Math.PI / 180;

    const x =
      safeBeta * r;

    const y =
      safeGamma * r;

    const z =
      alpha * r;


    const cX = Math.cos(x);
    const cY = Math.cos(y);
    const cZ = Math.cos(z);

    const sX = Math.sin(x);
    const sY = Math.sin(y);
    const sZ = Math.sin(z);


    const Vx =
      -cZ * sY
      -sZ * sX * cY;

    const Vy =
      -sZ * sY
      +cZ * sX * cY;


    return norm(
      Math.atan2(
        Vx,
        Vy
      )
      * 180
      / Math.PI
    );
  }


  function extract(event) {

    if (
      typeof event.webkitCompassHeading
        === "number"
      &&
      Number.isFinite(
        event.webkitCompassHeading
      )
    ) {

      return {
        heading:
          norm(
            event.webkitCompassHeading
          ),

        absolute:true
      };
    }


    if (
      typeof event.alpha
        !== "number"
      ||
      !Number.isFinite(
        event.alpha
      )
    ) {

      return null;
    }


    const absolute =
      event.absolute === true
      ||
      event.type ===
        "deviceorientationabsolute";


    const heading =
      absolute
      ?
      headingFromAngles(
        event.alpha,
        event.beta,
        event.gamma
      )
      :
      norm(
        360 - event.alpha
      );


    return {
      heading,
      absolute
    };
  }


  function show(result) {

    if (!result) {
      return;
    }


    gotEvent = true;


    if (result.absolute) {
      gotAbsolute = true;
    }


    const heading =
      result.heading;


    needle.style.transform =
      `rotate(${heading}deg)`;


    headingText.textContent =
      `${direction(heading)} ${Math.round(heading)}°`;


    if (result.absolute) {

      status.textContent =
        "✅ 方位を取得しています";

      status.style.color =
        "#2F9B63";

      source.textContent =
        "地磁気を使った絶対方位";

    }

    else if (!gotAbsolute) {

      status.textContent =
        "⚠️ 相対方位を取得中";

      status.style.color =
        "#C88724";

      source.textContent =
        "北基準ではない可能性があるため参考値です";
    }
  }


  const absoluteHandler =
    event =>
      show(
        extract(event)
      );


  const relativeHandler =
    event => {

      if (!gotAbsolute) {

        show(
          extract(event)
        );
      }
    };


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
      typeof DeviceOrientationEvent
        === "undefined"
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

        catch (error) {

          permission =
            await DeviceOrientationEvent
              .requestPermission();
        }


        if (
          permission !== "granted"
        ) {

          status.textContent =
            "方位センサーの利用が許可されませんでした";

          return;
        }
      }


      started = true;

      start.disabled = true;

      start.textContent =
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
        relativeHandler,
        true
      );


      timer =
        window.setTimeout(
          () => {

            if (!gotEvent) {

              status.textContent =
                "方位情報を取得できません。スマートフォンで確認してください。";
            }

          },
          5000
        );

    }

    catch (error) {

      status.textContent =
        "方位センサーを開始できませんでした";
    }
  }


  start.addEventListener(
    "click",
    startSensor
  );


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
      startSensor
    );


    if (timer !== null) {

      window.clearTimeout(
        timer
      );
    }
  };
}
"""


try:

    orientation_component =
        st.components.v2.component(
            name="oshi_compass_orientation_sensor",
            html=ORIENTATION_HTML,
            css=ORIENTATION_CSS,
            js=ORIENTATION_JS,
        )

except Exception:

    orientation_component = None


# タイトル
st.markdown(
    f"""
    <div style="
        background:{colors["accent_soft"]};
        border:1px solid {colors["accent_line"]};
        border-radius:24px;
        padding:24px;
        margin-bottom:18px
    ">

      <div style="
          font-size:48px;
          font-weight:800;
          color:{colors["text"]}
      ">
        おしコンパス 🧭
      </div>

      <div style="
          margin-top:8px;
          font-size:24px;
          font-weight:700;
          color:{colors["accent"]}
      ">
        好きな場所は、あっち！
      </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# 接続OK表示は出さない
if not supabase_connected:

    st.error(
        "データベースに接続できませんでした"
    )


# 現在の目的地
if st.session_state.selected_seichi:

    selected_name =
        html.escape(
            str(
                st.session_state
                .selected_seichi["name"]
            )
        )


    st.markdown(
        f"""
        <div style="
            background:{colors["selected_bg"]};
            border:1px solid {colors["accent_line"]};
            border-radius:18px;
            padding:14px 18px;
            margin-bottom:16px;
            font-size:20px;
            font-weight:700;
            color:{colors["text"]}
        ">
          🧭 現在の目的地：{selected_name}
        </div>
        """,
        unsafe_allow_html=True,
    )


# 現在地
st.divider()

st.subheader(
    "📍 現在地"
)


location =
    streamlit_geolocation()


if (
    isinstance(
        location,
        dict
    )
    and
    location.get(
        "latitude"
    ) is not None
    and
    location.get(
        "longitude"
    ) is not None
):

    st.session_state.current_location = {

        "latitude":
            float(
                location["latitude"]
            ),

        "longitude":
            float(
                location["longitude"]
            ),

        "accuracy":
            location.get(
                "accuracy"
            ),
    }


if st.session_state.current_location:

    st.success(
        "📍 現在地を取得できました"
    )

else:

    st.info(
        "現在地を取得してください"
    )


# 目的地の方角
if (
    st.session_state.current_location
    and
    st.session_state.selected_seichi
):

    current =
        st.session_state.current_location

    destination =
        st.session_state.selected_seichi


    bearing =
        calculate_bearing(
            current["latitude"],
            current["longitude"],
            destination["latitude"],
            destination["longitude"],
        )


    direction_name =
        get_direction_name(
            bearing
        )


    bearing_display =
        round(
            bearing
        )


    safe_name =
        html.escape(
            str(
                destination["name"]
            )
        )


    # このSVGは最初から真上向き
    # 0°=北 / 90°=東

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
        f'fill="{colors["arrow"]}"'
        f'/>'

        f'</svg>'
    )


    compass_html = (

        f'<div style="'
        f'background:{colors["card_bg"]};'
        f'border:1px solid {colors["card_border"]};'
        f'border-radius:28px;'
        f'padding:30px 18px;'
        f'margin:24px 0;'
        f'text-align:center;'
        f'">'

        f'<div style="'
        f'display:inline-block;'
        f'background:{colors["badge_bg"]};'
        f'border:1px solid {colors["accent_line"]};'
        f'border-radius:999px;'
        f'padding:8px 16px;'
        f'font-size:16px;'
        f'font-weight:700;'
        f'color:{colors["accent"]};'
        f'margin-bottom:18px;'
        f'">'
        f'おしの方向'
        f'</div>'

        f'<div style="'
        f'font-size:28px;'
        f'font-weight:800;'
        f'color:{colors["text"]};'
        f'margin-bottom:20px;'
        f'">'
        f'{safe_name}はこっち！'
        f'</div>'

        f'<div style="'
        f'width:230px;'
        f'height:230px;'
        f'margin:0 auto;'
        f'border-radius:50%;'
        f'background:{colors["compass_bg"]};'
        f'border:4px solid {colors["compass_border"]};'
        f'display:flex;'
        f'justify-content:center;'
        f'align-items:center;'
        f'">'
        f'{arrow_svg}'
        f'</div>'

        f'<div style="'
        f'font-size:34px;'
        f'font-weight:800;'
        f'color:{colors["text"]};'
        f'margin-top:22px;'
        f'">'
        f'{direction_name}　{bearing_display}°'
        f'</div>'

        f'</div>'
    )


    st.markdown(
        compass_html,
        unsafe_allow_html=True,
    )


# STEP 12
st.divider()

st.subheader(
    "STEP 12　スマートフォンの向き"
)


st.caption(
    "Androidでは画面を縦向きにし、スマホを水平に持って、画面を上向きにして試してください。"
)


if orientation_component is not None:

    orientation_component(

        key="orientation_sensor",

        data={

            "card_background":
                colors["card_bg"],

            "card_border":
                colors["card_border"],

            "text_color":
                colors["text"],

            "button_background":
                colors["button_bg"],

            "button_text":
                colors["button_text"],

            "compass_background":
                colors["compass_bg"],

            "compass_arrow":
                colors["arrow"],
        },

        width="stretch",

        height=390,
    )


else:

    st.warning(
        "方位センサー用Componentを読み込めませんでした。"
    )


# 聖地検索
st.divider()

st.subheader(
    "聖地を探す"
)


st.markdown(
    "**🔎 行きたい場所・好きな場所を入力**"
)


place_name =
    st.text_input(
        "場所を入力",
        placeholder=
            "ここに入力　例：東京タワー、東京駅、秋葉原",
        label_visibility="collapsed",
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


# 検索結果
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
            float(
                coordinates[0]
            )


        latitude =
            float(
                coordinates[1]
            )


        result_name =
            properties.get(
                "name",
                st.session_state.searched_name,
            )


        place_parts = [

            part

            for part in [

                result_name,

                properties.get(
                    "district",
                    ""
                ),

                properties.get(
                    "city",
                    ""
                ),

                properties.get(
                    "state",
                    ""
                ),

                properties.get(
                    "country",
                    ""
                ),
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
                and
                st.button(
                    "♡ 聖地に登録",
                    type="primary",
                    key="register_button",
                )
            ):

                try:

                    save_name =
                        st.session_state.searched_name


                    existing = (

                        supabase
                        .table(
                            "seichi"
                        )
                        .select(
                            "id"
                        )
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
                        .limit(
                            1
                        )
                        .execute()
                    )


                    if existing.data:

                        st.info(
                            "この聖地はすでに登録されています ♡"
                        )


                    else:

                        (
                            supabase
                            .table(
                                "seichi"
                            )
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
                            f"♡ 「{save_name}」を聖地に登録しました"
                        )


                except Exception as error:

                    st.error(
                        "聖地を登録できませんでした"
                    )


                    st.caption(
                        f"エラー種類："
                        f"{type(error).__name__}"
                    )


# お気に入り
st.divider()

st.subheader(
    "♡ お気に入りの聖地"
)


if supabase_connected:

    try:

        response = (

            supabase
            .table(
                "seichi"
            )
            .select(
                "id,name,latitude,longitude,created_at"
            )
            .order(
                "created_at",
                desc=True
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

                    col1, col2 =
                        st.columns(
                            [3, 1]
                        )


                    with col1:

                        st.markdown(
                            f"### ♡ {seichi['name']}"
                        )


                    with col2:

                        selected_now =
                            bool(
                                st.session_state.selected_seichi
                                and
                                st.session_state.selected_seichi.get(
                                    "id"
                                )
                                ==
                                seichi["id"]
                            )


                        if st.button(

                            "選択中"
                            if selected_now
                            else "選ぶ",

                            key=
                                f"select_{seichi['id']}",

                            use_container_width=True,

                            disabled=
                                selected_now,
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


    except Exception as error:

        st.error(
            "登録済みの聖地を読み込めませんでした"
        )


        st.caption(
            f"エラー種類："
            f"{type(error).__name__}"
        )


st.divider()

st.caption(
    "検索データ：Photon / © OpenStreetMap contributors"
)
