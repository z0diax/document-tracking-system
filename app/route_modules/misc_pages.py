import os
from datetime import datetime
from pathlib import Path

from flask import abort, current_app, jsonify, render_template, request, send_file, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.models import ActivityLog, Document, to_local_time
from app.route_modules.shared import main


@main.route('/overview')
@login_required
def overview():
    current_time = to_local_time(datetime.utcnow())
    return render_template(
        'overview.html',
        title='Overview',
        user_name=current_user.username if current_user.is_authenticated else 'Guest',
        current_time=current_time,
    )


@main.route('/docgen')
@login_required
def docgen_mock():
    """Render mock DocGen dashboard data."""
    mock_stats = {
        'generated_today': 12,
        'awaiting_approval': 5,
        'templates_updated': 8,
        'activity': [
            {'title': 'Procurement Summary - April 04', 'status': 'Completed', 'status_class': 'success'},
            {'title': 'HR Onboarding Packet', 'status': 'Approval Needed', 'status_class': 'warning'},
            {'title': 'Executive Brief - Infrastructure', 'status': 'Drafting', 'status_class': 'secondary'},
        ],
        'team_members': [
            {'name': 'Alex Rivera', 'role': 'Content Strategist'},
            {'name': 'Jamie Cruz', 'role': 'Policy Reviewer'},
            {'name': 'Taylor Gomez', 'role': 'Legal Liaison'},
        ],
    }
    return render_template('docgen_mock.html', title='DocGen (Mock)', mock_stats=mock_stats)


@main.route('/get_document_activities/<int:document_id>')
@login_required
def get_document_activities(document_id):
    """Endpoint to fetch document activities for the admin dashboard modal."""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized access'}), 403

        Document.query.get_or_404(document_id)
        activities = (
            ActivityLog.query
            .filter_by(document_id=document_id)
            .order_by(ActivityLog.timestamp.desc())
            .all()
        )
        activity_dicts = []

        for activity in activities:
            try:
                activity_dicts.append({
                    'id': activity.id,
                    'timestamp': (
                        to_local_time(activity.timestamp).strftime('%B %d, %Y at %I:%M %p')
                        if activity.timestamp else 'Unknown'
                    ),
                    'action': activity.action,
                    'remarks': activity.remarks,
                    'user': {'username': activity.user.username} if activity.user else None,
                })
            except Exception as exc:
                print(f'Error serializing activity {activity.id}: {str(exc)}')
                activity_dicts.append({
                    'id': activity.id,
                    'timestamp': 'Error parsing timestamp',
                    'action': activity.action or 'Unknown action',
                    'remarks': 'Error retrieving details',
                    'user': {'username': 'Unknown'},
                })

        return jsonify({
            'document_id': document_id,
            'activities': activity_dicts,
        })
    except Exception as exc:
        print(f'Error in get_document_activities: {str(exc)}')
        return jsonify({
            'error': 'An error occurred while fetching activities',
            'message': str(exc),
        }), 500


@main.route('/check_barcode', methods=['POST'])
@login_required
def check_barcode():
    """Check if a barcode is available and suggest alternatives if taken."""
    barcode = request.form.get('barcode', '').strip()

    if not barcode:
        return jsonify({
            'valid': False,
            'message': 'Barcode is required',
            'suggestions': [],
        })

    existing_document = Document.query.filter_by(barcode=barcode).first()
    if not existing_document:
        return jsonify({
            'valid': True,
            'message': 'Barcode is available',
            'suggestions': [],
        })

    suggestions = []
    suffixes = ['-A', '-B', '-C', 'A', 'B', 'C', '_1', '_2', '_3']
    for suffix in suffixes:
        suggestion = barcode + suffix
        if not Document.query.filter_by(barcode=suggestion).first():
            suggestions.append(suggestion)
            if len(suggestions) >= 5:
                break

    return jsonify({
        'valid': False,
        'message': 'This barcode is already in use',
        'suggestions': suggestions,
        'document': existing_document.to_dict() if existing_document else None,
    })


@main.route('/uploads/<filename>')
@login_required
def serve_file(filename):
    try:
        safe_filename = secure_filename(filename)
        uploads_dir = os.path.join(current_app.root_path, 'uploads')
        Path(uploads_dir).mkdir(parents=True, exist_ok=True)

        file_path = os.path.join(uploads_dir, safe_filename)
        absolute_path = os.path.abspath(file_path)

        if not absolute_path.startswith(os.path.abspath(uploads_dir)):
            current_app.logger.error(f'Directory traversal attempt: {filename}')
            abort(403)

        if not os.path.isfile(absolute_path):
            current_app.logger.error(f'File not found: {absolute_path}')
            abort(404)

        mime_type = 'application/pdf' if filename.lower().endswith('.pdf') else 'application/octet-stream'
        return send_from_directory(
            directory=uploads_dir,
            path=safe_filename,
            mimetype=mime_type,
            as_attachment=False,
            download_name=safe_filename,
        )
    except Exception as exc:
        current_app.logger.error(f'Error serving file {filename}: {str(exc)}')
        abort(500)


def get_file_download_url(filename):
    """Generate proper URL for file download."""
    if not filename:
        return None
    safe_filename = os.path.basename(secure_filename(filename))
    return url_for('main.serve_file', filename=safe_filename)


@main.route('/favicon.ico')
def favicon():
    try:
        favicon_path = os.path.join(current_app.root_path, 'static', 'favicon.ico')
        if not os.path.exists(favicon_path):
            default_favicon = os.path.join(current_app.root_path, 'static', 'default_favicon.ico')
            return send_file(default_favicon, mimetype='image/x-icon')
        return send_file(favicon_path, mimetype='image/x-icon')
    except Exception as exc:
        current_app.logger.error(f'Error serving favicon: {str(exc)}')
        abort(404)
