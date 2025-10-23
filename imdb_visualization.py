# imdb_visualization.py
"""
IMDb 2024 - Interactive SQL Query & Visualization Dashboard
- Uses environment variables / Streamlit secrets for DB credentials.
- Falls back to a relative CSV file in data/ when DB is unavailable.
- Clean, safe numeric conversions and UI filters.
"""

import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# ---------------- Config ----------------
st.set_page_config(page_title="IMDb 2024 - Data Visualization", layout="wide")
TABLE_NAME = os.getenv("IMDB_TABLE", "movies_2024")
CSV_FALLBACK = os.path.join("data", "movies_2024_detailed.csv")

# DB credentials from environment variables (or Streamlit secrets)
DB_USER = os.getenv("IMDB_DB_USER")
DB_PASS = os.getenv("IMDB_DB_PASS")
DB_HOST = os.getenv("IMDB_DB_HOST", "localhost")
DB_PORT = os.getenv("IMDB_DB_PORT", "3306")
DB_NAME = os.getenv("IMDB_DB_NAME")

# Helper: try to build SQLAlchemy engine string if credentials available
def get_engine():
    if DB_USER and DB_PASS and DB_HOST and DB_NAME:
        conn_str = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        return create_engine(conn_str, pool_pre_ping=True)
    return None

# ---------- Load data (DB preferred, CSV fallback) ----------
@st.cache_data
def load_data():
    engine = get_engine()
    if engine is not None:
        try:
            df = pd.read_sql(text(f"SELECT * FROM {TABLE_NAME}"), engine)
            st.info("Loaded data from SQL database.")
            return df
        except SQLAlchemyError as e:
            st.warning(f"Database read failed: {e}. Falling back to CSV.")
    # CSV fallback (relative path)
    if not os.path.exists(CSV_FALLBACK):
        st.error(f"CSV fallback not found at: {CSV_FALLBACK}")
        return pd.DataFrame()
    df = pd.read_csv(CSV_FALLBACK, encoding="utf-8", on_bad_lines="skip")
    st.info("Loaded data from CSV fallback.")
    return df

df = load_data()

# If no data, stop
if df.empty:
    st.error("No data available to display. Ensure CSV is present or DB credentials are configured.")
    st.stop()

# ---------- Data cleaning (safe numeric conversions) ----------
# rating -> float
df["rating"] = pd.to_numeric(df["rating"].astype(str).str.strip().replace({"": None, "N/A": None}), errors="coerce")

# votes -> numeric (handle K/M)
def votes_to_int(v):
    if pd.isna(v):
        return 0
    s = str(v).replace(",", "").strip()
    try:
        if s.endswith("K") or s.endswith("k"):
            return int(float(s[:-1]) * 1000)
        if s.endswith("M") or s.endswith("m"):
            return int(float(s[:-1]) * 1_000_000)
        return int(float(s))
    except:
        # remove non-digits then try
        digits = "".join(ch for ch in s if ch.isdigit())
        return int(digits) if digits else 0

df["votes_num"] = df.get("votes", "").apply(votes_to_int)

# duration to minutes if possible (store in duration_min)
def duration_to_minutes(s):
    if pd.isna(s):
        return None
    s = str(s)
    hrs = 0
    mins = 0
    try:
        if "h" in s:
            import re
            m = re.search(r"(\d+)\s*h", s)
            if m:
                hrs = int(m.group(1))
        if "m" in s:
            import re
            m2 = re.search(r"(\d+)\s*m", s)
            if m2:
                mins = int(m2.group(1))
        total = hrs * 60 + mins
        return total if total > 0 else None
    except:
        return None

df["duration_min"] = df.get("duration", "").apply(duration_to_minutes)

# ---------- UI ----------
st.title("IMDb 2024 — Movie Analytics Dashboard")
st.markdown("Explore IMDb 2024 data. Use SQL (if configured) or the CSV fallback. Use filters to refine results.")

st.markdown("---")
# SQL Query panel
st.subheader("Run SQL Query (optional)")
default_query = f"SELECT * FROM {TABLE_NAME} LIMIT 50;"
query_text = st.text_area("SQL query (only if DB configured):", default_query, height=120)
run_query = st.button("Execute SQL Query")

if run_query:
    engine = get_engine()
    if engine is None:
        st.error("No DB credentials configured. Set environment variables or use Streamlit secrets.")
    else:
        try:
            with engine.connect() as conn:
                res = pd.read_sql(text(query_text), conn)
            st.success("Query executed. Showing results:")
            st.dataframe(res, use_container_width=True)
        except Exception as e:
            st.error(f"Query execution failed: {e}")

st.markdown("---")
# Filters
st.subheader("Filter & Visualize")
col1, col2, col3, col4 = st.columns(4)

with col1:
    all_genres = sorted([g for g in df["genre"].dropna().unique()]) if "genre" in df.columns else []
    genre_choice = st.selectbox("Genre", ["All"] + all_genres)

with col2:
    min_rating = st.slider("Minimum rating", 0.0, 10.0, 6.0, 0.1)

with col3:
    min_votes = st.number_input("Minimum votes", min_value=0, value=0, step=100)

with col4:
    duration_choice = st.selectbox("Duration", ["All", "< 2 hrs", "2-3 hrs", "> 3 hrs"])

# Apply filters
filtered = df.copy()
if genre_choice != "All":
    filtered = filtered[filtered["genre"].fillna("").str.contains(genre_choice, case=False, na=False)]
filtered = filtered[filtered["rating"].fillna(0) >= float(min_rating)]
filtered = filtered[filtered["votes_num"].fillna(0) >= int(min_votes)]

if duration_choice != "All":
    if duration_choice == "< 2 hrs":
        filtered = filtered[filtered["duration_min"].notna() & (filtered["duration_min"] < 120)]
    elif duration_choice == "2-3 hrs":
        filtered = filtered[filtered["duration_min"].notna() & (filtered["duration_min"] >= 120) & (filtered["duration_min"] <= 180)]
    else:
        filtered = filtered[filtered["duration_min"].notna() & (filtered["duration_min"] > 180)]

st.markdown(f"Showing {len(filtered)} movies after filtering.")
st.dataframe(filtered[["title", "genre", "rating", "votes", "duration"]].head(200), use_container_width=True)

# Visuals
st.markdown("---")
st.subheader("Top Visuals")

# Top 10 Rated
top_rated = filtered.dropna(subset=["rating"]).nlargest(10, "rating")[["title", "rating"]]
if not top_rated.empty:
    st.write("Top 10 Rated Movies")
    st.bar_chart(top_rated.set_index("title"))

# Genre distribution
if "genre" in filtered.columns:
    genre_counts = filtered["genre"].value_counts().nlargest(20)
    if not genre_counts.empty:
        st.write("Genre distribution (top 20)")
        st.bar_chart(genre_counts)

# Votes vs Rating scatter
if "votes_num" in filtered.columns and "rating" in filtered.columns:
    scatter_df = filtered.dropna(subset=["rating"]).loc[:, ["votes_num", "rating"]]
    if not scatter_df.empty:
        st.write("Votes vs Rating scatter")
        st.altair_chart(
            (
                (st.altair.Chart(scatter_df)
                 .mark_circle(size=60)
                 .encode(x="votes_num", y="rating", tooltip=["votes_num", "rating"]))
            ).interactive(),
            use_container_width=True,
        )

st.markdown("---")
st.caption("Data source: scraped IMDb 2024 dataset. Backend: SQL (preferred) or CSV fallback.")
