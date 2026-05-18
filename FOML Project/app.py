from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import pickle
import os
import re

app = Flask(__name__)

# ─── Language detection helpers ───────────────────────────────────────────────
INDIAN_DIRECTORS = {
    'Rajkumar Hirani', 'Sanjay Leela Bhansali', 'Nitesh Tiwari', 'Anurag Kashyap',
    'Zoya Akhtar', 'Imtiaz Ali', 'Vishal Bhardwaj', 'Dibakar Banerjee',
    'Vikramaditya Motwane', 'Shoojit Sircar', 'S.S. Rajamouli', 'Mani Ratnam',
    'Shankar', 'K. Balachander', 'Priyadarshan', 'Sukumar', 'Trivikram Srinivas',
    'Prashanth Neel', 'Rishab Shetty', 'Vetrimaaran', 'Pa. Ranjith', 'Mari Selvaraj',
    'Bala', 'Selvaraghavan', 'Gautham Vasudev Menon', 'A.R. Murugadoss',
    'Atlee', 'Nelson Dilipkumar', 'Lokesh Kanagaraj', 'Karthik Subbaraj',
    'Fahadh Faasil', 'Dileesh Pothan', 'Lijo Jose Pellissery', 'Jeethu Joseph',
    'Alphonse Puthren', 'Aashiq Abu', 'Mahesh Narayanan', 'Shyamaprasad',
    'Siddique', 'Ranjith', 'Renji Panicker', 'Vineeth Sreenivasan',
    'Amal Neerad', 'Anjali Menon', 'Lal Jose', 'Anwar Rasheed',
    'Shoojit Sircar', 'Neeraj Pandey', 'Tigmanshu Dhulia', 'Abhishek Chaubey',
    'Aanand L. Rai', 'Sriram Raghavan', 'Raj Kumar Gupta', 'Hansal Mehta',
    'Onir', 'Sudhir Mishra', 'Nagesh Kukunoor', 'Aparna Sen',
    'Rituparno Ghosh', 'Mrinal Sen', 'Satyajit Ray', 'Ritwik Ghatak',
    'Bimal Roy', 'Guru Dutt', 'Raj Kapoor', 'Yash Chopra',
    'Karan Johar', 'Aditya Chopra', 'Subhash Ghai',
}

INDIAN_NAME_PATTERNS = [
    r'\b(Kumar|Singh|Sharma|Patel|Rao|Reddy|Nair|Menon|Pillai|Iyer|Krishnan|Venkatesh)\b',
    r'\b(Ranbir|Ranveer|Deepika|Priyanka|Aamir|Salman|Shah Rukh|Amitabh|Hrithik)\b',
    r'\b(Vijay|Ajith|Dhanush|Suriya|Vikram|Kamal|Rajinikanth|Mohanlal|Mammootty)\b',
    r'\b(Prabhas|Allu Arjun|Ram Charan|Jr\.? NTR|Mahesh Babu|Chiranjeevi)\b',
]

JAPANESE_KOREAN_PATTERNS = [
    r'\b(Kurosawa|Miyazaki|Kitano|Miike|Ozu|Kobayashi|Naruse)\b',
    r'\b(Bong|Park|Kim|Lee|Joon-ho|Chan-wook|Woo-sik)\b',
]

def detect_language(row):
    director = str(row.get('Director', ''))
    actors = str(row.get('Actors', ''))
    title = str(row.get('Movie_Title', ''))
    censor = str(row.get('Censor', ''))

    # Explicit US/EU censors lean English
    if censor in ['R', 'PG-13', 'PG', 'G', 'NC-17', 'Not Rated', 'Unrated']:
        # Could still be Indian co-production; check director
        if director in INDIAN_DIRECTORS:
            return 'Hindi'
        # Check actor names
        for pat in INDIAN_NAME_PATTERNS:
            if re.search(pat, actors, re.IGNORECASE):
                return 'Hindi'
        return 'English'

    # Indian censor board
    if censor in ['UA', 'U', 'A', 'UA 16+', 'UA 13+', 'UA 7+']:
        if director in INDIAN_DIRECTORS:
            # Rough South Indian director detection
            south_indian = {
                'S.S. Rajamouli', 'Sukumar', 'Trivikram Srinivas', 'Prashanth Neel',
                'Rishab Shetty', 'Vetrimaaran', 'Pa. Ranjith', 'Mari Selvaraj',
                'Bala', 'Selvaraghavan', 'Gautham Vasudev Menon', 'A.R. Murugadoss',
                'Atlee', 'Nelson Dilipkumar', 'Lokesh Kanagaraj', 'Karthik Subbaraj',
                'Dileesh Pothan', 'Lijo Jose Pellissery', 'Jeethu Joseph',
                'Alphonse Puthren', 'Aashiq Abu', 'Mahesh Narayanan',
                'Amal Neerad', 'Anjali Menon',
            }
            telugu_directors = {
                'S.S. Rajamouli', 'Sukumar', 'Trivikram Srinivas', 'Prashanth Neel',
            }
            kannada_directors = {'Rishab Shetty'}
            if director in telugu_directors:
                return 'Telugu'
            if director in kannada_directors:
                return 'Kannada'
            if director in (south_indian - telugu_directors - kannada_directors):
                return 'Tamil/Malayalam'
            return 'Hindi'
        # Check actors for South Indian names
        if any(name in actors for name in ['Prabhas', 'Allu Arjun', 'Ram Charan', 'Jr. NTR', 'Mahesh Babu']):
            return 'Telugu'
        if any(name in actors for name in ['Vijay', 'Ajith', 'Dhanush', 'Suriya', 'Vikram', 'Kamal Haasan', 'Rajinikanth']):
            return 'Tamil/Malayalam'
        if any(name in actors for name in ['Mohanlal', 'Mammootty', 'Fahadh Faasil']):
            return 'Tamil/Malayalam'
        return 'Hindi'

    # European/other
    for pat in JAPANESE_KOREAN_PATTERNS:
        if re.search(pat, director + ' ' + actors, re.IGNORECASE):
            return 'Korean/Japanese'

    return 'English'


