#!/usr/bin/env python3
"""Intelligence Library API - Unified Research Asset Retrieval.
P1-C: Provides REST API for querying the intelligence_assets table.
Does NOT modify intelligence.py Q&A gateway functionality.
OSAI boundary: Intelligence Core is read-only reference, never a runtime dependency.
"""
import json
import os
import sqlite3
from flask import Blueprint, jsonify, request

# Blueprint
intelligence_library_bp = Blueprint('intelligence_library', __name__, url_prefix='/api/intelligence/library')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db')


def _get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row):
    """Convert sqlite3.Row to dict, parse tags JSON."""
    d = dict(row)
    if d.get('tags'):
        try:
            d['tags'] = json.loads(d['tags'])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


# ============================================================
# GET /api/intelligence/library - List all assets with filters
# ============================================================
@intelligence_library_bp.route('', methods=['GET'])
def list_assets():
    """List all intelligence assets with optional filters.
    
    Query params:
        sub_library: filter by 13-directory sub-library
        source_origin: OSAI/ADRH/SICI/ZBC-internal/Governance/DCC
        product: ZBC/GGI/SHARED
        domain: ZBMP/CTH/SYSTEM/SHARED
        evidence_level: E0-E4
        knowledge_status: FACT/VERIFIED/PENDING/CONCEPT/RECOMMENDATION/LEGACY
        landing_status: 已落地/已实现待验证/可直接复用/建议转化/仅研究不应转化
        admission_status: CANDIDATE/VALIDATED/GENERALIZABLE/ADMITTED
        page: page number (default 1)
        per_page: items per page (default 50, max 200)
    """
    conn = _get_db()
    cursor = conn.cursor()
    
    # Build query
    query = "SELECT * FROM intelligence_assets WHERE 1=1"
    params = []
    
    filterable = ['sub_library', 'source_origin', 'product', 'domain', 
                  'evidence_level', 'knowledge_status', 'landing_status', 'admission_status']
    for field in filterable:
        val = request.args.get(field)
        if val:
            query += f" AND {field} = ?"
            params.append(val)
    
    # Count total
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    # Pagination
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(200, max(1, int(request.args.get('per_page', 50))))
    offset = (page - 1) * per_page
    
    query += " ORDER BY asset_id LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    assets = [_row_to_dict(r) for r in rows]
    
    conn.close()
    
    return jsonify({
        'ok': True,
        'data': assets,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page,
        }
    })


# ============================================================
# GET /api/intelligence/library/<asset_id> - Single asset detail
# ============================================================
@intelligence_library_bp.route('/<asset_id>', methods=['GET'])
def get_asset(asset_id):
    """Get single asset by asset_id (e.g., AST-0001)."""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM intelligence_assets WHERE asset_id = ?", (asset_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'ok': False, 'error': f'Asset {asset_id} not found'}), 404
    
    return jsonify({'ok': True, 'data': _row_to_dict(row)})


# ============================================================
# GET /api/intelligence/library/search?q=xxx - Full text search
# ============================================================
@intelligence_library_bp.route('/search', methods=['GET'])
def search_assets():
    """Full-text search across title, summary, tags, sub_library.
    
    Query params:
        q: search query (required)
        sub_library: optional filter
        product: optional filter
        landing_status: optional filter
        limit: max results (default 50, max 100)
    """
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'ok': False, 'error': 'Query parameter q is required'}), 400
    
    conn = _get_db()
    cursor = conn.cursor()
    
    # Build search query using LIKE
    search_terms = q.split()
    where_clauses = []
    params = []
    
    for term in search_terms:
        like = f'%{term}%'
        where_clauses.append("(title LIKE ? OR summary LIKE ? OR tags LIKE ? OR sub_library LIKE ? OR source_origin LIKE ?)")
        params.extend([like, like, like, like, like])
    
    query = "SELECT * FROM intelligence_assets WHERE " + " AND ".join(where_clauses)
    
    # Optional filters
    for field in ['sub_library', 'product', 'landing_status', 'evidence_level']:
        val = request.args.get(field)
        if val:
            query += f" AND {field} = ?"
            params.append(val)
    
    limit = min(100, max(1, int(request.args.get('limit', 50))))
    query += " ORDER BY asset_id LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    assets = [_row_to_dict(r) for r in rows]
    
    conn.close()
    
    return jsonify({
        'ok': True,
        'query': q,
        'count': len(assets),
        'data': assets,
    })


# ============================================================
# GET /api/intelligence/library/stats - Statistics
# ============================================================
@intelligence_library_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get library statistics grouped by various dimensions."""
    conn = _get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    # Total
    cursor.execute("SELECT COUNT(*) FROM intelligence_assets")
    stats['total'] = cursor.fetchone()[0]
    
    # By sub_library
    cursor.execute("SELECT sub_library, COUNT(*) as cnt FROM intelligence_assets GROUP BY sub_library ORDER BY sub_library")
    stats['by_sub_library'] = {r[0]: r[1] for r in cursor.fetchall()}
    
    # By source_origin
    cursor.execute("SELECT source_origin, COUNT(*) as cnt FROM intelligence_assets GROUP BY source_origin ORDER BY cnt DESC")
    stats['by_source_origin'] = {r[0]: r[1] for r in cursor.fetchall()}
    
    # By product
    cursor.execute("SELECT product, COUNT(*) as cnt FROM intelligence_assets GROUP BY product ORDER BY cnt DESC")
    stats['by_product'] = {r[0]: r[1] for r in cursor.fetchall()}
    
    # By domain (ZBC only)
    cursor.execute("SELECT domain, COUNT(*) as cnt FROM intelligence_assets WHERE domain != '' GROUP BY domain ORDER BY cnt DESC")
    stats['by_domain'] = {r[0]: r[1] for r in cursor.fetchall()}
    
    # By evidence_level
    cursor.execute("SELECT evidence_level, COUNT(*) as cnt FROM intelligence_assets GROUP BY evidence_level ORDER BY evidence_level")
    stats['by_evidence_level'] = {r[0]: r[1] for r in cursor.fetchall()}
    
    # By knowledge_status
    cursor.execute("SELECT knowledge_status, COUNT(*) as cnt FROM intelligence_assets GROUP BY knowledge_status ORDER BY cnt DESC")
    stats['by_knowledge_status'] = {r[0]: r[1] for r in cursor.fetchall()}
    
    # By landing_status
    cursor.execute("SELECT landing_status, COUNT(*) as cnt FROM intelligence_assets GROUP BY landing_status ORDER BY cnt DESC")
    stats['by_landing_status'] = {r[0]: r[1] for r in cursor.fetchall()}
    
    # By admission_status
    cursor.execute("SELECT admission_status, COUNT(*) as cnt FROM intelligence_assets GROUP BY admission_status ORDER BY cnt DESC")
    stats['by_admission_status'] = {r[0]: r[1] for r in cursor.fetchall()}
    
    conn.close()
    
    return jsonify({'ok': True, 'data': stats})


# ============================================================
# GET /api/intelligence/library/sub_libraries - List sub-libraries
# ============================================================
@intelligence_library_bp.route('/sub_libraries', methods=['GET'])
def list_sub_libraries():
    """List all 13 sub-libraries with file counts."""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT sub_library, COUNT(*) as cnt FROM intelligence_assets GROUP BY sub_library ORDER BY sub_library")
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify({
        'ok': True,
        'data': [{'name': r[0], 'count': r[1]} for r in rows]
    })
