# =============================================================================
# PLACIFY - CONFIGURATION
# File: config.py
# =============================================================================
# SYLLABUS MAPPING: Configuration management, Environment variables
# =============================================================================

import os
from dotenv import load_dotenv

# Load environment variables from .env file (if exists)
load_dotenv()


class Config:
    """Base configuration class with common settings."""
    
    # =============================================================================
    # FLASK SETTINGS
    # =============================================================================
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cpms-secret-key-change-in-production-2026'
    
    # Session configuration
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # =============================================================================
    # MYSQL DATABASE CONFIGURATION
    # =============================================================================
    
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE') or 'campus_placement'
    
    # Connection pool settings (SYLLABUS: Connection Pooling)
    MYSQL_POOL_SIZE = int(os.environ.get('MYSQL_POOL_SIZE') or 5)
    MYSQL_POOL_NAME = 'placify_pool'
    
    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # =============================================================================
    # CORS SETTINGS (for API access from frontend)
    # =============================================================================
    
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_HEADERS = ['Content-Type', 'Authorization']
    
    # =============================================================================
    # LOGGING SETTINGS
    # =============================================================================
    
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'placify.log'


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False
    
    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    
    # Production security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes in production
    PREFERRED_URL_SCHEME = 'https'
    
    # Stricter CORS in production
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
    
    # Production database (use individual env vars OR DATABASE_URL)
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    if DATABASE_URL and DATABASE_URL.startswith('mysql'):
        from urllib.parse import urlparse as _urlparse
        _parsed = _urlparse(DATABASE_URL)
        MYSQL_HOST = _parsed.hostname
        MYSQL_PORT = _parsed.port or 3306
        MYSQL_USER = _parsed.username
        MYSQL_PASSWORD = _parsed.password
        MYSQL_DATABASE = (_parsed.path or '/campus_placement').lstrip('/')
    else:
        MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
        MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)
        MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
        MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''
        MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE') or 'campus_placement'
    
    # Larger pool for production
    MYSQL_POOL_SIZE = int(os.environ.get('MYSQL_POOL_SIZE') or 5)
    
    # Vercel serverless: uploads go to /tmp (ephemeral)
    if os.environ.get('VERCEL'):
        UPLOAD_FOLDER = '/tmp/placify_uploads'
        SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing environment configuration."""
    DEBUG = True
    TESTING = True
    
    # Use test database
    MYSQL_DATABASE = 'campus_placement_test'
    
    # Smaller pool for testing
    MYSQL_POOL_SIZE = 2
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False


# =============================================================================
# CLOUD DEPLOYMENT CONFIGURATIONS
# =============================================================================

class RailwayConfig(ProductionConfig):
    """Configuration for Railway deployment."""
    
    # Railway provides DATABASE_URL in format:
    # mysql://user:password@host:port/database
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL and DATABASE_URL.startswith('mysql://'):
        # Parse DATABASE_URL
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)
        
        MYSQL_HOST = parsed.hostname
        MYSQL_PORT = parsed.port or 3306
        MYSQL_USER = parsed.username
        MYSQL_PASSWORD = parsed.password
        MYSQL_DATABASE = parsed.path[1:]  # Remove leading /


class RenderConfig(ProductionConfig):
    """Configuration for Render deployment."""
    
    # Render also provides DATABASE_URL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)
        
        MYSQL_HOST = parsed.hostname
        MYSQL_PORT = parsed.port or 3306
        MYSQL_USER = parsed.username
        MYSQL_PASSWORD = parsed.password
        MYSQL_DATABASE = parsed.path[1:]


# =============================================================================
# CONFIGURATION DICTIONARY
# =============================================================================

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'railway': RailwayConfig,
    'render': RenderConfig,
    'default': DevelopmentConfig
}


# =============================================================================
# CONFIGURATION GETTER
# =============================================================================

def get_config(env: str = None) -> type:
    """
    Get configuration based on environment.
    Auto-detects Vercel deployment via VERCEL env variable.
    """
    if env is None:
        # Auto-detect Vercel
        if os.environ.get('VERCEL'):
            env = 'production'
        else:
            env = os.environ.get('FLASK_ENV', 'development')
    
    return config.get(env, config['default'])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_database_url() -> str:
    """
    Get formatted database URL for connection.
    
    Returns:
        Database URL string
    """
    cfg = get_config()
    return f"mysql://{cfg.MYSQL_USER}:{cfg.MYSQL_PASSWORD}@{cfg.MYSQL_HOST}:{cfg.MYSQL_PORT}/{cfg.MYSQL_DATABASE}"


def print_config():
    """Print current configuration (for debugging)."""
    cfg = get_config()
    
    print("=" * 60)
    print("PLACIFY CONFIGURATION")
    print("=" * 60)
    print(f"Environment     : {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Debug Mode      : {cfg.DEBUG}")
    print(f"Testing Mode    : {cfg.TESTING}")
    print("-" * 60)
    print("DATABASE:")
    print(f"  Host          : {cfg.MYSQL_HOST}")
    print(f"  Port          : {cfg.MYSQL_PORT}")
    print(f"  User          : {cfg.MYSQL_USER}")
    print(f"  Database      : {cfg.MYSQL_DATABASE}")
    print(f"  Pool Size     : {cfg.MYSQL_POOL_SIZE}")
    print("-" * 60)
    print("SESSION:")
    print(f"  Secure Cookie : {cfg.SESSION_COOKIE_SECURE}")
    print(f"  HTTP Only     : {cfg.SESSION_COOKIE_HTTPONLY}")
    print(f"  Same Site     : {cfg.SESSION_COOKIE_SAMESITE}")
    print("=" * 60)


if __name__ == '__main__':
    # Print configuration when run directly
    print_config()
