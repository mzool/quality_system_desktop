# Quality Management System Configuration
# Copy this file to config.py and customize as needed

# Database Configuration
# =====================

# Option 1: SQLite (Default - Single User Desktop)
# No configuration needed - uses ~/.quality_system/quality_system.db

# Option 2: PostgreSQL (Multi-User / Server Deployment)
# Uncomment and configure:
# DATABASE_URL = 'postgresql://username:password@localhost:5432/quality_system'

# Option 3: MySQL (Alternative)
# DATABASE_URL = 'mysql+pymysql://username:password@localhost:3306/quality_system'

# Application Settings
# ====================
APP_NAME = "Quality Management System"
APP_VERSION = "1.0.0"

# Debug Mode
DEBUG = False  # Set to True to enable SQL query logging

# Company Information (Optional - can be set in UI)
# COMPANY_NAME = "Your Company Name"
# COMPANY_LOGO = "/path/to/logo.png"

# File Storage
# ============
# Images and documents storage location
# Default: ~/.quality_system/
# STORAGE_PATH = "/custom/path/for/files"

# Update Server (Optional)
# UPDATE_SERVER_URL = "https://your-server.com/updates"

# Email Notifications (Future Feature)
# EMAIL_ENABLED = False
# EMAIL_HOST = "smtp.gmail.com"
# EMAIL_PORT = 587
# EMAIL_USERNAME = "your-email@example.com"
# EMAIL_PASSWORD = "your-password"
