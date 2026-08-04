import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv("NEWS_API_URL", "http://localhost:8000/api/articles")


st.set_page_config(page_title="AI News Intelligence Platform", layout="wide", page_icon="🧠")
st.title("🧠 AI News Intelligence Platform")
st.caption("Real-time news with an AI-assisted categorization pipeline")


def format_published_at(value):
    if not value:
        return "Unknown"
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return value[:10]
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def fetch_articles(limit: int = 50):
    response = requests.get(f"{API_URL}/", params={"limit": limit}, timeout=10)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


def fetch_news():
    response = requests.post(f"{API_URL}/fetch", timeout=30)
    response.raise_for_status()
    return response.json()


with st.sidebar:
    st.title("📊 Analytics")
    st.markdown("---")
    st.info("Use the button below to queue a real NewsAPI fetch and let the worker classify items in the background.")

    if st.button("🔄 Fetch Latest News", use_container_width=True):
        with st.spinner("Fetching and processing in the background..."):
            try:
                result = fetch_news()
                st.success(result.get("message", "News fetch queued successfully."))
            except requests.RequestException as exc:
                st.error(f"Failed to start fetch: {exc}")

try:
    articles = fetch_articles(limit=50)
except requests.RequestException as exc:
    st.error(f"Could not load articles: {exc}")
    articles = []

if not articles:
    st.info("No articles yet. Click 'Fetch Latest News' to start the background intelligence pipeline.")
    st.stop()


df = pd.DataFrame(articles)
if "published_at" in df.columns:
    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")

st.markdown("---")
metrics = st.columns(5)
metrics[0].metric("Total Articles", len(df))
metrics[1].metric("Categories Detected", int(df["category"].nunique(dropna=True)))
metrics[2].metric("Latest Update", df["published_at"].max().strftime("%H:%M") if not df["published_at"].isna().all() else "N/A")
metrics[3].metric("Sources", int(df["source"].nunique(dropna=True)))
metrics[4].metric("Uncategorized", int(df["category"].isna().sum()))

st.markdown("---")
st.subheader("📈 Category Distribution")
category_counts = df["category"].dropna().value_counts()
if not category_counts.empty:
    st.bar_chart(category_counts)
else:
    st.info("Run the classifier to populate article categories.")

st.subheader("📅 Timeline")
if "published_at" in df.columns and not df["published_at"].isna().all():
    timeline = df.set_index("published_at")["id"].resample("H").count()
    st.line_chart(timeline)

st.markdown("---")
st.subheader("📰 Intelligence Feed")
for _, row in df.iterrows():
    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"### {row['title']}")
            if row.get("category"):
                st.markdown(f"**🏷️ Category:** `{row['category']}`")
            st.caption(
                f"📰 {row.get('source', 'Unknown')} | 🕒 {format_published_at(row.get('published_at'))}"
            )
            st.write(row.get("description") or "No description")
        with col2:
            if row.get("category"):
                st.markdown(
                    f"<div style='background-color:#4CAF50;padding:8px;border-radius:8px;text-align:center;color:white;'>{row['category']}</div>",
                    unsafe_allow_html=True,
                )
            if row.get("url"):
                st.link_button("🔗 Read", row["url"])
        st.divider()

