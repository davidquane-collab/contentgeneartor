import os
from datetime import timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash

from config import Config
from utils.database import (
    init_db, verify_user, get_user_by_id, create_user, update_user_password,
    get_all_users, deactivate_user, activate_user,
    get_all_brands, get_brand_by_id, get_asset_count_by_brand,
    add_brand_asset, get_brand_assets, get_asset_by_id, delete_asset,
    add_audience, get_brand_audiences, get_audience_by_id, update_audience, delete_audience,
    save_generated_content, get_content_by_id, update_content_regulatory_flags,
    update_content_design_brief, get_user_content_history,
    log_activity, get_all_activity
)
from utils.file_processor import allowed_file, extract_text, save_uploaded_file, delete_file
from utils.ai_generator import (
    generate_content, run_regulatory_check, generate_design_brief,
    extract_audiences_from_document
)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=Config.SESSION_TIMEOUT_MINUTES)


# Initialize database on startup
with app.app_context():
    init_db()


# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        user = get_user_by_id(session['user_id'])
        if not user or not user['is_admin']:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# Context processor for templates
@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        return {'current_user': user}
    return {'current_user': None}


# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = verify_user(username, password)
        if user:
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])

            log_activity(user['id'], 'login', 'User logged in')

            if user['must_change_password']:
                flash('Please change your password.', 'warning')
                return redirect(url_for('change_password'))

            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_activity(session['user_id'], 'logout', 'User logged out')
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        user = get_user_by_id(session['user_id'])

        if not verify_user(user['username'], current_password):
            flash('Current password is incorrect.', 'danger')
        elif len(new_password) < 8:
            flash('New password must be at least 8 characters.', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
        else:
            update_user_password(session['user_id'], new_password)
            log_activity(session['user_id'], 'password_change', 'User changed password')
            flash('Password changed successfully!', 'success')
            return redirect(url_for('dashboard'))

    return render_template('change_password.html')


@app.route('/dashboard')
@login_required
def dashboard():
    brands = get_all_brands()
    brands_with_stats = []
    for brand in brands:
        asset_count = get_asset_count_by_brand(brand['id'])
        brands_with_stats.append({
            'id': brand['id'],
            'brand_name': brand['brand_name'],
            'description': brand['description'],
            'asset_count': asset_count
        })

    recent_content = get_user_content_history(session['user_id'], limit=5)

    return render_template('dashboard.html',
                           brands=brands_with_stats,
                           recent_content=recent_content)


# Brand Asset Management
@app.route('/brand/<int:brand_id>/assets')
@login_required
def brand_assets(brand_id):
    brand = get_brand_by_id(brand_id)
    if not brand:
        flash('Brand not found.', 'danger')
        return redirect(url_for('dashboard'))

    asset_type_filter = request.args.get('type', None)
    category_filter = request.args.get('category', None)

    assets = get_brand_assets(brand_id, asset_type_filter, category_filter)

    return render_template('brand_assets.html',
                           brand=brand,
                           assets=assets,
                           asset_types=Config.ASSET_TYPES,
                           asset_categories=Config.ASSET_CATEGORIES,
                           current_type=asset_type_filter,
                           current_category=category_filter)


@app.route('/brand/<int:brand_id>/upload', methods=['GET', 'POST'])
@login_required
def upload_asset(brand_id):
    brand = get_brand_by_id(brand_id)
    if not brand:
        flash('Brand not found.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Invalid file type. Allowed: PDF, DOCX, TXT, PPTX', 'danger')
            return redirect(request.url)

        asset_category = request.form.get('asset_category', 'Internal')
        asset_type = request.form.get('asset_type', 'Other')
        description = request.form.get('description', '')

        try:
            # Save file
            file_path, filename = save_uploaded_file(file, brand['brand_name'])

            # Extract text
            extracted_text = extract_text(file_path)

            # Save to database
            asset_id = add_brand_asset(
                brand_id=brand_id,
                file_name=filename,
                file_path=file_path,
                asset_category=asset_category,
                asset_type=asset_type,
                description=description,
                extracted_text=extracted_text,
                uploaded_by=session['user_id']
            )

            log_activity(session['user_id'], 'upload_asset',
                         f'Uploaded {filename} to {brand["brand_name"]}')

            # Extract audiences from marketing materials
            if asset_type == 'Marketing Material' and extracted_text:
                try:
                    audiences, error = extract_audiences_from_document(
                        extracted_text, brand_id, filename
                    )
                    if audiences and not error:
                        for aud in audiences:
                            add_audience(
                                brand_id=brand_id,
                                audience_name=aud.get('name', 'Unknown'),
                                audience_description=aud.get('description', ''),
                                extracted_from=filename
                            )
                        flash(f'Extracted {len(audiences)} audience(s) from document.', 'info')
                except Exception:
                    pass  # Silently fail audience extraction

            flash(f'File "{filename}" uploaded successfully!', 'success')
            return redirect(url_for('brand_assets', brand_id=brand_id))

        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'danger')
            return redirect(request.url)

    return render_template('upload_assets.html',
                           brand=brand,
                           asset_types=Config.ASSET_TYPES,
                           asset_categories=Config.ASSET_CATEGORIES)


