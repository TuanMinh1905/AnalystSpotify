import os
from flask_appbuilder.security.manager import AUTH_DB

# Superset specific config
ROW_LIMIT = 5000
SUPERSET_WEBSERVER_PORT = 8088

# Flask App Builder configuration
SECRET_KEY = 'SpotifyBigDataAnalytics2024_minhlong_SecretKey_Random_String_12345'

# The SQLAlchemy connection string to your database backend
# Sử dụng SQLite cho đơn giản
SQLALCHEMY_DATABASE_URI = 'sqlite:////home/hadoopminhquang/superset.db'

# Flask-WTF flag for CSRF
WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = []
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24 * 365

# Set this API key to enable Mapbox visualizations
MAPBOX_API_KEY = ''

# Cấu hình timezone
BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_TIMEZONE = 'Asia/Ho_Chi_Minh'

# Cache configuration
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
}

# Async query configuration  
FEATURE_FLAGS = {
    'ALERT_REPORTS': False,
    'ENABLE_TEMPLATE_PROCESSING': True,
    'DASHBOARD_NATIVE_FILTERS': True,
    'DASHBOARD_CROSS_FILTERS': True,
    'DASHBOARD_RBAC': True,
}

# CORS configuration
ENABLE_CORS = True
CORS_OPTIONS = {
    'supports_credentials': True,
    'allow_headers': ['*'],
    'resources': ['*'],
    'origins': ['*']
}

# Logging configuration
LOG_LEVEL = 'INFO'
ENABLE_TIME_ROTATE = False
LOG_FORMAT = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
LOG_FILE_PATH = '/home/hadoopminhquang/superset_logs/superset.log'

# Security configuration
AUTH_TYPE = AUTH_DB
AUTH_USER_REGISTRATION = False  # Không cho phép user tự đăng ký
AUTH_USER_REGISTRATION_ROLE = 'Public'

# CSV Upload
UPLOAD_FOLDER = '/home/hadoopminhquang/superset_uploads/'
UPLOAD_ALLOWED_EXTENSIONS = {'csv', 'tsv', 'txt', 'json', 'xml', 'parquet'}

# Database configuration
SQLALCHEMY_TRACK_MODIFICATIONS = False
# SQLite không hỗ trợ pool config
# SQLALCHEMY_POOL_SIZE = 5  
# SQLALCHEMY_MAX_OVERFLOW = 10

# Results backend
RESULTS_BACKEND = None

# Web server configuration
SUPERSET_WEBSERVER_TIMEOUT = 60
