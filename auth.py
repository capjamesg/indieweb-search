import base64
import hashlib
import random
import string

import indieweb_utils
import requests
from flask import Blueprint, flash, redirect, render_template, request, session

from config import CALLBACK_URL, CLIENT_ID, ME

auth = Blueprint("auth", __name__)


@auth.route("/callback")
def indieauth_callback_handler_view():
    code = request.args.get("code")
    state = request.args.get("state")

    # these are the scopes necessary for the application to run
    required_scopes = ["read", "channels"]

    message, response = indieweb_utils.indieauth_callback_handler(
        code,
        state,
        session.get("token_endpoint"),
        session["code_verifier"],
        session.get("state"),
        ME,
        CALLBACK_URL,
        CLIENT_ID,
        required_scopes,
    )

    if message is not None:
        flash(message)
        return redirect("/login")

    session.pop("code_verifier")

    session["me"] = response.get("me")
    session["access_token"] = response.get("access_token")
    session["scopes"] = response.get("scope", "")

    session.permanent = True

    return redirect("/")


@auth.route("/logout")
def logout():
    session.pop("me")
    session.pop("access_token")

    return redirect("/login")


@auth.route("/login", methods=["GET"])
def login():
    return render_template("authentication/auth.html", title="IndieWeb Search Login")


@auth.route("/discover", methods=["POST"])
def discover_auth_endpoint():
    domain = request.form.get("me")

    headers_to_find = [
        "authorization_endpoint",
        "token_endpoint",
    ]

    headers = indieweb_utils.discover_endpoints(domain, headers_to_find)

    if not headers.get("authorization_endpoint"):
        flash(
            "A valid IndieAuth authorization endpoint could not be found on your website."
        )
        return redirect("/login")

    if not headers.get("token_endpoint"):
        flash("A valid IndieAuth token endpoint could not be found on your website.")
        return redirect("/login")

    authorization_endpoint = headers.get("authorization_endpoint")
    token_endpoint = headers.get("token_endpoint")

    random_code = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(30)
    )

    session["code_verifier"] = random_code
    session["authorization_endpoint"] = authorization_endpoint
    session["token_endpoint"] = token_endpoint

    sha256_code = hashlib.sha256(random_code.encode("utf-8")).hexdigest()

    code_challenge = base64.b64encode(sha256_code.encode("utf-8")).decode("utf-8")

    state = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
    )

    session["state"] = state

    return redirect(
        authorization_endpoint
        + "?client_id="
        + CLIENT_ID
        + "&redirect_uri="
        + CALLBACK_URL
        + "&scope=profile&response_type=code&code_challenge="
        + code_challenge
        + "&code_challenge_method=S256&state="
        + state
    )
