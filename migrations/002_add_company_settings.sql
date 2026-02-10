-- ============================================================================
-- ADD COMPANY SETTINGS TABLE
-- Migration 002: Add company branding and settings
-- ============================================================================

CREATE TABLE IF NOT EXISTS company_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name VARCHAR(255) NOT NULL,
    company_logo BLOB,
    logo_filename VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    phone VARCHAR(50),
    fax VARCHAR(50),
    email VARCHAR(255),
    website VARCHAR(255),
    registration_number VARCHAR(100),
    tax_id VARCHAR(100),
    certification_info TEXT,
    date_format VARCHAR(50) DEFAULT 'YYYY-MM-DD',
    timezone VARCHAR(100) DEFAULT 'UTC',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by_id INTEGER,
    FOREIGN KEY (updated_by_id) REFERENCES users(id)
);

-- Note: This table should only have one row (singleton pattern)
-- The application will manage this automatically
