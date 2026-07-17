import os
import requests
import streamlit as st

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AutoGen Data Analyst", page_icon="📊", layout="centered")

st.title("📊 AutoGen Data Analyst")
st.caption(
    "Upload a CSV, ask a question in plain English. A data-analyst agent writes "
    "and runs pandas/matplotlib code, and a reviewer agent checks the result."
)

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
question = st.text_area(
    "What do you want to know about this data?",
    placeholder="e.g. Which product category has the highest average revenue?",
)

if st.button("Analyze", type="primary"):
    if not uploaded_file or not question.strip():
        st.warning("Please upload a CSV and enter a question.")
    else:
        with st.spinner("Agents are writing and running the analysis..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                data = {"question": question}
                response = requests.post(f"{BACKEND_URL}/analyze", files=files, data=data, timeout=180)
                response.raise_for_status()
                result = response.json()

                st.subheader("Summary")
                st.write(result["summary"])

                if result.get("chart_url"):
                    chart_response = requests.get(f"{BACKEND_URL}{result['chart_url']}", timeout=30)
                    if chart_response.ok:
                        st.image(chart_response.content, caption="Generated chart")

                if result["approved"]:
                    st.success("Reviewer approved this analysis.")
                else:
                    st.warning(f"Reviewer feedback: {result['review_feedback']}")

            except requests.exceptions.HTTPError as exc:
                try:
                    detail = exc.response.json().get("detail", exc.response.text)
                except ValueError:
                    detail = exc.response.text
                st.error(f"Backend error: {detail}")
            except requests.exceptions.RequestException as exc:
                st.error(f"Could not reach backend: {exc}")
