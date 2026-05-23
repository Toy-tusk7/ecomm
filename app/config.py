import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Secret key for signing session cookies
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-this-in-production-123456789')
    
    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads directory
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    
    # Max file upload size (16MB)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
