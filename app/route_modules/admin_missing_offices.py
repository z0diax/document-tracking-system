from datetime import datetime, timedelta

from flask import current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app import db
from app.models import Document, format_timestamp
from app.route_modules.shared import OFFICE_CHOICES, main


def _parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except Exception:
        return None


def _resolve_date_window():
    date_from_str = (request.args.get('date_from') or '').strip()
    date_to_str = (request.args.get('date_to') or '').strip()
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    start_dt = None
    end_dt = None

    if date_from_str or date_to_str:
        date_from = _parse_date(date_from_str)
        date_to = _parse_date(date_to_str)
        if date_from and date_to:
            start_dt = datetime(date_from.year, date_from.month, date_from.day)
            end_dt = datetime(date_to.year, date_to.month, date_to.day) + timedelta(days=1)
    elif month and year:
        try:
            start_dt = datetime(year, month, 1)
            end_dt = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
        except Exception:
            start_dt = None
            end_dt = None

    return {
        'date_from': date_from_str,
        'date_to': date_to_str,
        'month': month,
        'year': year,
        'start_dt': start_dt,
        'end_dt': end_dt,
    }


@main.route('/admin/missing-offices')
@login_required
def admin_missing_offices():
    """Return office-level status (has/no records) for a selected classification."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    classification = (request.args.get('classification') or '').strip()
    if not classification:
        return jsonify({'error': 'Classification is required.'}), 400

    window = _resolve_date_window()
    start_dt = window['start_dt']
    end_dt = window['end_dt']
    offices = [choice[0] for choice in OFFICE_CHOICES]

    try:
        office_rows = (
            db.session.query(Document.office, db.func.count(Document.id))
            .filter(
                Document.classification.ilike(f'{classification}%'),
                Document.office.isnot(None),
                Document.timestamp >= start_dt if start_dt else True,
                Document.timestamp < end_dt if end_dt else True,
            )
            .group_by(Document.office)
            .all()
        )
        counts_map = {row[0]: int(row[1]) for row in office_rows if row[0]}
    except Exception as exc:
        try:
            current_app.logger.error('Missing office report error: %s', exc)
        except Exception:
            pass
        return jsonify({'error': 'Unable to generate report.'}), 500

    rows = []
    total_with_records = 0
    for office in offices:
        count = counts_map.get(office, 0)
        has_record = count > 0
        if has_record:
            total_with_records += 1
        rows.append({
            'office': office,
            'status': 'Has Record' if has_record else 'No Records',
            'has_record': has_record,
            'count': count,
        })

    for office, count in counts_map.items():
        if office not in offices:
            total_with_records += 1
            rows.append({
                'office': office,
                'status': 'Has Record',
                'has_record': True,
                'count': count,
                'note': 'Not in OFFICE_CHOICES',
            })

    rows_sorted = sorted(rows, key=lambda row: row['office'].lower())

    return jsonify({
        'classification': classification,
        'total_offices': len(rows_sorted),
        'offices_with_records': total_with_records,
        'offices_without_records': len([row for row in rows_sorted if not row.get('has_record')]),
        'rows': rows_sorted,
        'message': 'Report generated successfully.',
        'date_from': window['date_from'],
        'date_to': window['date_to'],
        'month': window['month'],
        'year': window['year'],
    })


@main.route('/admin/missing-offices/details')
@login_required
def admin_missing_office_details():
    """Return documents for a given office and classification."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    classification = (request.args.get('classification') or '').strip()
    office = (request.args.get('office') or '').strip()
    if not classification or not office:
        return jsonify({'error': 'Classification and office are required.'}), 400

    window = _resolve_date_window()
    start_dt = window['start_dt']
    end_dt = window['end_dt']

    try:
        documents = (
            Document.query
            .options(joinedload(Document.creator), joinedload(Document.recipient))
            .filter(
                Document.classification.ilike(f'{classification}%'),
                Document.office == office,
                Document.timestamp >= start_dt if start_dt else True,
                Document.timestamp < end_dt if end_dt else True,
            )
            .order_by(Document.timestamp.desc())
            .limit(200)
            .all()
        )
        data = []
        for document in documents:
            data.append({
                'id': document.id,
                'title': document.title,
                'classification': document.classification,
                'office': document.office,
                'status': document.status,
                'creator': document.creator.username if document.creator else 'Unknown',
                'recipient': document.recipient.username if document.recipient else 'Unknown',
                'timestamp': format_timestamp(document.timestamp),
                'barcode': document.barcode or '',
            })
        return jsonify({
            'classification': classification,
            'office': office,
            'count': len(data),
            'documents': data,
            'date_from': window['date_from'],
            'date_to': window['date_to'],
            'month': window['month'],
            'year': window['year'],
        })
    except Exception as exc:
        try:
            current_app.logger.error('Missing office details error: %s', exc)
        except Exception:
            pass
        return jsonify({'error': 'Unable to fetch document details.'}), 500
