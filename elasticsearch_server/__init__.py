import os

from flask import Flask, abort, request, send_from_directory

import config


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.urandom(32)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///search.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    from .main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    from .database_methods import \
        database_methods as database_methods_blueprint

    app.register_blueprint(database_methods_blueprint)

    from .stats import stats as stats_blueprint

    app.register_blueprint(stats_blueprint)

    @app.route("/assets/<path:path>")
    def send_assets(path):
        return send_from_directory("static", path)

    @app.before_request
    def before_request():
        # check auth header
        if request.headers.get("Authorization") == "{}".format(
            config.ELASTICSEARCH_API_TOKEN
        ):
            return

        if request.args.get("pw") == config.ELASTICSEARCH_PASSWORD:
            return

        return abort(401)

    # from werkzeug.middleware.profiler import ProfilerMiddleware
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[5], profile_dir='./profile')

    return app


create_app()
