import os
import string
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, convert_to_dict, insertBook, readBlobData

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# connecting to sqlite3 database
try:
    sqliteConnection = sqlite3.connect('user.db', check_same_thread=False)
    db = sqliteConnection.cursor()
except sqlite3.Error as error:
    print("Error while connecting to sqlite", error)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """page that first appears when visting the site (before logging in)"""
    checkExist = db.execute("SELECT * FROM book").fetchall()
    if len(checkExist) == 0:
        # inserting data into database
        insertBook("Denial of Death", "Ernest Becker", "./static/bookCovers/Denial of Death.jpg", "A book that discusses about the psychological and philosophical implications of how people and cultures have reacted to the concept of death.")
        insertBook("All the Light We Cannot See", "Anthony Doerr", "./static/bookCovers/All the Light We Cannot See.jpg", "A stunningly beautiful instant New York Times bestseller about a blind French girl and a German boy whose paths collide in occupied France as both try to survive the devastation of World War II.")
        insertBook("The Social Contract", "Jean-Jacques Rousseau", "./static/bookCovers/The Social Contract.jpg", "A book that discusses about the issues of liberty and law, freedom and justice, arriving at a view of society that has seemed to some a blueprint for totalitarianism, to others a declaration of democratic principles.")
        insertBook("Jane Eyre", "Charlotte Bronte", "./static/bookCovers/Jane Eyre.jpg", "An unconventional love story that broadened the scope of romantic fiction, Jane Eyre is ultimately the tale of one woman’s fight to claim her independence and self-respect in a society that has no place for her.")

    rows = db.execute("SELECT * FROM book").fetchmany(3)
    cursor = sqliteConnection.execute('select * from book')
    headers = list(map(lambda x: x[0], cursor.description))  # headers will be a list of headers of the table
    rows_dict = convert_to_dict(rows, headers)
    for row in rows_dict:
        readBlobData(row)
    return render_template("intro.html", rows=rows_dict)

@app.route("/book", methods=["GET", "POST"])
def book():
    """when user clicks on the hyperlinks of specific books"""
    errorMsg=""
    if request.method == "POST":
        # checking if user signed in
        try:
            session["user_id"]
            # checking if review is empty
            if (request.form.get("comment") == ""):
                errorMsg="Please enter a review first!"
            else:
                # inserting review into database
                data = (session["user_id"], request.args["bookId"], session["email"], request.form.get("comment"))
                db.execute("INSERT INTO userBooks (userId, bookId, email, comment) VALUES (?,?,?,?)", data)
                sqliteConnection.commit()
        except:
            errorMsg="Log in / register for an account first!"

    # the specific from book table
    rows = db.execute("SELECT * from book WHERE bookId=?", (request.args["bookId"],)).fetchmany(1)
    cursor = sqliteConnection.execute('select * from book')
    headers = list(map(lambda x: x[0], cursor.description))  # headers will be a list of headers of the table
    rows_dict = convert_to_dict(rows, headers)
    for row in rows_dict:
        readBlobData(row)

    # the logged in user's comments for the book
    try:
        session["user_id"]
        comments = db.execute("SELECT * from userBooks WHERE bookId=? AND userId=?", (request.args["bookId"],session["user_id"])).fetchall()
        cursor = sqliteConnection.execute('select * from userBooks')
        headers = list(map(lambda x: x[0], cursor.description))  # headers will be a list of headers of the table
        user_comments_dict = convert_to_dict(comments, headers)
        other_comments = db.execute("SELECT * from userBooks WHERE bookId=? AND NOT userId=?", (request.args["bookId"],session["user_id"])).fetchall()
    except:
        user_comments_dict = []
        other_comments = db.execute("SELECT * from userBooks WHERE bookId=?", (request.args["bookId"],)).fetchall()

    # other peoples' comments
    if (other_comments != []):
        cursor = sqliteConnection.execute('select * from userBooks')
        headers = list(map(lambda x: x[0], cursor.description))  # headers will be a list of headers of the table
        other_comments_dict = convert_to_dict(other_comments, headers)
    else:
        other_comments_dict = []

    try:
        session["email"]
        user_email=session["email"]
    except:
        user_email = ""

    if (errorMsg != ""):
        return render_template("book.html", book=rows_dict[0], user_comments=user_comments_dict, user_email=user_email, other_comments=other_comments_dict, errorMsg=errorMsg)
    else:
        return render_template("book.html", book=rows_dict[0], user_comments=user_comments_dict, user_email=user_email, other_comments=other_comments_dict, errorMsg="")


@app.route("/discover")
def home():
    """page when the user wants to look at the book repository"""
    rows = db.execute("SELECT * FROM book").fetchall()
    cursor = sqliteConnection.execute('select * from book')
    headers = list(map(lambda x: x[0], cursor.description))  # headers will be a list of headers of the table
    rows_dict = convert_to_dict(rows, headers)
    for row in rows_dict:
        readBlobData(row)
    return render_template("discover.html", rows=rows_dict)


@app.route("/homepage")
@login_required
def homepage():
    """homepage when the user logs in"""
    books = db.execute("SELECT DISTINCT book.bookId, book.bookName FROM userBooks INNER JOIN book ON book.bookId=userBooks.bookId WHERE userId = ?", (session["user_id"],)).fetchall()
    return render_template("home.html", books=books)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure email was submitted
        if not request.form.get("email"):
            return render_template("login.html", errorMsg="Please provide your email")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", errorMsg="Please provide your password")

        # Query database for email
        rows = db.execute("SELECT * FROM account WHERE email = ?", (request.form.get("email"),)).fetchall()

        # Ensure email exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return render_template("login.html", errorMsg="Invalid email and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0][0]
        session["email"] = rows[0][1]

        # Redirect user to home page
        return redirect("/homepage")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html", errorMsg="")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # the email and/or password field is empty
        if not request.form.get("password") or not request.form.get("email") or not request.form.get("confirmation"):
            return render_template("register.html", errorMsg="All fields must be filled in")

        # the email is already taken
        email = db.execute("SELECT * FROM account WHERE email=?", (request.form.get("email"),)).fetchall()
        if email:
            return render_template("register.html", errorMsg="Email is already taken")

        # passwords do not match
        if request.form.get("password") != request.form.get("confirmation"):
            return render_template("register.html", errorMsg="The passwords do not match")

        # checking the password. Require users’ passwords to have some number of letters, numbers, and/or symbols
        condition = []
        special = string.punctuation
        for char in request.form.get("password"):
            if char.isalpha() and "alpha" not in condition:
                condition.append("alpha")
            if char.isdigit() and "digit" not in condition:
                condition.append("digit")
            if char in special and "special" not in condition:
                condition.append("special")
        if len(condition) != 3:
            return render_template("register.html", errorMsg="Your password needs to include at least one letter, number and symbol")
        if len(request.form.get("password")) < 5:
            return render_template("register.html", errorMsg="Your password needs to be at least 6 characters long")

        # insert user data into the database
        hashed = generate_password_hash(request.form.get("password"))
        data = (request.form.get("email"), hashed)
        db.execute("INSERT INTO account (email, password) VALUES (?,?)", data)
        sqliteConnection.commit()

        # logging user into the website
        rows = db.execute("SELECT userId FROM account WHERE email=(?)", (request.form.get("email"),)).fetchall()
        session["user_id"] = rows[0][0]
        session["email"] = request.form.get("email")
        return redirect("/homepage")

    else:  # if the user has reached here via GET (show them the form)
        return render_template("register.html", errorMsg="")
