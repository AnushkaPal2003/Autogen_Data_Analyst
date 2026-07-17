import requests
import streamlit as st

# Read backend URL from Streamlit Secrets
BACKEND_URL = st.secrets.get(
    "BACKEND_URL",
    "https://autogen-data-analyst-1.onrender.com"
)

st.set_page_config(page_title="AutoGen Data Analyst", page_icon="📊", layout="centered")

st.title("📊 AutoGen Data Analyst")
st.caption(
    "Upload a CSV, ask a question in plain English. "
    "A data-analyst agent writes and runs pandas/matplotlib code, "
    "and a reviewer agent checks the result."
)

# Debug (remove after everything works)
st.sidebar.write("Backend:", BACKEND_URL)

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

question = st.text_area(
    "What do you want to know about this data?",
    placeholder="e.g. Which product category has the highest average revenue?",
)

if st.button("Analyze", type="primary"):

    if uploaded_file is None:
        st.warning("Please upload a CSV.")
        st.stop()

    if not question.strip():
        st.warning("Please enter a question.")
        st.stop()

    with st.spinner("Agents are writing and running the analysis..."):

        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "text/csv",
            )
        }

        data = {
            "question": question
        }

        try:

            response = requests.post(
                f"{BACKEND_URL}/analyze",
                files=files,
                data=data,
                timeout=300,
            )

            # Debug
            st.sidebar.write("Status Code:", response.status_code)

            if response.status_code != 200:
                st.error(response.text)
                st.stop()

            result = response.json()

            st.subheader("Summary")
            st.write(result.get("summary", "No summary returned."))

            if result.get("chart_url"):
                chart = requests.get(
                    f"{BACKEND_URL}{result['chart_url']}"
                )
                if chart.ok:
                    st.image(chart.content)

            if result.get("approved"):
                st.success("✅ Reviewer approved the analysis.")
            else:
                st.warning(result.get("review_feedback", "Reviewer did not approve."))

        except Exception as e:
            st.exception(e)
