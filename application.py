import os

from flask import Flask, session, render_template, request, escape, jsonify, json
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests

app = Flask(__name__)
app.secret_key = 'jg7g780u;jhv3#454*6'

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
KEY = os.getenv("KEY")

# Initialization of hompage
@app.route("/")
def index():
    if 'username' in session:
        username = session['username']
        message = "{} is logged in".format(username)
        return render_template("index.html", message = message)
    return render_template("index.html")

# Register new user
@app.route("/create")
def create():
    return render_template("sign_up.html")

# Sign in existing user
@app.route("/incumbent")
def incumbent():
    return render_template("sign_in.html")

# Take to search page
@app.route("/query")
def query():
    return render_template("search.html")

# Function for handling new users and making sure account
# does not already exist
@app.route("/signup", methods = ["POST"])
def signup():
    """signup for an account"""

    user_name = request.form['username']
    pass_word = request.form['password']
    repeat = request.form['psw-repeat']
    person = db.execute("SELECT username FROM people WHERE username = :username", {"username": user_name}).fetchone()
    secret = db.execute("SELECT password FROM people WHERE password = :password", {"password": pass_word}).fetchone()
    if person is not None:
        return render_template("error.html", message="Name already exists")
    elif person is None and pass_word == repeat:
        db.execute("INSERT into people(username, password) VALUES(:username, :password)", {"username": user_name, "password": pass_word})
        db.commit()
    return render_template("sign_in.html")

# Login users who already have accounts
@app.route("/signin", methods = ["POST"])
def signin():
    """signin to account"""

    user_name = request.form['username']
    pass_word = request.form['password']
    person = db.execute("SELECT username FROM people WHERE username = :username", {"username": user_name}).fetchone()
    secret = db.execute("SELECT password FROM people WHERE password = :password", {"password": pass_word}).fetchone()
    if user_name == person[0] and pass_word == secret[0]:
        session['username'] = user_name
        return render_template("search.html")
    else:
        return render_template("error.html", message= "Invalid login. Try again")

# Allow for the ability to log user out of session from the
# search page.
@app.route("/search")
def logout():
    session.pop('username', None)
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search():
    """Lookup information about book"""

    name = request.form['search']
    detail = '{}%'.format(name)

    if name == '':
        return render_template("search.html")

    queries = db.execute('SELECT * FROM books WHERE isbn ILIKE :name OR title ILIKE :name OR author ILIKE :name OR year ILIKE :name', {"name": detail}).fetchall()

    if len(queries) == 0:
        return render_template("search.html", message="No matches found")
    else:
        return render_template("search.html", queries=queries)

@app.route("/search/<info>", methods=["GET", "POST"])
def page(info):

    """Show details of chosen book and leave a review"""
    key = KEY
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": info})
    if res.status_code != 200:
      raise Exception("ERROR: API request unsuccessful.")

    about = db.execute("SELECT * FROM books WHERE isbn = :id", {"id": info}).fetchone()
    data = res.json()
    count = data["books"][0]["work_ratings_count"]
    average = data["books"][0]["average_rating"]

    username = session['username']
    rating = request.form.get('rating')
    review = request.form.get('review')

    if request.method == "POST":
        book = db.execute("SELECT title FROM books WHERE isbn = :isbn", {"isbn": info}).fetchone()
        db.execute("INSERT into reviews(name, rating, isbn, book, review) VALUES(:name, :rating, :isbn, :book, :review)", {"name":username, "rating": rating, "isbn": info, "book": book[0], "review": review})
        db.commit()

    if about is None:
        return render_template("search.html", message="No matches found")
    reviews = db.execute("SELECT * FROM reviews WHERE isbn = :info", {"info": info}).fetchall()
    return render_template("page.html", about = about, count= count, average=average, reviews = reviews)

#Creates api for users of website to obtain
@app.route("/api/<info>")
def api(info):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": info}).fetchone()
    review = db.execute("SELECT rating FROM reviews WHERE isbn = :isbn", {"isbn": info}).fetchall()

    isbn10 = " "
    title = " "
    author = " "
    year = " "
    count = 0
    average = 0

    if book is None and review is None:
        return jsonify({"error": "Invalid isbn"}), 404
    elif book is not None and review is not None:
        isbn10 = book[0]
        title = book[1]
        author = book[2]
        year = book[3]
        count = len(review)
        for rev in review:
            average = average + rev[0]
        if count != 0:
            average = average/count
        else:
            average = 0

    return jsonify({
                  "isbn": isbn10,
                  "title": title,
                  "author": author,
                  "year": year,
                  "review_count": count,
                  "average_score": average
                    })
