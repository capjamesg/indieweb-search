from flask import Blueprint, Flask, flash, redirect, render_template, request
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from . import db
from .models import User

auth = Blueprint("auth", __name__, static_folder="static", static_url_path="")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        # check if the user actually exists
        # take the user-supplied password, hash it, and compare it to the hashed password in the database
        if not user or not check_password_hash(user.password, password):
            flash("Please check your login details and try again.")
            return redirect(
                "/login"
            )  # if the user doesn"t exist or password is wrong, reload the page

        # if the above check passes, then we know the user has the right credentials
        login_user(user, remember=True)

        return redirect("/log")
    else:
        if current_user.is_authenticated:
            return redirect("/log")

        return render_template(
            "admin/auth.html", title="Log In | James' Coffee Blog Search"
        )


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")
