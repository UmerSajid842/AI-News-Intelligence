import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv("NEWS_API_URL", "http://localhost:8000/api/articles")
AUTH_URL = API_URL.replace("/api/articles", "/api/auth")
NEWS_MODE = os.getenv("NEWS_MODE", "demo").lower()

st.set_page_config(page_title="AI News Intelligence Platform", layout="wide")
st.title("AI News Intelligence Platform")
st.caption("A demo-first news ingestion, classification, and analytics workspace")


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


def sign_in(username: str, password: str):
    response = requests.post(
        f"{AUTH_URL}/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_news(token: str):
    response = requests.post(
        f"{API_URL}/fetch",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


with st.sidebar:
    st.header("Controls")
    st.caption(f"Current ingestion mode: `{NEWS_MODE}`")
    if NEWS_MODE == "demo":
        st.info("Demo mode uses deterministic local fixtures. It does not call a live news provider.")
    elif NEWS_MODE == "live":
        st.warning("Live mode requires NEWS_API_KEY, Celery, Redis, and a running worker.")
    else:
        st.error("Invalid NEWS_MODE. Use only 'demo' or 'live'.")

    st.subheader("Local demo sign-in")
    username = st.text_input("Username", value=os.getenv("DEMO_USER", ""))
    password = st.text_input("Password", type="password")
    if st.button("Sign in", use_container_width=True):
        try:
            st.session_state.token = sign_in(username, password)
            st.success("Signed in for protected actions.")
        except requests.RequestException as exc:
            st.error(f"Sign-in failed: {exc}")

    token = st.session_state.get("token")
    if token:
        st.success("Authenticated")
        if st.button("Fetch latest articles", use_container_width=True):
            with st.spinner("Loading and classifying articles..."):
                try:
                    result = fetch_news(token)
                    st.success(result.get("message", "Fetch completed."))
                    st.rerun()
                except requests.RequestException as exc:
                    st.error(f"Fetch failed: {exc}")
    else:
        st.caption("Sign in to run fetch or classification actions.")

try:
    articles = fetch_articles(limit=50)
except requests.RequestException as exc:
    st.error(f"Could not load articles from the API: {exc}")
    articles = []

if not articles:
    st.info("No articles yet. Sign in and use 'Fetch latest articles' to load the demo fixtures.")
    st.stop()


df = pd.DataFrame(articles)
if "published_at" in df.columns:
    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")

metrics = st.columns(5)
metrics[0].metric("Total Articles", len(df))
metrics[1].metric("Categories Detected", int(df["category"].nunique(dropna=True)))
metrics[2].metric("Latest Update", df["published_at"].max().strftime("%H:%M") if not df["published_at"].isna().all() else "N/A")
metrics[3].metric("Sources", int(df["source"].nunique(dropna=True)))
metrics[4].metric("Uncategorized", int(df["category"].isna().sum()))

st.subheader("Category Distribution")
category_counts = df["category"].dropna().value_counts()
if not category_counts.empty:
    st.bar_chart(category_counts)
else:
    st.info("No categories are available yet.")

st.subheader("Publication Timeline")
if "published_at" in df.columns and not df["published_at"].isna().all():
    timeline = df.set_index("published_at")["id"].resample("h").count()
    st.line_chart(timeline)

st.subheader("Intelligence Feed")
for _, row in df.iterrows():
    with st.container():
        st.markdown(f"### {row.get('title', 'Untitled article')}")
        if row.get("category"):
            st.markdown(f"**Category:** `{row['category']}`")
        st.caption(f"{row.get('source', 'Unknown')} | {format_published_at(row.get('published_at'))}")
        st.write(row.get("description") or "No description")
        if row.get("url"):
            st.link_button("Read source", row["url"])
        st.divider()

