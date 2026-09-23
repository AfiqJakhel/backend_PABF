from flask import Flask
from config import DevelopmentConfig
from .core.extensions import db, jwt, cors, migrate

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    migrate.init_app(app, db)


    # Root route for API health check
    @app.route('/')
    def index():
        return {"status": "success", "message": "Hello!"}

    return app