@app.route('/asset/<int:asset_id>/download')
@login_required
def download_asset(asset_id):
    asset = get_asset_by_id(asset_id)
    if not asset:
        flash('Asset not found.', 'danger')
        return redirect(url_for('dashboard'))

    if os.path.exists(asset['file_path']):
        return send_file(asset['file_path'], as_attachment=True,
                         download_name=asset['file_name'])
    else:
        flash('File not found on server.', 'danger')
        return redirect(url_for('dashboard'))


@app.route('/asset/<int:asset_id>/delete', methods=['POST'])
@admin_required
def delete_asset_route(asset_id):
    asset = get_asset_by_id(asset_id)
    if not asset:
        return jsonify({'success': False, 'error': 'Asset not found'})

    brand_id = asset['brand_id']

    # Delete file from disk
    delete_file(asset['file_path'])

    # Delete from database
    delete_asset(asset_id)

    log_activity(session['user_id'], 'delete_asset',
                 f'Deleted asset {asset["file_name"]}')

    flash('Asset deleted successfully.', 'success')
    return jsonify({'success': True, 'redirect': url_for('brand_assets', brand_id=brand_id)})


# Content Creation
@app.route('/brand/<int:brand_id>/create', methods=['GET', 'POST'])
@login_required
def create_content(brand_id):
    brand = get_brand_by_id(brand_id)
    if not brand:
        flash('Brand not found.', 'danger')
        return redirect(url_for('dashboard'))

    audiences = get_brand_audiences(brand_id)

    if request.method == 'POST':
        asset_type = request.form.get('asset_type', '')
        audience_id = request.form.get('audience_id', '')
        custom_audience = request.form.get('custom_audience', '')
        additional_context = request.form.get('additional_context', '')

        if not asset_type:
            flash('Please select a content type.', 'danger')
            return redirect(request.url)

        try:
            # Generate content
            content, error = generate_content(
                brand_id=brand_id,
                asset_type=asset_type,
                audience_id=int(audience_id) if audience_id else None,
                custom_audience=custom_audience,
                additional_context=additional_context
            )

            if error:
                flash(f'Error generating content: {error}', 'danger')
                return redirect(request.url)

            # Get audience text for display
            audience_text = custom_audience
            if audience_id:
                aud = get_audience_by_id(int(audience_id))
                if aud:
                    audience_text = aud['audience_name']

            # Save generated content
            content_id = save_generated_content(
                brand_id=brand_id,
                user_id=session['user_id'],
                asset_type=asset_type,
                target_audience=audience_text,
                content=content,
                additional_context=additional_context
            )

            log_activity(session['user_id'], 'generate_content',
                         f'Generated {asset_type} for {brand["brand_name"]}')

            return redirect(url_for('review_content', content_id=content_id))

        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(request.url)

    return render_template('create_content.html',
                           brand=brand,
                           content_types=Config.CONTENT_TYPES,
                           audiences=audiences)


