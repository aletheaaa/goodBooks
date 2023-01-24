import os
import requests
import urllib.parse
import sqlite3

from flask import redirect, render_template, request, session
from functools import wraps

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def convert_to_dict(values, headers):
    '''
    this is to convert a list of strings into a dictionary
    '''
    final = []
    # values would look like: [(1, 'x'), (2, 'y')]
    # headers would look like: ['Number', 'Letter1']
    # final will look like: [{'Number': 1, 'Letter1':'x'}, {'Number': 2, 'Letter1':'y'}]
    for i in range(len(values)):
        temp = {}
        for x in range(len(values[i])):
            temp[headers[x]] = values[i][x]
        final.append(temp)
    return final

def convertToBinaryData(filename):
    # Convert digital data to binary format
    with open(filename, 'rb') as file:
        blobData = file.read()
    return blobData

def insertBook(bookName, author, bookCoverPic, description):
    sqliteConnection = sqlite3.connect('user.db')
    cursor = sqliteConnection.cursor()
    print("Connected to SQLite")
    sqlite_insert_blob_query = """ INSERT INTO book
                                (bookName, author, bookCover, description) VALUES (?, ?, ?, ?)"""

    bookCover = convertToBinaryData(bookCoverPic)
    # Convert data into tuple format
    data_tuple = (bookName, author, bookCover, description)
    cursor.execute(sqlite_insert_blob_query, data_tuple)
    sqliteConnection.commit()
    print("Image and file inserted successfully as a BLOB into a table")

def writeTofile(data, filename):
    # Convert binary data to proper format and write it on Hard Disk
    with open(filename, 'wb') as file:
        file.write(data)
    print("Stored blob data into: ", filename, "\n")

def readBlobData(row):
    print("Storing bookCover image on disk \n")
    photoPath = "./static/bookCovers/" + row["bookName"] + ".jpg"
    writeTofile(row["bookCover"], photoPath)
