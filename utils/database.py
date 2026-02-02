import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config


def get_db_connection():
    """Create and return a database connection."""
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with all required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            must_change_password INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create brands table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create brand_assets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brand_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            asset_category TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            description TEXT,
            extracted_text TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER,
            FOREIGN KEY (brand_id) REFERENCES brands(id),
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
    ''')

    # Create audiences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audiences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER NOT NULL,
            audience_name TEXT NOT NULL,
            audience_description TEXT,
            extracted_from TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brand_id) REFERENCES brands(id)
        )
    ''')

    # Create generated_content table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS generated_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            asset_type TEXT NOT NULL,
            target_audience TEXT,
            content TEXT NOT NULL,
            additional_context TEXT,
            regulatory_flags TEXT,
            design_brief TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brand_id) REFERENCES brands(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Create activity_log table for audit trail
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()

    # Initialize default admin user if not exists
    cursor.execute('SELECT id FROM users WHERE username = ?', (Config.DEFAULT_ADMIN_USERNAME,))
    if cursor.fetchone() is None:
        password_hash = generate_password_hash(Config.DEFAULT_ADMIN_PASSWORD)
        cursor.execute('''
            INSERT INTO users (username, password_hash, email, is_admin, must_change_password)
            VALUES (?, ?, ?, 1, 1)
        ''', (Config.DEFAULT_ADMIN_USERNAME, password_hash, 'admin@deciphex.com'))
        conn.commit()

    # Initialize default brands if not exist
    for brand in Config.BRANDS:
        cursor.execute('SELECT id FROM brands WHERE brand_name = ?', (brand['name'],))
        if cursor.fetchone() is None:
            cursor.execute('''
                INSERT INTO brands (brand_name, description)
                VALUES (?, ?)
            ''', (brand['name'], brand['description']))

    conn.commit()
    conn.close()


# User functions
def get_user_by_username(username):
    """Get user by username."""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    """Get user by ID."""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user


def verify_user(username, password):
    """Verify user credentials."""
    user = get_user_by_username(username)
    if user and user['is_active'] and check_password_hash(user['password_hash'], password):
        return user
    return None


def create_user(username, password, email, is_admin=False):
    """Create a new user."""
    conn = get_db_connection()
    try:
        password_hash = generate_password_hash(password)
        conn.execute('''
            INSERT INTO users (username, password_hash, email, is_admin)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, email, 1 if is_admin else 0))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_user_password(user_id, new_password):
    """Update user password."""
    conn = get_db_connection()
    password_hash = generate_password_hash(new_password)
    conn.execute('''
        UPDATE users SET password_hash = ?, must_change_password = 0
        WHERE id = ?
    ''', (password_hash, user_id))
    conn.commit()
    conn.close()


def get_all_users():
    """Get all users."""
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return users


def deactivate_user(user_id):
    """Deactivate a user."""
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()


def activate_user(user_id):
    """Activate a user."""
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_active = 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()


# Brand functions
def get_all_brands():
    """Get all brands."""
    conn = get_db_connection()
    brands = conn.execute('SELECT * FROM brands ORDER BY brand_name').fetchall()
    conn.close()
    return brands


def get_brand_by_id(brand_id):
    """Get brand by ID."""
    conn = get_db_connection()
    brand = conn.execute('SELECT * FROM brands WHERE id = ?', (brand_id,)).fetchone()
    conn.close()
    return brand


def get_brand_by_name(brand_name):
    """Get brand by name."""
    conn = get_db_connection()
    brand = conn.execute('SELECT * FROM brands WHERE brand_name = ?', (brand_name,)).fetchone()
    conn.close()
    return brand


# Asset functions
def add_brand_asset(brand_id, file_name, file_path, asset_category, asset_type, description, extracted_text, uploaded_by):
    """Add a new brand asset."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO brand_assets (brand_id, file_name, file_path, asset_category, asset_type, description, extracted_text, uploaded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (brand_id, file_name, file_path, asset_category, asset_type, description, extracted_text, uploaded_by))
    conn.commit()
    asset_id = cursor.lastrowid
    conn.close()
    return asset_id


def get_brand_assets(brand_id, asset_type=None, asset_category=None):
    """Get assets for a brand, optionally filtered."""
    conn = get_db_connection()
    query = 'SELECT * FROM brand_assets WHERE brand_id = ?'
    params = [brand_id]

    if asset_type:
        query += ' AND asset_type = ?'
        params.append(asset_type)

    if asset_category:
        query += ' AND asset_category = ?'
        params.append(asset_category)

    query += ' ORDER BY upload_date DESC'
    assets = conn.execute(query, params).fetchall()
    conn.close()
    return assets


def get_asset_by_id(asset_id):
    """Get asset by ID."""
    conn = get_db_connection()
    asset = conn.execute('SELECT * FROM brand_assets WHERE id = ?', (asset_id,)).fetchone()
    conn.close()
    return asset


def delete_asset(asset_id):
    """Delete an asset."""
    conn = get_db_connection()
    conn.execute('DELETE FROM brand_assets WHERE id = ?', (asset_id,))
    conn.commit()
    conn.close()


def get_asset_count_by_brand(brand_id):
    """Get the count of assets for a brand."""
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) as count FROM brand_assets WHERE brand_id = ?', (brand_id,)).fetchone()
    conn.close()
    return count['count'] if count else 0


# Audience functions
def add_audience(brand_id, audience_name, audience_description, extracted_from=None):
    """Add a new audience."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audiences (brand_id, audience_name, audience_description, extracted_from)
        VALUES (?, ?, ?, ?)
    ''', (brand_id, audience_name, audience_description, extracted_from))
    conn.commit()
    audience_id = cursor.lastrowid
    conn.close()
    return audience_id


def get_brand_audiences(brand_id):
    """Get all audiences for a brand."""
    conn = get_db_connection()
    audiences = conn.execute('''
        SELECT * FROM audiences WHERE brand_id = ? ORDER BY audience_name
    ''', (brand_id,)).fetchall()
    conn.close()
    return audiences


def get_audience_by_id(audience_id):
    """Get audience by ID."""
    conn = get_db_connection()
    audience = conn.execute('SELECT * FROM audiences WHERE id = ?', (audience_id,)).fetchone()
    conn.close()
    return audience


def update_audience(audience_id, audience_name, audience_description):
    """Update an audience."""
    conn = get_db_connection()
    conn.execute('''
        UPDATE audiences SET audience_name = ?, audience_description = ?
        WHERE id = ?
    ''', (audience_name, audience_description, audience_id))
    conn.commit()
    conn.close()


def delete_audience(audience_id):
    """Delete an audience."""
    conn = get_db_connection()
    conn.execute('DELETE FROM audiences WHERE id = ?', (audience_id,))
    conn.commit()
    conn.close()


# Generated content functions
def save_generated_content(brand_id, user_id, asset_type, target_audience, content, additional_context=None):
    """Save generated content."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO generated_content (brand_id, user_id, asset_type, target_audience, content, additional_context)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (brand_id, user_id, asset_type, target_audience, content, additional_context))
    conn.commit()
    content_id = cursor.lastrowid
    conn.close()
    return content_id


def get_content_by_id(content_id):
    """Get generated content by ID."""
    conn = get_db_connection()
    content = conn.execute('''
        SELECT gc.*, b.brand_name, u.username
        FROM generated_content gc
        JOIN brands b ON gc.brand_id = b.id
        JOIN users u ON gc.user_id = u.id
        WHERE gc.id = ?
    ''', (content_id,)).fetchone()
    conn.close()
    return content


def update_content_regulatory_flags(content_id, regulatory_flags):
    """Update regulatory flags for content."""
    conn = get_db_connection()
    conn.execute('''
        UPDATE generated_content SET regulatory_flags = ?
        WHERE id = ?
    ''', (regulatory_flags, content_id))
    conn.commit()
    conn.close()


def update_content_design_brief(content_id, design_brief):
    """Update design brief for content."""
    conn = get_db_connection()
    conn.execute('''
        UPDATE generated_content SET design_brief = ?
        WHERE id = ?
    ''', (design_brief, content_id))
    conn.commit()
    conn.close()


def get_user_content_history(user_id, limit=20):
    """Get content generation history for a user."""
    conn = get_db_connection()
    content = conn.execute('''
        SELECT gc.*, b.brand_name
        FROM generated_content gc
        JOIN brands b ON gc.brand_id = b.id
        WHERE gc.user_id = ?
        ORDER BY gc.created_at DESC
        LIMIT ?
    ''', (user_id, limit)).fetchall()
    conn.close()
    return content


def get_brand_content_stats(brand_id):
    """Get content generation statistics for a brand."""
    conn = get_db_connection()
    stats = conn.execute('''
        SELECT asset_type, COUNT(*) as count
        FROM generated_content
        WHERE brand_id = ?
        GROUP BY asset_type
    ''', (brand_id,)).fetchall()
    conn.close()
    return stats


# Activity log functions
def log_activity(user_id, action, details=None):
    """Log user activity."""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO activity_log (user_id, action, details)
        VALUES (?, ?, ?)
    ''', (user_id, action, details))
    conn.commit()
    conn.close()


def get_user_activity(user_id, limit=50):
    """Get activity log for a user."""
    conn = get_db_connection()
    activity = conn.execute('''
        SELECT * FROM activity_log
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit)).fetchall()
    conn.close()
    return activity


def get_all_activity(limit=100):
    """Get all activity log entries."""
    conn = get_db_connection()
    activity = conn.execute('''
        SELECT al.*, u.username
        FROM activity_log al
        JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return activity
