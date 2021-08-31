from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import click

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )

    app.config['SECRET_KEY'] = 'capjamesgsecretkeysearch555'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///search.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    from .models import User

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .seed import seed_db

    app.register_blueprint(seed_db)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    # import authentication and register as a blueprint
    from .auth import auth as auth_blueprint

    app.register_blueprint(auth_blueprint)

    # import admin views
    from .admin import admin as admin_blueprint

    app.register_blueprint(admin_blueprint)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("error.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", server_error=True), 500

    @app.errorhandler(429)
    def rate_limit():
        return render_template("error.html", rate_limit_error=True), 429

    # from werkzeug.middleware.profiler import ProfilerMiddleware
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[5], profile_dir='./profile')

    return app

create_app()