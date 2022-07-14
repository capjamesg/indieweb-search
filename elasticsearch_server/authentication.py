from flask import abort, request

import config

# from __init__ import app


def is_authenticated_check(r):
    pass
    # with app.app_context():
    #     # check auth header
    #     if request.headers.get("Authorization") != "Bearer {}".format(
    #         config.ELASTICSEARCH_API_TOKEN
    #     ):
    #         return abort(401)


def check_password(r):
    pass
    # with app.app_context():
    #     # check password
    #     if request.args.get("pw") != config.ELASTICSEARCH_PASSWORD:
    #         return abort(401)
