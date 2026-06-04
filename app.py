from flask import Flask, render_template, request, jsonify, session, redirect
import random
import smtplib
import time
import requests
from email.mime.text import MIMEText
import sqlite3

selected_cuisine = "Any"
selected_budget = "Any"
selected_food_type = "Any"

app = Flask(__name__)
app.secret_key = "super_secret_key"

GOOGLE_API_KEY = "AIzaSyDAA9513gmfOsnqi6PtnmF2ytGKR90CSkU"

EMAIL_ADDRESS = "shaikmohammedasif52@gmail.com"
EMAIL_PASSWORD = "sgwpupfftmaadqgb"

OTP_EXPIRY_SECONDS = 120


# ================= DATABASE =================

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        first_name TEXT,
        last_name TEXT,
        age INTEGER,
        phone TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS favorites(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        name TEXT,
        address TEXT,
        rating REAL,
        lat REAL,
        lon REAL,
        photo TEXT
    )
    """)
 
    conn.commit()
    conn.close()

init_db()
#=========FILTER BAD REVIEWS===========
def is_fake_review(text):

    text = text.lower()

    # too short
    if len(text.split()) < 4:
        return True

    # repeated words
    if text.count("good") > 2:
        return True 

    # spammy text
    if "best best best" in text:
        return True

    return False
#================CALCULATE CLEAN RATING=============
def get_clean_rating(reviews):

    total = 0
    count = 0

    for r in reviews:
        text = r.get("text", "")
        rating = r.get("rating", 0)

        if not is_fake_review(text):
            total += rating
            count += 1

    if count == 0:
        return 0

    return round(total / count, 2)


# ================= OTP =================

def send_email_otp(receiver_email, otp):
    try:
        msg = MIMEText(f"Your OTP is {otp}")
        msg["Subject"] = "FoodFinder OTP"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = receiver_email

        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        server.sendmail(
            EMAIL_ADDRESS,
            receiver_email,
            msg.as_string()
        )

        server.quit()

        print("EMAIL SENT SUCCESSFULLY")

    except Exception as e:
        print("EMAIL ERROR:", str(e))


@app.route("/get_otp", methods=["POST"])
def get_otp():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({
            "status": "error",
            "message": "Email required"
        })

    otp = str(random.randint(100000, 999999))

    session["otp"] = otp
    session["otp_time"] = time.time()
    session["email"] = email

    print("OTP GENERATED:", otp)

    try:
        send_email_otp(email, otp)

        return jsonify({
            "status": "sent",
            "otp": otp
        })

    except Exception as e:
        print("OTP ERROR:", str(e))

        return jsonify({
            "status": "error",
            "message": str(e),
            "otp": otp
        })

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    user_otp = data.get("otp")

    saved_otp = session.get("otp")
    otp_time = session.get("otp_time")

    if not saved_otp:
        return jsonify({"status": "error"})

    if time.time() - otp_time > OTP_EXPIRY_SECONDS:
        return jsonify({"status": "expired"})

    if user_otp == saved_otp:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "invalid"})

# ================= GOOGLE =================

def get_lat_lon(location):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location, "key": GOOGLE_API_KEY}

    res = requests.get(url, params=params).json()

    if res["status"] == "OK":
        loc = res["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    return None, None


def get_nearby_restaurants(lat, lon, min_rating=0):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    params = {
        "location": f"{lat},{lon}",
        "radius": 5000,
        "type": "restaurant",
        "key": GOOGLE_API_KEY
    }

    response = requests.get(url, params=params).json()

    restaurants = []

    if response.get("status") != "OK":
        return []

    for place in response.get("results", []):
        rating = place.get("rating", 0)

        if rating >= min_rating:
            photo_url = None

            if "photos" in place:
                ref = place["photos"][0]["photo_reference"]
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={ref}&key={GOOGLE_API_KEY}"

            restaurants.append({
                "name": place.get("name"),
                "rating": rating,
                "address": place.get("vicinity"),
                "lat": place["geometry"]["location"]["lat"],
                "lon": place["geometry"]["location"]["lng"],
                "photo": photo_url,
                "place_id": place.get("place_id")
            })

    return restaurants

@app.route("/profile_check")
def profile_check():

    email = session.get("email")

    if not email:
        return jsonify({"status": "new"})

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    conn.close()

    if user:
        return jsonify({"status": "existing"})
    else:
        return jsonify({"status": "new"})


# ================= ROUTES =================

@app.route("/")
def login():
    return render_template("login.html")


@app.route("/search")
def search():
    return render_template("index.html")

@app.route("/user_details")
def user_details():
    return render_template("user_details.html")

@app.route("/save_details", methods=["POST"])
def save_details():

    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    phone = request.form.get("phone")
    email = session.get("email")

    if not email:
        return redirect("/")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # create table if not exists


    # insert user
    cursor.execute("""
    INSERT OR REPLACE INTO users (first_name, last_name, email, phone)
    VALUES (?, ?, ?, ?)
    """, (first_name, last_name, email, phone))

    conn.commit()
    conn.close()

    return redirect("/home")


# ================= SETTINGS =================

@app.route("/settings")
def settings():
    email = session.get("email")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT first_name, phone FROM users WHERE email=?", (email,))
    row = cursor.fetchone()
    conn.close()

    user = None
    if row:
        user = {"name": row[0], "phone": row[1]}

    return render_template("settings.html", user=user)


@app.route("/save_settings", methods=["POST"])
def save_settings():
    email = session.get("email")

    name = request.form.get("name")
    phone = request.form.get("phone")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users SET first_name=?, phone=? WHERE email=?
    """, (name, phone, email))

    conn.commit()
    conn.close()

    return redirect("/settings")


