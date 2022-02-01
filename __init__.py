import os

from flask import Flask, render_template

from config import SENTRY_DSN, SENTRY_SERVER_NAME

# set up sentry for error handling
if SENTRY_DSN != "":
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0,
        server_name=SENTRY_SERVER_NAME,
    )


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.urandom(32)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///search.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # blueprint for non-auth parts of app
    from main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("error.html", title="Page Not Found Error"), 404

    @app.errorhandler(500)
    def server_error(e):
        return (
            render_template("error.html", server_error=True, title="Server Error"),
            500,
        )

    @app.errorhandler(429)
    def rate_limit():
        return (
            render_template(
                "error.html", rate_limit_error=True, title="Rate Limit Error"
            ),
            429,
        )

    # from werkzeug.middleware.profiler import ProfilerMiddleware
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[5], profile_dir='./profile')

    return app


create_app()
