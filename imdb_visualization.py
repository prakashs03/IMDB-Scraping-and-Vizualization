import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="IMDb 2024 Analytics Dashboard", layout="wide")

st.title(" IMDb 2024 Data Analysis & SQL Query Explorer")
st.write("Analyze IMDb 2024 movies interactively using SQL queries, filters, and dynamic visualizations.")

# ---------- DATABASE CONNECTION ----------
DB_HOST = st.secrets["DB_HOST"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_NAME = st.secrets["DB_NAME"]

# ---------- LOAD DATA ----------
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
            st.error("CSV file not found. Please upload `movies_2024_detailed.csv`.")
            df = pd.DataFrame()
    return df

df = load_data()
if df.empty:
    st.stop()

# ---------- DATA CLEANING ----------
df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
df['votes_clean'] = df['votes'].replace('N/A', '0').replace(r'[KM]', '', regex=True)
df['votes_clean'] = pd.to_numeric(df['votes_clean'], errors='coerce')

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
st.sidebar.header(" Filters")

genre_list = sorted(df['genre'].dropna().unique().tolist())
selected_genres = st.sidebar.multiselect("Select Genre(s):", genre_list)

min_rating = st.sidebar.slider("Minimum Rating", 0.0, 10.0, 0.0, 0.1)
min_votes = st.sidebar.number_input("Minimum Votes", min_value=0, value=0)
duration_filter = st.sidebar.radio("Filter by Duration", ["All", "< 2 hrs", "2–3 hrs", "> 3 hrs"], index=0)

# ---------- APPLY FILTERS ----------
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

# ---------- SQL QUERY EXPLORER (TOP SECTION) ----------
st.subheader(" SQL Query Explorer")

st.markdown("""
You can execute SQL queries directly on the IMDb 2024 dataset stored in AWS RDS.  
Example queries:  
- `SELECT * FROM movies_2024 LIMIT 10;`  
- `SELECT title, rating FROM movies_2024 WHERE rating > 8.0;`  
- `SELECT genre, COUNT(*) FROM movies_2024 GROUP BY genre;`
""")

query_input = st.text_area("Enter your SQL query below:", "SELECT * FROM movies_2024 LIMIT 10;", height=150)

if st.button("Run Query"):
    try:
        engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")
        result_df = pd.read_sql(text(query_input), con=engine)
        if not result_df.empty:
            st.success(f"Query executed successfully. Showing {len(result_df)} records.")
            st.dataframe(result_df)
        else:
            st.warning("Query executed but returned no results.")
    except Exception as e:
        st.error(f"Error executing query: {e}")

st.divider()

# ---------- VISUALIZATIONS (DYNAMIC) ----------
if not filtered_df.empty:
    st.subheader(" Dynamic Visualizations (Based on Filters)")

    col1, col2 = st.columns(2)

    # Genre Distribution
    with col1:
        st.markdown("**Top 10 Genres by Movie Count**")
        genre_counts = filtered_df['genre'].value_counts().head(10)
        fig1, ax1 = plt.subplots()
        genre_counts.plot(kind='bar', color='skyblue', ax=ax1)
        ax1.set_xlabel("Genre")
        ax1.set_ylabel("Number of Movies")
        st.pyplot(fig1)

    # Rating Distribution
    with col2:
        st.markdown("**Rating Distribution**")
        fig2, ax2 = plt.subplots()
        filtered_df['rating'].dropna().plot(kind='hist', bins=20, color='orange', ax=ax2)
        ax2.set_xlabel("Rating")
        ax2.set_ylabel("Movies Count")
        st.pyplot(fig2)

    st.divider()

    # Top Movies
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("**Top 10 Movies by Rating**")
        top_movies = filtered_df.sort_values(by='rating', ascending=False).head(10)
        st.table(top_movies[['title', 'genre', 'rating', 'votes', 'duration']])

    with col4:
        st.markdown("**Top 10 Movies by Votes**")
        top_voted = filtered_df.sort_values(by='votes_clean', ascending=False).head(10)
        st.table(top_voted[['title', 'genre', 'rating', 'votes', 'duration']])

    st.divider()

    # Correlation Plot
    st.markdown("**Correlation: Votes vs Ratings**")
    fig3, ax3 = plt.subplots()
    ax3.scatter(filtered_df['votes_clean'], filtered_df['rating'], alpha=0.6, color='purple')
    ax3.set_xlabel("Votes (in thousands)")
    ax3.set_ylabel("Ratings")
    ax3.set_title("Correlation between Votes and Ratings")
    st.pyplot(fig3)

else:
    st.warning("No movies found matching your filters.")

st.divider()

# ---------- SHOW FILTERED DATA ----------
st.subheader(" Filtered Movie Dataset")
st.dataframe(filtered_df[['title', 'genre', 'rating', 'votes', 'duration']])
