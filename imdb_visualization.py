import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="IMDb 2024 SQL-Based Visualization", layout="wide")

st.title("🎬 IMDb 2024 Interactive Data Analysis & SQL Visualization")
st.caption("Dynamically explore IMDb 2024 movies using SQL queries and live charts.")

# ---------- DATABASE CONNECTION ----------
DB_HOST = st.secrets["DB_HOST"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_NAME = st.secrets["DB_NAME"]

@st.cache_data
def load_data():
    try:
        engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")
        df = pd.read_sql(text("SELECT * FROM movies_2024"), con=engine)
        st.sidebar.success("Connected to AWS RDS ")
    except Exception as e:
        st.sidebar.warning(f"Database connection failed ({e}). Loading CSV backup...")
        try:
            df = pd.read_csv("data/movies_2024_detailed.csv")
            st.sidebar.info("Loaded from local CSV.")
        except:
            st.error("CSV file not found. Please upload 'movies_2024_detailed.csv'.")
            df = pd.DataFrame()
    return df

df = load_data()
if df.empty:
    st.stop()

# ---------- SIDEBAR FILTERS ----------
st.sidebar.header(" Filters")

genres = sorted(df['genre'].dropna().unique().tolist())
selected_genres = st.sidebar.multiselect("Select Genre(s):", genres)
min_rating = st.sidebar.slider("Minimum Rating", 0.0, 10.0, 0.0, 0.1)
min_votes = st.sidebar.number_input("Minimum Votes", min_value=0, value=0)
duration_filter = st.sidebar.radio("Filter by Duration", ["All", "< 2 hrs", "2–3 hrs", "> 3 hrs"], index=0)

# ---------- FILTER DATA ----------
df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
df['votes_clean'] = df['votes'].replace('N/A', '0').replace(r'[KM]', '', regex=True)
df['votes_clean'] = pd.to_numeric(df['votes_clean'], errors='coerce')

def convert_duration(d):
    try:
        if 'h' in d and 'm' in d:
            h, m = d.replace('h', '').replace('m', '').split()
            return int(h) * 60 + int(m)
        elif 'h' in d:
            return int(d.replace('h', '').strip()) * 60
        elif 'm' in d:
            return int(d.replace('m', '').strip())
        else:
            return 0
    except:
        return 0

df['duration_mins'] = df['duration'].fillna("0").apply(convert_duration)
filtered_df = df.copy()

if selected_genres:
    filtered_df = filtered_df[filtered_df['genre'].str.contains('|'.join(selected_genres), case=False, na=False)]
if min_rating > 0:
    filtered_df = filtered_df[filtered_df['rating'] >= min_rating]
if min_votes > 0:
    filtered_df = filtered_df[filtered_df['votes_clean'] >= min_votes]
if duration_filter == "< 2 hrs":
    filtered_df = filtered_df[filtered_df['duration_mins'] < 120]
elif duration_filter == "2–3 hrs":
    filtered_df = filtered_df[(filtered_df['duration_mins'] >= 120) & (filtered_df['duration_mins'] <= 180)]
elif duration_filter == "> 3 hrs":
    filtered_df = filtered_df[filtered_df['duration_mins'] > 180]

# ---------- SQL QUERY EXPLORER ----------
st.subheader(" SQL Query Explorer (Dynamic Visualization)")

st.markdown("""
Enter any **SQL query** to explore and visualize data from the IMDb 2024 dataset.  
Examples:  
- `SELECT * FROM movies_2024 LIMIT 10;`  
- `SELECT genre, COUNT(*) AS count FROM movies_2024 GROUP BY genre ORDER BY count DESC;`  
- `SELECT title, rating, votes FROM movies_2024 WHERE rating > 8.0;`
""")

query_input = st.text_area("Enter your SQL query:", "SELECT * FROM movies_2024 LIMIT 10;", height=150)

if st.button("Run Query"):
    try:
        engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")
        result_df = pd.read_sql(text(query_input), con=engine)

        if not result_df.empty:
            st.success(f"Query executed successfully. Showing {len(result_df)} records.")
            st.dataframe(result_df, use_container_width=True)

            # ---------- DYNAMIC VISUALIZATION ----------
            st.subheader(" Visualization for Query Results")

            # Detect numeric and categorical columns
            numeric_cols = result_df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            cat_cols = result_df.select_dtypes(exclude=['float64', 'int64']).columns.tolist()

            if len(numeric_cols) >= 2:
                st.markdown("**Scatter Plot (First 2 Numeric Columns)**")
                fig, ax = plt.subplots(figsize=(5, 3))
                ax.scatter(result_df[numeric_cols[0]], result_df[numeric_cols[1]], color='teal', alpha=0.6)
                ax.set_xlabel(numeric_cols[0])
                ax.set_ylabel(numeric_cols[1])
                st.pyplot(fig)

            elif len(numeric_cols) == 1 and len(cat_cols) >= 1:
                st.markdown("**Bar Chart (Category vs Numeric)**")
                fig, ax = plt.subplots(figsize=(5, 3))
                result_df.groupby(cat_cols[0])[numeric_cols[0]].mean().sort_values(ascending=False).head(10).plot(kind='bar', ax=ax)
                ax.set_xlabel(cat_cols[0])
                ax.set_ylabel(numeric_cols[0])
                st.pyplot(fig)

            elif len(cat_cols) >= 1:
                st.markdown("**Category Frequency Chart**")
                fig, ax = plt.subplots(figsize=(5, 3))
                result_df[cat_cols[0]].value_counts().head(10).plot(kind='bar', color='skyblue', ax=ax)
                ax.set_xlabel(cat_cols[0])
                ax.set_ylabel("Count")
                st.pyplot(fig)

            else:
                st.info("No suitable numeric or categorical columns for visualization.")

        else:
            st.warning("Query executed but returned no results.")
    except Exception as e:
        st.error(f"Error executing query: {e}")

st.divider()

# ---------- FILTERED DATA SECTION ----------
st.subheader(" Filtered Movie Dataset")
st.caption("These results dynamically update as you change filters.")
st.dataframe(filtered_df[['title', 'genre', 'rating', 'votes', 'duration']], use_container_width=True)
