import streamlit as st
from PIL import Image

st.set_page_config(page_title="Revive or Recycle", layout="centered")

st.title("Revive or Recycle")
st.write("Upload a photo of your device and we'll recommend whether to repair or recycle it.")
st.divider()

uploaded_file = st.file_uploader("Upload a photo of your device", type=["jpg", "jpeg", "png", "webp"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, use_container_width=True)

st.write("")

if st.button("Analyse Device", disabled=(uploaded_file is None)):

    with st.spinner("Analysing..."):

        # TODO: wire up to src.pipeline.run_pipeline
        import time
        time.sleep(1.5)

        result = {
            "device_type": "Cell Phone",
            "brand": "Samsung",
            "model": "Galaxy S21",
            "repair_cost_estimate": "$85",
            "verdict": "revive",
            "reason": "Repair cost is low relative to resale value. Worth fixing.",
        }

    st.divider()

    col1, col2 = st.columns(2)
    col1.metric("Device Type", result["device_type"])
    col2.metric("Brand / Model", f"{result['brand']} {result['model']}")

    st.metric("Estimated Repair Cost", result["repair_cost_estimate"])

    st.divider()

    if result["verdict"] == "revive":
        st.success(f"Revive It — {result['reason']}")
    else:
        st.info(f"Recycle It — {result['reason']}")
