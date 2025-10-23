import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

# ---------- Page Setup ----------
st.set_page_config(page_title="IMDb 2024 Analytics Dashboard", layout="wide")

st.title(" IMDb 2024 Data Analysis & SQL Query Explorer")
st.write("Explore IMDb 2024 movie data interactively using SQL and visualization tools.")

# ---------- AWS RDS Credentials ----------
DB_HOST = st.secrets["DB_HOST"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_NAME = st.secrets["DB_NAME"]

# ---------- Load Data ----------
@st.cache_data
def load_data():
    try:
        engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")
        df = pd.read_sql(text("SELECT * FROM movies_2024"), con=engine)
        st.sidebar.success("Connected to AWS RDS successfully")
    except Exception as e:
        st.sidebar.warning(f"Database connection failed ({e}). Loading from CSV instead.")
        try:
            df = pd.read_csv("data/movies_2024_detailed.csv")
        except:
            st.error("CSV file not found. Please upload 'movies_2024_detailed.csv'.")
            df = pd.DataFrame()
    return df

df = load_data()
if df.empty:
    st.error("No data available to display.")
    st.stop()

# ---------- Data Cleaning ----------
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

# ---------- Sidebar Filters ----------
st.sidebar.header(" Filters")

genre_list = sorted(df['genre'].dropna().unique().tolist())
selected_genres = st.sidebar.multiselect("Select Genre(s):", genre_list, default=None)

min_rating = st.sidebar.slider("Minimum Rating", 0.0, 10.0, 0.0, 0.1)
min_votes = st.sidebar.number_input("Minimum Votes", min_value=0, value=0)
duration_filter = st.sidebar.radio("Filter by Duration", ["All", "< 2 hrs", "2–3 hrs", "> 3 hrs"], index=0)

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

st.divider()

# ---------- Charts Section ----------
st.subheader(" Genre Distribution (Top 10)")
genre_counts = df['genre'].value_counts().head(10)
fig1, ax1 = plt.subplots()
genre_counts.plot(kind='bar', color='skyblue', ax=ax1)
ax1.set_title("Top 10 Genres by Movie Count")
ax1.set_xlabel("Genre")
ax1.set_ylabel("Number of Movies")
st.pyplot(fig1)

st.subheader(" Rating Distribution")
fig2, ax2 = plt.subplots()
df['rating'].dropna().plot(kind='hist', bins=20, color='orange', ax=ax2)
ax2.set_xlabel("Rating")
ax2.set_ylabel("Number of Movies")
ax2.set_title("Distribution of IMDb Ratings")
st.pyplot(fig2)

st.subheader(" Correlation: Votes vs Ratings")
fig3, ax3 = plt.subplots()
ax3.scatter(df['votes_clean'], df['rating'], alpha=0.6, color='purple')
ax3.set_xlabel("Votes (in thousands)")
ax3.set_ylabel("Ratings")
ax3.set_title("Correlation between Votes and Ratings")
st.pyplot(fig3)

st.divider()

# ---------- SQL Query Section ----------
st.subheader(" SQL Query Explorer")

st.markdown("""
Write your own SQL query to explore the IMDb 2024 dataset.
Example queries you can try:
- `SELECT * FROM movies_2024 LIMIT 10;`
- `SELECT title, rating FROM movies_2024 WHERE rating > 8.5;`
- `SELECT genre, COUNT(*) FROM movies_2024 GROUP BY genre;`
""")

query_input = st.text_area("Enter your SQL query:", "SELECT * FROM movies_2024 LIMIT 10;", height=150)

if st.button("Run Query"):
    try:
        engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")
        result_df = pd.read_sql(text(query_input), con=engine)
        if not result_df.empty:
            st.success("Query executed successfully.")
            st.dataframe(result_df)
        else:
            st.warning("Query executed, but returned no results.")
    except Exception as e:
        st.error(f"Error executing query: {e}")

st.divider()

# ---------- Display Filtered Data ----------
st.subheader(" Full Movie Dataset (After Filters)")
st.dataframe(filtered_df[['title', 'genre', 'rating', 'votes', 'duration']])
