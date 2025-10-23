import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

# Streamlit page setup
st.set_page_config(page_title="IMDb 2024 Analytics Dashboard", layout="wide")

# Title and intro
st.title("🎬 IMDb 2024 Data Visualization Dashboard")
st.write("Analyze, visualize, and explore IMDb 2024 movie data using AWS RDS SQL and interactive filters.")

# AWS RDS credentials (from Streamlit secrets)
DB_HOST = st.secrets["DB_HOST"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_NAME = st.secrets["DB_NAME"]

# ---------- DATA LOADING ----------
@st.cache_data
def load_data():
    try:
        engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")
        df = pd.read_sql(text("SELECT * FROM movies_2024"), con=engine)
        st.sidebar.success("Connected to AWS RDS successfully ")
    except Exception as e:
        st.sidebar.warning(f"Database connection failed ({e}). Loading local CSV instead.")
        try:
            df = pd.read_csv("data/movies_2024_detailed.csv")
            st.sidebar.info("Loaded data from local CSV backup.")
        except:
            st.error("CSV file not found. Please ensure 'data/movies_2024_detailed.csv' exists.")
            df = pd.DataFrame()
    return df

df = load_data()
if df.empty:
    st.error("No data available to display.")
    st.stop()

# ---------- DATA CLEANING ----------
df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
df['votes_clean'] = df['votes'].replace('N/A', '0').replace(r'[KM]', '', regex=True)
df['votes_clean'] = pd.to_numeric(df['votes_clean'], errors='coerce')

# Convert duration into minutes
def get_duration_in_minutes(d):
    try:
        if 'h' in d and 'm' in d:
            parts = d.replace('h', '').replace('m', '').split()
            h, m = map(int, parts)
            return h * 60 + m
        elif 'h' in d:
            return int(d.replace('h', '').strip()) * 60
        elif 'm' in d:
            return int(d.replace('m', '').strip())
        else:
            return 0
    except:
        return 0

df['duration_mins'] = df['duration'].fillna("0").apply(get_duration_in_minutes)

# ---------- SIDEBAR FILTERS ----------
st.sidebar.header("🎛️ Filters")

genre_list = sorted(df['genre'].dropna().unique().tolist())
selected_genres = st.sidebar.multiselect("Select Genre(s):", genre_list)

min_rating = st.sidebar.slider("Minimum Rating", 0.0, 10.0, 6.0, 0.1)
min_votes = st.sidebar.number_input("Minimum Votes", min_value=0, value=100)
duration_filter = st.sidebar.radio("Filter by Duration", ["All", "< 2 hrs", "2-3 hrs", "> 3 hrs"])

# Apply filters
filtered_df = df.copy()

if selected_genres:
    filtered_df = filtered_df[filtered_df['genre'].str.contains('|'.join(selected_genres), case=False, na=False)]

filtered_df = filtered_df[filtered_df['rating'] >= min_rating]
filtered_df = filtered_df[filtered_df['votes_clean'] >= min_votes]

if duration_filter == "< 2 hrs":
    filtered_df = filtered_df[filtered_df['duration_mins'] < 120]
elif duration_filter == "2-3 hrs":
    filtered_df = filtered_df[(filtered_df['duration_mins'] >= 120) & (filtered_df['duration_mins'] <= 180)]
elif duration_filter == "> 3 hrs":
    filtered_df = filtered_df[filtered_df['duration_mins'] > 180]

# ---------- DASHBOARD METRICS ----------
st.divider()
col1, col2, col3 = st.columns(3)
col1.metric("Total Movies", len(filtered_df))
col2.metric("Average Rating", f"{filtered_df['rating'].mean():.2f}")
col3.metric("Average Votes", f"{filtered_df['votes_clean'].mean():,.0f}")

st.divider()

# ---------- VISUALIZATIONS ----------

# 1️ Genre Distribution
st.subheader("🎭 Genre Distribution (Top 10)")
genre_counts = filtered_df['genre'].value_counts().head(10)
fig1, ax1 = plt.subplots()
genre_counts.plot(kind='bar', color='skyblue', ax=ax1)
ax1.set_title("Top 10 Genres by Movie Count")
ax1.set_xlabel("Genre")
ax1.set_ylabel("Number of Movies")
st.pyplot(fig1)

# 2️ Rating Distribution
st.subheader("⭐ Rating Distribution")
fig2, ax2 = plt.subplots()
filtered_df['rating'].dropna().plot(kind='hist', bins=20, color='orange', ax=ax2)
ax2.set_xlabel("Rating")
ax2.set_ylabel("Number of Movies")
ax2.set_title("Distribution of IMDb Ratings")
st.pyplot(fig2)

# 3️ Top 10 Movies by Rating
st.subheader(" Top 10 Movies by Rating")
top_movies = filtered_df.sort_values(by='rating', ascending=False).head(10)
st.table(top_movies[['title', 'genre', 'rating', 'votes', 'duration']])

# 4️ Top 10 Movies by Votes
st.subheader(" Top 10 Movies by Votes")
top_voted = filtered_df.sort_values(by='votes_clean', ascending=False).head(10)
st.table(top_voted[['title', 'genre', 'rating', 'votes', 'duration']])

# 5️ Correlation Between Votes and Ratings
st.subheader(" Correlation: Votes vs Ratings")
fig3, ax3 = plt.subplots()
ax3.scatter(filtered_df['votes_clean'], filtered_df['rating'], alpha=0.5)
ax3.set_xlabel("Votes (in thousands)")
ax3.set_ylabel("Ratings")
ax3.set_title("Correlation between Votes and Ratings")
st.pyplot(fig3)

st.divider()

# ---------- SHOW FILTERED DATA ----------
st.subheader(" Filtered Movie Data")
st.dataframe(filtered_df[['title', 'genre', 'rating', 'votes', 'duration']])
