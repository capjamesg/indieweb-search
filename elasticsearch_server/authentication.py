from flask import abort

import config


def is_authenticated_check(request):
    # check auth header
    if request.headers.get("Authorization") != "Bearer {}".format(
        config.ELASTICSEARCH_API_TOKEN
    ):
        return abort(401)


def check_password(request):
    # check password
    if request.args.get("pw") != config.ELASTICSEARCH_PASSWORD:
        return abort(401)
