import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration settings."""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'deciphex-content-studio-secret-key-change-in-production')

    # Database settings
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'content_studio.db')

    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'pptx'}

    # OpenAI API settings
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    OPENAI_MODEL = 'gpt-4o'

    # Session settings
    SESSION_TIMEOUT_MINUTES = 60
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour in seconds

    # Default admin credentials (to be changed on first login)
    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'deciphex2025'

    # Available brands
    BRANDS = [
        {'name': 'Deciphex', 'description': 'Main Deciphex brand - AI-powered digital pathology solutions'},
        {'name': 'Diagnexia', 'description': 'Diagnexia brand - Advanced diagnostic platform'},
        {'name': 'Diagnexia Analytix', 'description': 'Diagnexia Analytix - Data analytics and insights'},
        {'name': 'Patholytix', 'description': 'Patholytix brand - Pathology workflow solutions'}
    ]

    # Asset categories
    ASSET_CATEGORIES = ['Internal', 'External']

    # Asset types
    ASSET_TYPES = [
        'Regulatory',
        'Pitch Deck',
        'Feature Description',
        'Release Docs',
        'Call Transcript',
        'Marketing Material',
        'GTM Strategy',
        'Other'
    ]

    # Content types that can be generated
    CONTENT_TYPES = [
        'Brochure',
        'Postcard',
        'Flyer',
        'Conference Backdrop',
        'Email Campaign',
        'Social Media Post',
        'Website Copy',
        'Case Study',
        'White Paper',
        'Data Sheet',
        'Sales One-Pager'
    ]