@app.route("/save_preferences", methods=["POST"])
def save_preferences():
    session["food_type"] = request.form.get("food_type")
    session["cuisine"] = request.form.get("cuisine")
    session["budget"] = request.form.get("budget")
    return redirect("/settings")


@app.route("/save_location", methods=["POST"])
def save_location():
    session["city"] = request.form.get("city")
    session["auto_location"] = request.form.get("auto_location")
    return redirect("/settings")


@app.route("/save_ai", methods=["POST"])
def save_ai():
    session["ai_enabled"] = request.form.get("ai_enabled")
    return redirect("/settings")


@app.route("/save_theme", methods=["POST"])
def save_theme():
    session["theme"] = request.form.get("theme")
    return redirect("/settings")


@app.route("/clear_favorites", methods=["POST"])
def clear_favorites():
    email = session.get("email")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM favorites WHERE email=?", (email,))
    conn.commit()
    conn.close()

    return redirect("/settings")


# 🔥 RESTAURANT DETAILS
@app.route("/restaurant")
def restaurant():
    r = {
        "name": request.args.get("name", ""),
        "address": request.args.get("address", ""),
        "rating": request.args.get("rating", "N/A"),
        "lat": float(request.args.get("lat") or 0),
        "lon": float(request.args.get("lon") or 0),
        "photo": request.args.get("photo"),
        "place_id": request.args.get("place_id"),
        "reviews": []
    }

    if r["place_id"]:
        try:
            url = "https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                "place_id": r["place_id"],
                "fields": "reviews",
                "key": GOOGLE_API_KEY
            }

            res = requests.get(url, params=params).json()

            if res.get("status") == "OK":
                r["reviews"] = res["result"].get("reviews", [])
                r["clean_rating"] = get_clean_rating(r["reviews"])

        except Exception as e:
            print("Reviews Error:", e)

    return render_template("restaurant.html", r=r)


# ================= HOME =================

@app.route("/home")
def home():
    # Default location (Hyderabad)
    lat, lon = 17.3850, 78.4867

    restaurants = get_nearby_restaurants(lat, lon)

    return render_template("home.html", recs=restaurants)


@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")


