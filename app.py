import streamlit as st

st.set_page_config(
    page_title="おしコンパス",
    page_icon="🧭"
)

st.markdown("""
<style>
div[data-baseweb="input"] > div {
    background-color: white !important;
    border: 2px solid #d9d9e3 !important;
    border-radius: 10px !important;
}

div[data-baseweb="input"] input {
    background-color: white !important;
}
</style>
""", unsafe_allow_html=True)

st.title("おしコンパス 🧭")
st.write("好きな場所は、あっち！")

st.divider()

st.subheader("聖地を探す")

place_name = st.text_input(
    "場所の名前",
    placeholder="例：東京タワー、東京駅、秋葉原"
)

if st.button("検索"):
    if place_name:
        st.write(f"検索する場所：{place_name}")
    else:
        st.warning("場所の名前を入力してください")
