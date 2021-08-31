
from flask import Blueprint
import click
from werkzeug.security import generate_password_hash
from . import db
from .models import User
import sqlite3

seed_db = Blueprint('seed', __name__)

@seed_db.cli.command("create-user")
@click.argument("username")
def init_db(username):
    new_user = User(username=username, api_key="searchapi", password=generate_password_hash("searchapi", method='sha256'))

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

@seed_db.cli.command("build-tables")
def create_tables():
    connection = sqlite3.connect("search.db")

    with connection:
        cursor = connection.cursor()

        cursor.execute("CREATE VIRTUAL TABLE posts USING FTS5(title, description, url, category, published, keywords, h1, h2, h3, h4, h5, h6, length, page_content, incoming_links, outgoing_links, pagerank)")

        cursor.execute("CREATE VIRTUAL TABLE images USING FTS5(post_url, alt_text, image_src, published, md5_checksum, caption, ocr_result)")

        cursor.execute("CREATE TABLE user (id integer primary key, username text, password text, api_key text)")

        cursor.execute("CREATE TABLE crawl_errors (url, status_code, message, discovered, discovered_date)")

        cursor.execute("CREATE TABLE sitemaps (url)")