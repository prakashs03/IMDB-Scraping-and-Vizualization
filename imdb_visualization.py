import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(page_title="IMDb 2024 SQL Explorer", layout="wide")

st.title("IMDb 2024 - SQL Query Explorer")
st.write("Explore and analyze IMDb 2024 movie data stored in AWS RDS MySQL.")

# AWS RDS Connection Details
DB_HOST = st.secrets["DB_HOST"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_NAME = st.secrets["DB_NAME"]

@st.cache_data
def load_data(query):
    try:
        engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")
        df = pd.read_sql(text(query), con=engine)
        return df
    except Exception as e:
        st.warning(f"Database connection failed ({e}). Loading local CSV instead.")
        try:
            df = pd.read_csv("data/movies_2024_detailed.csv")
            return df
        except Exception as e:
            st.error(f"CSV fallback not found. ({e})")
            return pd.DataFrame()

# Sidebar Queries
st.sidebar.header("Sample Queries")
sample = st.sidebar.selectbox(
    "Choose a query",
    [
        "All Movies",
        "Top Rated Movies",
        "Most Voted Movies",
        "Action Movies with Rating > 8",
        "Drama Movies Sorted by Votes"
    ]
)

if sample == "All Movies":
    query = "SELECT * FROM movies_2024 LIMIT 50;"
elif sample == "Top Rated Movies":
    query = "SELECT title, rating, genre FROM movies_2024 WHERE rating >= 8.0 ORDER BY rating DESC LIMIT 20;"
elif sample == "Most Voted Movies":
    query = "SELECT title, rating, votes FROM movies_2024 ORDER BY CAST(REPLACE(votes, 'K', '') AS UNSIGNED) DESC LIMIT 20;"
elif sample == "Action Movies with Rating > 8":
    query = "SELECT title, rating, genre FROM movies_2024 WHERE genre LIKE '%Action%' AND rating > 8.0 LIMIT 20;"
elif sample == "Drama Movies Sorted by Votes":
    query = "SELECT title, rating, votes FROM movies_2024 WHERE genre LIKE '%Drama%' ORDER BY CAST(REPLACE(votes, 'K', '') AS UNSIGNED) DESC LIMIT 20;"
else:
    query = "SELECT * FROM movies_2024 LIMIT 50;"

# SQL Input Box
st.subheader("Write Your Own SQL Query")
user_query = st.text_area("Enter your SQL query here:", query, height=150)

if st.button("Execute Query"):
    df = load_data(user_query)
    if not df.empty:
        st.success("Query executed successfully.")
        st.dataframe(df)
    else:
        st.warning("No data found or query failed.")
