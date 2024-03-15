# Libraries
import streamlit as st
from google.cloud import bigquery
import requests
from wordcloud import WordCloud


st.set_page_config(page_title="ReelQuest", page_icon=":movie_camera:") # Page title and favicon

# ----------------------------------------#
# Loading the Data from Big Query
# ----------------------------------------#

key_bigquery_path = './testapi-415115-18f8f1b39899.json'

# Function to load movie data from BigQuery using the Google Cloud BigQuery API.
# It queries the 'movies' table from the specified dataset and returns a DataFrame.
@st.cache_data
def load_movies_data():
    try:
        client = bigquery.Client.from_service_account_json(key_bigquery_path)   # Create a client with service account credentials

        query = """
        SELECT * FROM `testapi-415115.assignment1.movies`
        """

        query_job = client.query(query)
        movies_df = query_job.to_dataframe()

        return movies_df

    except Exception as e:
        st.error(f"Error during data loading: {e}")
        return None

data_movies = load_movies_data()


# ----------------------------------------#
# Main Functionalities
# ----------------------------------------#

@st.cache_data
def handle_queries(user_input, genre_filter, language_filter, released_date_filter, average_rating_filter):

    # Handles user queries for movies
    # Args: All the inputs that the user will select through the filters.
    # Returns a list:  List of movie results matching the user's query.

    try:
        client = bigquery.Client.from_service_account_json(key_bigquery_path)   # Create a client with service account credentials
        
        base_query = """
            SELECT title, AVG(mr.rating) AS average_rating
            FROM `testapi-415115.assignment1.movies` mm
            JOIN  `testapi-415115.assignment1.ratings` mr ON mm.movieId = mr.movieId
            WHERE 1 = 1
            """

        # Additional conditions to the base query if a filter is added.
        # Many filters can be added at the same time thanks to the "if" condition
        if user_input.strip() != "":
            base_query += f" AND LOWER(title) LIKE '{user_input.lower()}%'"
        
        if genre_filter:
            base_query += f" AND genres LIKE '%{genre_filter}%'"

        if language_filter:
            base_query += f" AND language = '{language_filter}'"

        if released_date_filter:
            min_year, max_year = released_date_filter
            base_query += f" AND release_year BETWEEN {min_year} AND {max_year}"

        base_query += " GROUP BY mm.movieId, mm.title "

        if average_rating_filter:
            min_rating = average_rating_filter
            base_query += f" HAVING AVG(mr.rating) >= {min_rating}"

        query_job = client.query(base_query)        # Executing the query
        results = [{ 'title': row['title'], 'average_rating': row['average_rating'] } for row in query_job]
        return results

    except Exception as e:
        st.error(f"Error during autocomplete: {e}")
        return []


def handle_ui():

    # Handles the user interface for movie search and display

    col1, col2 = st.columns([1, 4])

    # Column 1: Filters
    with col1:
        # Displaying filter options for genre, language, released date, and average rating
        unique_genres = data_movies['genres'].str.split('|', expand=True).stack().unique()
        genre_filter = st.selectbox("Genre", [""] + list(unique_genres))
        language_filter = st.selectbox("Language", [""] + list(data_movies["language"].unique()))
        released_date_filter = st.slider("Released Date", min_value=1891, max_value=2022, value=(1900, 2022), step=1)
        average_rating_filter = st.slider("Minimum Average Rating", min_value=0, max_value=5, step=1)

    # Column 2: Search Results
    with col2:
        # Displaying text input for searching movie titles
        user_input = st.text_input("Type to search for movie titles")

        # Handling queries based on user input and applied filters
        autocomplete_results = handle_queries(user_input, genre_filter, language_filter, released_date_filter, average_rating_filter)

        if autocomplete_results:
            num_movies_found = len(autocomplete_results)
            st.write(f"Number of movies found: {num_movies_found}")
            for movie_info in autocomplete_results:
                title = movie_info['title']
                average_rating = round(movie_info['average_rating'], 1)
                num_stars = int(average_rating)
                star_emoji = "⭐️" * num_stars

                # Displaying buttons for each movie title found
                if st.button(title):
                    movie_row = data_movies[data_movies["title"] == title].iloc[0]
                    poster_url = get_movie_poster(movie_row["tmdbId"])
                    description = get_movie_details(movie_row["tmdbId"])
                    trailer_url = get_movie_trailer(movie_row["tmdbId"])
                    
                    col1, col2 = st.columns([2, 2])

                    with col1:
                        # Displaying movie poster if available on the left
                        if poster_url:
                            st.image(poster_url, caption=title, width=col1.width, use_column_width=True)
                        else:
                            st.write(f"No poster found for {title}")

                    with col2:
                        # Displaying all other information on the right
                        st.write("**Title:**", title)
                        st.write("**Genre:**", movie_row["genres"])
                        st.write("**Language:**", movie_row["language"])
                        st.write("**Average Rating:**", f"{star_emoji} ({average_rating})") 
                        st.write("**Description:**", description)
                        st.write("**Trailer:**", trailer_url)

                    # Button to close the movie details section
                    if st.button("Close"):
                        st.text("")             
        
        else:
            st.write("No matching titles found.")


