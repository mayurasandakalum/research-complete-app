from flask import Flask, render_template
from config import Config
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from kinesthetic.models import User

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize CSRF protection
    csrf.init_app(app)

    # Initialize login manager with correct login view
    login_manager.init_app(app)
    login_manager.login_view = (
        "kinesthetic.login"  # Changed from "login" to "kinesthetic.login"
    )

    from kinesthetic.routes import kinesthetic_blueprint
    from kinesthetic.utils import load_initial_questions

    app.register_blueprint(kinesthetic_blueprint)

    # Load initial questions if they don't exist
    with app.app_context():
        load_initial_questions()

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("error_500.html"), 500

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    return app


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(debug=True)
