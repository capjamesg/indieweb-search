from flask import Flask, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

def create_app():
    app = Flask(__name__)

    # Limiter(
    #     app,
    #     key_func=get_remote_address,
    #     default_limits=["200 per day", "50 per hour"]
    # )

    app.config['SECRET_KEY'] = os.urandom(32)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///search.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    from .main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    from .database_methods import database_methods as database_methods_blueprint

    app.register_blueprint(database_methods_blueprint)

    from .stats import stats as stats_blueprint

    app.register_blueprint(stats_blueprint)

    # from werkzeug.middleware.profiler import ProfilerMiddleware
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[5], profile_dir='./profile')

    return app

create_app()