# ----------------------------------------#
# TMDB Related Functions
# ----------------------------------------#

@st.cache_data
def get_movie_poster(tmdb_id):

    # Fetches the poster image URL for a given movie ID from TMDB.
    # Args: tmdb_id (str): TMDB movie ID.
    # Returns an str: URL of the movie poster image.

    api_key = "35a1a21523af09d62c97695abf6bc067"  # This is my TMDB API key
    base_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/images?api_key={api_key}"
    
    try:
        response = requests.get(base_url)
        data = response.json()
        if "posters" in data and data["posters"]:
            return f"https://image.tmdb.org/t/p/w500{data['posters'][0]['file_path']}" # Return the URL of the first poster image
        else:
            return None
    except Exception as e:
        print(f"Error fetching movie poster: {e}")
        return None


@st.cache_data
def get_movie_details(tmdb_id):

    # Fetches the details of a movie from TMDB.
    # Args: tmdb_id (str): TMDB movie ID.
    # Returns an str : Description of the movie.


    api_key = "35a1a21523af09d62c97695abf6bc067"  # This is my TMDB API key
    base_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}"
    
    try:
        response = requests.get(base_url)
        data = response.json()
        if "overview" in data:
            # Return the overview/description of the movie
            return data["overview"]
        else:
            return None
    except Exception as e:
        print(f"Error fetching movie details: {e}")
        return None


@st.cache_data
def get_movie_trailer(tmdb_id):

    # Fetches the movie trailer URL for a given movie ID from TMDB.
    # Args: tmdb_id (str): TMDB movie ID.
    # Returns an str : URL of the movie trailer on YouTube.

    api_key = "35a1a21523af09d62c97695abf6bc067"  # This is my TMDB API key
    base_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos?api_key={api_key}"
    
    try:
        response = requests.get(base_url)
        data = response.json()
        if "results" in data and data["results"]:
            for video in data["results"]:
                if video.get("type") == "Trailer" and video.get("site") == "YouTube": 
                    # if a trailer on youtube exists, it will return its URL
                    return f"https://www.youtube.com/watch?v={video['key']}"
        return None
    except Exception as e:
        print(f"Error fetching movie trailer: {e}")
        return None


# ----------------------------------------#
# Creating a user-friendly website (UI/UX)
# ----------------------------------------#

# Titles
st.write(""" <div style="color:#666666; font-size:48px; text-align:center;">🎬 ReelQuest 🎥</div> """, unsafe_allow_html=True)
st.write(""" <div style="color:#666666; font-size:36px; text-align:center;">Discover Cinematic Treasures</div> """, unsafe_allow_html=True)
st.write(""" <div style="color:#666666; font-size:16px; text-align:center;">By Laura Fabbiano</div> """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("   ")

# Creating 3 columns to display 3 different statistics to make the site more fun
col1, col2, col3 = st.columns(3)

# Stats about language distribution
col1.write(f"<div style='color:white; font-size:18px; text-align:center;'>AVAILABLE LANGUAGES </div>", unsafe_allow_html=True)
col1.write(" ")
language_counts = data_movies["language"].value_counts().to_dict()
wordcloud = WordCloud(width=800, height=400, background_color='#0d1118').generate_from_frequencies(language_counts)
col1.image(wordcloud.to_array(), use_column_width=True)


# Stats about the number of available movies
col1.write(" ")
col2.write(f"<div style='color:white; text-align:center; font-size:18px;'>NUMBER OF MOVIES <span style='color:#ffcc00; font-size:72px; text-align:center;'>26210</span></div>", unsafe_allow_html=True)


# Stats about the genres
col3.write(f"<div style='color:white; font-size:18px; text-align:center;'>DIFFERENT GENRES</div>", unsafe_allow_html=True)
col3.write(" ")
data_movies['clean_genres'] = data_movies['genres'].apply(lambda x: x.split('|')[0])   #cleaning the data
genre_counts = data_movies['clean_genres'].value_counts()
wordcloud = WordCloud(width=800, height=400, background_color='#0d1118').generate_from_frequencies(genre_counts)
col3.image(wordcloud.to_array(), use_column_width=True)


# Some separations for the esthetic
st.markdown("  ")
st.markdown("  ")
st.markdown("  ")

st.write(""" <div style="font-size:21px;">Feel free to search a movie using the filters provided below</div> """, unsafe_allow_html=True)

st.markdown("  ")

# Calling the main function to search for movies and using filters
handle_ui()

st.markdown("---")

st.write(""" <div style="color:#ff6666; font-size:18px; text-align:center;">Don't hesitate to reach out if you need assistance!</div> """, unsafe_allow_html=True)
st.write(""" <div style="color:white; font-size:14px; text-align:center;">laura.fabbiano.gomez@hotmail.com</div> """, unsafe_allow_html=True)