@app.route("/profile")
def profile():
    email = session.get("email")

    if not email:
        return redirect("/")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT first_name, last_name, age, phone, email
    FROM users WHERE email=?
    """, (email,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return render_template("profile.html", user=None)

    user = {
        "first_name": row[0],
        "last_name": row[1],
        "age": row[2],
        "phone": row[3],
        "email": row[4]
    }

    return render_template("profile.html", user=user)


# ================= SEARCH =================

@app.route("/recommend", methods=["POST"])
def recommend():
    location = request.form.get("location")
    cuisine = request.form.get("cuisine", "Any")
    budget = request.form.get("budget", "Any")
    food_type = request.form.get("food_type", "Any")
    min_rating = float(request.form.get("min_rating", 0))

    lat = request.form.get("lat")
    lon = request.form.get("lon")
    if lat and lon:
        lat = float(lat)
        lon = float(lon)
    else:
        lat, lon = get_lat_lon(location)

    if lat is None:
        return "Invalid location"

    restaurants = get_nearby_restaurants(lat, lon, min_rating)
    for r in restaurants:
        r["clean_rating"] = r.get("rating", 0)
    restaurants = sorted(restaurants, key=lambda x: x["clean_rating"], reverse=True)
    return render_template("results.html",
                       location=location,
                       cuisine=cuisine,
                       budget=budget,
                       food_type=food_type,
                       restaurants=restaurants)


# ================= LOCATION =================

global_restaurants = []


@app.route("/nearby", methods=["POST"])
def nearby():
    global global_restaurants

    data = request.get_json()
    lat = data["latitude"]
    lon = data["longitude"]

    global_restaurants = get_nearby_restaurants(lat, lon)

    return jsonify({"status": "success"})


@app.route("/results_from_location")
def results_from_location():

    global global_restaurants

    # ✅ ADD clean_rating
    for r in global_restaurants:
        r["clean_rating"] = r.get("rating", 0)

    # ✅ SORT restaurants
    global_restaurants = sorted(
        global_restaurants,
        key=lambda x: x["clean_rating"],
        reverse=True
    )

    return render_template("results.html",
                           location="Current Location",
                           cuisine=session.get("cuisine", "Any"),
                           budget=session.get("budget", "Any"),
                           food_type=session.get("food_type", "Any"),
                           restaurants=global_restaurants)


# ================= FAVORITES =================

@app.route("/save_favorite", methods=["POST"])
def save_favorite():
    data = request.get_json()
    email = session.get("email")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM favorites WHERE email=? AND name=? AND address=?
    """, (email, data.get("name"), data.get("address")))

    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO favorites (email, name, address, rating, lat, lon, photo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            email,
            data.get("name"),
            data.get("address"),
            data.get("rating"),
            data.get("lat"),
            data.get("lon"),
            data.get("photo")
        ))

    conn.commit()
    conn.close()

    return jsonify({"status": "saved"})


@app.route("/remove_favorite", methods=["POST"])
def remove_favorite():
    data = request.get_json()
    email = session.get("email")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM favorites 
    WHERE email=? AND name=? AND address=?
    """, (email, data.get("name"), data.get("address")))

    conn.commit()
    conn.close()

    return jsonify({"status": "removed"})


@app.route("/favorites")
def favorites():
    email = session.get("email")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name, address, rating, lat, lon, photo FROM favorites WHERE email=?
    """, (email,))

    rows = cursor.fetchall()
    conn.close()

    restaurants = []

    for r in rows:
        restaurants.append({
            "name": r[0],
            "address": r[1],
            "rating": r[2],
            "lat": r[3],
            "lon": r[4],
            "photo": r[5]
        })

    return render_template("results.html",
                           location="Favorites",
                           cuisine="",
                           budget="",
                           food_type="",
                           restaurants=restaurants)


# ================= AI =================

@app.route("/api_ai_picks")
def api_ai_picks():
    lat, lon = 17.3850, 78.4867

    restaurants = get_nearby_restaurants(lat, lon)

    # ⭐ Apply user preference (basic)
    min_rating = 4 if session.get("ai_enabled") else 0

    filtered = [r for r in restaurants if r["rating"] >= min_rating]

    top_rated = sorted(filtered, key=lambda x: x["rating"], reverse=True)[:5]
    popular = filtered[:5]

    return jsonify({
        "top_rated": top_rated,
        "popular": popular,
        "favorites": []
    })


@app.route("/api_surprise")
def api_surprise():
    lat, lon = 17.3850, 78.4867

    restaurants = get_nearby_restaurants(lat, lon)

    if restaurants:
        return jsonify([random.choice(restaurants)])

    return jsonify([])


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/save_user", methods=["POST"])
def save_user():
    data = request.form
    email = session.get("email")

    if not email:
        return redirect("/")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO users (email, first_name, last_name, age, phone)
    VALUES (?, ?, ?, ?, ?)
    """, (
        email,
        data.get("first_name"),
        data.get("last_name"),
        data.get("age"),
        data.get("phone")
    ))

    conn.commit()
    conn.close()

    return redirect("/home")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def recommend_restaurants():

    restaurants = [
        {"name": "Pizza House", "category": "pizza italian"},
        {"name": "Biryani Hub", "category": "biryani spicy"},
        {"name": "Sweet Shop", "category": "dessert sweets"},
        {"name": "Italian Cafe", "category": "pizza pasta"},
        {"name": "Spicy Biryani", "category": "biryani rice"}
    ]

    # Convert text
    data = [r["category"] for r in restaurants]

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(data)

    similarity = cosine_similarity(vectors)

    # Assume user likes first restaurant
    index = 0  

    scores = list(enumerate(similarity[index]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)

    result = [restaurants[i[0]] for i in scores[1:4]]

    return result


if __name__ == "__main__":
    app.run(debug=True)
