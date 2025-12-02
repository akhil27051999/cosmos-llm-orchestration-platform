from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .logger import setup_logger

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=None):
    app = Flask(__name__)
    
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object('app.config.Config')
    
    # Set up the dedicated student logger
    student_logger = setup_logger()
    
    # Attach handlers and level to Flask's native logger to ensure all logs write to the same file
    app.logger.handlers = student_logger.handlers[:]
    app.logger.setLevel(student_logger.level)
    app.logger.propagate = False  # Prevent double logging

    app.logger.info("Student Management API started successfully.")

    # init db & migrations
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from . import models
    
    from .routes import student_bp
    app.register_blueprint(student_bp, url_prefix='/students')
    
    @app.route('/')
    def home():
        app.logger.info("Home page accessed")
        return "Welcome to the Student Management API!"
    
    @app.route('/health')
    def health():
        app.logger.info("Health check accessed")
        return jsonify({"status": "ok"}), 200
    
    return app