@app.route('/content/<int:content_id>/review')
@login_required
def review_content(content_id):
    content = get_content_by_id(content_id)
    if not content:
        flash('Content not found.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('review_content.html', content=content)


@app.route('/content/<int:content_id>/regulatory-check', methods=['POST'])
@login_required
def regulatory_check(content_id):
    content = get_content_by_id(content_id)
    if not content:
        return jsonify({'success': False, 'error': 'Content not found'})

    try:
        result, error = run_regulatory_check(content['content'], content['brand_id'])

        if error:
            return jsonify({'success': False, 'error': error})

        # Save regulatory flags
        update_content_regulatory_flags(content_id, result)

        log_activity(session['user_id'], 'regulatory_check',
                     f'Ran regulatory check on content {content_id}')

        return jsonify({'success': True, 'result': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/content/<int:content_id>/design-brief', methods=['POST'])
@login_required
def design_brief(content_id):
    content = get_content_by_id(content_id)
    if not content:
        return jsonify({'success': False, 'error': 'Content not found'})

    try:
        brief, error = generate_design_brief(
            content['content'],
            content['asset_type'],
            content['brand_id']
        )

        if error:
            return jsonify({'success': False, 'error': error})

        # Save design brief
        update_content_design_brief(content_id, brief)

        log_activity(session['user_id'], 'design_brief',
                     f'Generated design brief for content {content_id}')

        return jsonify({'success': True, 'result': brief})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# Audience Management
@app.route('/brand/<int:brand_id>/audiences')
@login_required
def brand_audiences(brand_id):
    brand = get_brand_by_id(brand_id)
    if not brand:
        flash('Brand not found.', 'danger')
        return redirect(url_for('dashboard'))

    audiences = get_brand_audiences(brand_id)

    return render_template('audiences.html', brand=brand, audiences=audiences)


@app.route('/brand/<int:brand_id>/audience/add', methods=['POST'])
@login_required
def add_audience_route(brand_id):
    brand = get_brand_by_id(brand_id)
    if not brand:
        return jsonify({'success': False, 'error': 'Brand not found'})

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        return jsonify({'success': False, 'error': 'Name is required'})

    audience_id = add_audience(brand_id, name, description)
    log_activity(session['user_id'], 'add_audience',
                 f'Added audience "{name}" to {brand["brand_name"]}')

    return jsonify({'success': True, 'audience_id': audience_id})


@app.route('/audience/<int:audience_id>/edit', methods=['POST'])
@login_required
def edit_audience(audience_id):
    audience = get_audience_by_id(audience_id)
    if not audience:
        return jsonify({'success': False, 'error': 'Audience not found'})

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        return jsonify({'success': False, 'error': 'Name is required'})

    update_audience(audience_id, name, description)

    return jsonify({'success': True})


@app.route('/audience/<int:audience_id>/delete', methods=['POST'])
@admin_required
def delete_audience_route(audience_id):
    audience = get_audience_by_id(audience_id)
    if not audience:
        return jsonify({'success': False, 'error': 'Audience not found'})

    delete_audience(audience_id)
    log_activity(session['user_id'], 'delete_audience',
                 f'Deleted audience {audience["audience_name"]}')

    return jsonify({'success': True})


# Admin Routes
@app.route('/admin')
@admin_required
def admin_panel():
    users = get_all_users()
    activity = get_all_activity(limit=50)
    brands = get_all_brands()

    brand_stats = []
    for brand in brands:
        assets = get_brand_assets(brand['id'])
        brand_stats.append({
            'name': brand['brand_name'],
            'asset_count': len(assets)
        })

    return render_template('admin.html',
                           users=users,
                           activity=activity,
                           brand_stats=brand_stats)


@app.route('/admin/user/add', methods=['POST'])
@admin_required
def add_user():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    is_admin = request.form.get('is_admin') == 'on'

    if not username or not password:
        flash('Username and password are required.', 'danger')
        return redirect(url_for('admin_panel'))

    if len(password) < 8:
        flash('Password must be at least 8 characters.', 'danger')
        return redirect(url_for('admin_panel'))

    if create_user(username, password, email, is_admin):
        log_activity(session['user_id'], 'create_user', f'Created user {username}')
        flash(f'User "{username}" created successfully!', 'success')
    else:
        flash('Username already exists.', 'danger')

    return redirect(url_for('admin_panel'))


@app.route('/admin/user/<int:user_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_user_route(user_id):
    if user_id == session['user_id']:
        return jsonify({'success': False, 'error': 'Cannot deactivate yourself'})

    deactivate_user(user_id)
    log_activity(session['user_id'], 'deactivate_user', f'Deactivated user {user_id}')

    return jsonify({'success': True})


@app.route('/admin/user/<int:user_id>/activate', methods=['POST'])
@admin_required
def activate_user_route(user_id):
    activate_user(user_id)
    log_activity(session['user_id'], 'activate_user', f'Activated user {user_id}')

    return jsonify({'success': True})


@app.route('/admin/user/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    new_password = request.form.get('password', '')

    if len(new_password) < 8:
        return jsonify({'success': False, 'error': 'Password must be at least 8 characters'})

    update_user_password(user_id, new_password)
    log_activity(session['user_id'], 'reset_password', f'Reset password for user {user_id}')

    return jsonify({'success': True})


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error'), 500


@app.errorhandler(413)
def file_too_large(error):
    flash('File is too large. Maximum size is 50MB.', 'danger')
    return redirect(request.url)


# Ensure upload directory exists (runs on import for gunicorn)
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


if __name__ == '__main__':
    # Run the application (use PORT env var for Render deployment)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug)