def load_and_prepare_data():
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'movies.csv'))
    df.dropna(subset=['Rating', 'Year', 'main_genre'], inplace=True)
    df['Language'] = df.apply(detect_language, axis=1)

    # Encode genres
    genre_encoder = LabelEncoder()
    df['genre_encoded'] = genre_encoder.fit_transform(df['main_genre'])

    lang_encoder = LabelEncoder()
    df['lang_encoded'] = lang_encoder.fit_transform(df['Language'])

    return df, genre_encoder, lang_encoder


def train_model(df):
    """Train Random Forest to predict a 'recommendation score' label."""
    # Create a target: movies with rating >= 7 are 'highly recommended'
    df['recommendation'] = (df['Rating'] >= 7.0).astype(int)

    features = ['genre_encoded', 'lang_encoded', 'Year', 'Rating']
    X = df[features]
    y = df['recommendation']

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X, y)
    return model


# ─── Boot-time training ────────────────────────────────────────────────────────
df_global, genre_encoder, lang_encoder = load_and_prepare_data()
model = train_model(df_global)

GENRES = sorted(df_global['main_genre'].unique().tolist())
LANGUAGES = sorted(df_global['Language'].unique().tolist())
YEAR_MIN = int(df_global['Year'].min())
YEAR_MAX = int(df_global['Year'].max())


# ─── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html',
                           genres=GENRES,
                           languages=LANGUAGES,
                           year_min=YEAR_MIN,
                           year_max=YEAR_MAX)


@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json()

    genre = data.get('genre')
    language = data.get('language')
    imdb_min = float(data.get('imdb_min', 6.0))
    imdb_max = float(data.get('imdb_max', 10.0))
    year_min = int(data.get('year_min', 2000))
    year_max = int(data.get('year_max', 2022))

    # Filter dataset
    filtered = df_global[
        (df_global['main_genre'] == genre) &
        (df_global['Language'] == language) &
        (df_global['Rating'] >= imdb_min) &
        (df_global['Rating'] <= imdb_max) &
        (df_global['Year'] >= year_min) &
        (df_global['Year'] <= year_max)
    ].copy()

    if filtered.empty:
        return jsonify({'movies': [], 'message': 'No movies found for your filters. Try widening the range!'})

    # Use RF model to get recommendation probabilities
    features = ['genre_encoded', 'lang_encoded', 'Year', 'Rating']
    proba = model.predict_proba(filtered[features])[:, 1]  # prob of being "highly recommended"
    filtered['rf_score'] = proba

    # Sort by RF score, then by rating
    filtered = filtered.sort_values(['rf_score', 'Rating'], ascending=False)

    top = filtered.head(20)

    movies = []
    for _, row in top.iterrows():
        movies.append({
            'title': row['Movie_Title'],
            'year': int(row['Year']),
            'rating': round(float(row['Rating']), 1),
            'genre': row['main_genre'],
            'side_genre': str(row.get('side_genre', '')).strip(),
            'director': str(row.get('Director', 'N/A')),
            'language': row['Language'],
            'runtime': int(row.get('Runtime(Mins)', 0)),
            'censor': str(row.get('Censor', 'N/A')),
            'rf_score': round(float(row['rf_score']), 3),
        })

    return jsonify({'movies': movies, 'message': f'{len(movies)} movies found'})


@app.route('/filter-options')
def filter_options():
    return jsonify({
        'genres': GENRES,
        'languages': LANGUAGES,
        'year_min': YEAR_MIN,
        'year_max': YEAR_MAX,
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
