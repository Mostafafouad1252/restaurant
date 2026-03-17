"""Application configuration."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "restaurant-secret-key-change-in-production"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(BASE_DIR, "restaurant.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images", "meals")
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 MB max upload
    MEAL_CATEGORIES = ["appetizer", "main", "dessert"]
    ORDER_STATUSES = ["New", "In Preparation", "Delivered"]
