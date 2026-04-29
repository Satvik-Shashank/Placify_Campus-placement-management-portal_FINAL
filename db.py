# =============================================================================
# PLACIFY - DATABASE CONNECTION LAYER (PostgreSQL / Supabase)
# File: db.py
# =============================================================================

import psycopg2
from psycopg2 import pool, extras, Error
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Tuple
import logging
from config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = get_config()

# =============================================================================
# CONNECTION POOL
# =============================================================================

# Lazy pool — created on first request, not at import time
_connection_pool = None

def _resolve_ipv4(hostname: str) -> str:
    """
    Resolve hostname to an IPv4 address.
    Vercel serverless functions cannot make outbound IPv6 connections,
    but Supabase's direct DB hostname often resolves to IPv6.
    Forcing AF_INET ensures we always get an IPv4 address.
    """
    import socket
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
        if results:
            ipv4 = results[0][4][0]
            logger.info(f"✓ Resolved {hostname} → {ipv4} (IPv4 forced)")
            return ipv4
    except Exception as e:
        logger.warning(f"IPv4 resolution failed for {hostname}: {e}, using hostname as-is")
    return hostname


def _get_pool():
    global _connection_pool
    if _connection_pool is not None:
        return _connection_pool
    try:
        host = config.MYSQL_HOST or 'localhost'
        port = int(config.MYSQL_PORT or 5432)
        dbname = config.MYSQL_DATABASE or 'postgres'
        user = config.MYSQL_USER or 'postgres'
        password = config.MYSQL_PASSWORD or ''
        pool_size = int(getattr(config, 'MYSQL_POOL_SIZE', 3))

        # ── CRITICAL FIX: Vercel blocks outbound IPv6. ──────────────────────
        # Supabase direct DB hostnames (db.*.supabase.co) resolve to IPv6.
        # Force IPv4 resolution so the connection always succeeds on Vercel.
        # For the connection pooler host (*.pooler.supabase.com) this is a no-op.
        connect_host = _resolve_ipv4(host)

        # Try with SSL first (required for Supabase), fall back without
        try:
            dsn = (f"host={connect_host} port={port} dbname={dbname} "
                   f"user={user} password={password} sslmode=require connect_timeout=15")
            _connection_pool = pool.SimpleConnectionPool(minconn=1, maxconn=pool_size, dsn=dsn)
        except Exception as ssl_err:
            logger.warning(f"SSL connect failed ({ssl_err}), retrying without SSL...")
            dsn = (f"host={connect_host} port={port} dbname={dbname} "
                   f"user={user} password={password} connect_timeout=15")
            _connection_pool = pool.SimpleConnectionPool(minconn=1, maxconn=pool_size, dsn=dsn)

        logger.info(f"✓ Pool created: {dbname}@{connect_host}:{port}")
    except Exception as e:
        logger.error(f"✗ Pool creation failed: {e}")
        _connection_pool = None
    return _connection_pool

# Keep backward-compat alias
def _pool_getter():
    return _get_pool()


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================

@contextmanager
def get_connection():
    connection = None
    p = _get_pool()
    try:
        if p is None:
            raise Exception("Database connection pool unavailable. Check environment variables.")
        connection = p.getconn()
        yield connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if connection:
            p = _get_pool()
            if p:
                p.putconn(connection)


@contextmanager
def get_cursor(dictionary=True, buffered=False):
    with get_connection() as connection:
        cursor_factory = extras.RealDictCursor if dictionary else None
        cursor = connection.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
            connection.commit()
        except Exception as e:
            connection.rollback()
            logger.error(f"Cursor error, rolled back: {e}")
            raise
        finally:
            cursor.close()


@contextmanager
def transaction():
    with get_connection() as connection:
        try:
            connection.autocommit = False
            yield connection
            connection.commit()
        except Exception as e:
            connection.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
        finally:
            connection.autocommit = True


# =============================================================================
# STORED PROCEDURE CALLS (PostgreSQL functions returning TABLE)
# =============================================================================

def call_procedure(proc_name: str, args: Optional[Tuple] = None, fetch_results: bool = True) -> Dict[str, Any]:
    result = {'success': False, 'data': None, 'error': None, 'rowcount': 0}
    try:
        with get_connection() as connection:
            cursor = connection.cursor(cursor_factory=extras.RealDictCursor)
            try:
                # PostgreSQL: SELECT * FROM function_name(args)
                placeholders = ', '.join(['%s'] * len(args)) if args else ''
                query = f"SELECT * FROM {proc_name}({placeholders})"
                cursor.execute(query, args or ())

                if fetch_results:
                    rows = cursor.fetchall()
                    result['data'] = [dict(row) for row in rows]

                connection.commit()
                result['success'] = True
                result['rowcount'] = cursor.rowcount
            except Exception as e:
                connection.rollback()
                result['error'] = str(e)
                logger.error(f"Procedure '{proc_name}' failed: {result['error']}")
            finally:
                cursor.close()
    except Exception as outer:
        result['error'] = str(outer)
        logger.error(f"Procedure '{proc_name}' connection error: {outer}")
    return result


def call_procedure_with_out_params(proc_name: str, in_args: Tuple, out_param_count: int) -> Dict[str, Any]:
    """
    Call a PostgreSQL function that returns TABLE(col1, col2...).
    The 'out params' are columns of the returned row.
    """
    result = {'success': False, 'data': None, 'out_params': [], 'error': None}
    try:
        with get_connection() as connection:
            cursor = connection.cursor(cursor_factory=extras.RealDictCursor)
            try:
                placeholders = ', '.join(['%s'] * len(in_args))
                query = f"SELECT * FROM {proc_name}({placeholders})"
                cursor.execute(query, in_args)

                row = cursor.fetchone()
                if row:
                    row_dict = dict(row)
                    result['out_params'] = list(row_dict.values())
                    result['data'] = [row_dict]

                # Fetch any remaining rows
                remaining = cursor.fetchall()
                if remaining:
                    result['data'] = [dict(row)] + [dict(r) for r in remaining] if row else [dict(r) for r in remaining]

                connection.commit()
                result['success'] = True
            except Exception as e:
                connection.rollback()
                result['error'] = str(e)
                if 'RAISE' in str(e) or 'ERROR' in str(e):
                    msg = str(e).split('\n')[0]
                    result['error'] = msg
                logger.error(f"Procedure '{proc_name}' failed: {result['error']}")
            finally:
                cursor.close()
    except Exception as outer:
        result['error'] = str(outer)
        logger.error(f"Procedure '{proc_name}' connection error: {outer}")
    return result


# =============================================================================
# QUERY EXECUTION
# =============================================================================

def execute_query(query: str, params: Optional[Tuple] = None, fetch: bool = True, fetch_one: bool = False) -> Dict[str, Any]:
    result = {'success': False, 'data': None, 'rowcount': 0, 'lastrowid': None, 'error': None}
    try:
        with get_cursor() as cursor:
            try:
                # Handle INSERT ... RETURNING for lastrowid
                is_insert = query.strip().upper().startswith('INSERT')
                if is_insert and 'RETURNING' not in query.upper():
                    query = query.rstrip().rstrip(';')
                    import re
                    m = re.match(r'INSERT\s+INTO\s+(\w+)', query, re.IGNORECASE)
                    if m:
                        table = m.group(1)
                        pk_map = {
                            'users': 'user_id', 'students': 'student_id',
                            'companies': 'company_id', 'applications': 'application_id',
                            'rounds': 'round_id', 'round_results': 'result_id',
                            'offers': 'offer_id', 'skills': 'skill_id',
                            'student_skills': 'student_skill_id',
                            'audit_logs': 'log_id', 'eligibility_criteria': 'criteria_id',
                            'placement_policy': 'policy_id'
                        }
                        pk = pk_map.get(table, table.rstrip('s') + '_id')
                        query += f" RETURNING {pk}"

                cursor.execute(query, params or ())
                result['rowcount'] = cursor.rowcount

                if fetch or is_insert:
                    if fetch_one:
                        row = cursor.fetchone()
                        result['data'] = dict(row) if row else None
                    else:
                        rows = cursor.fetchall()
                        if rows:
                            result['data'] = [dict(r) for r in rows]
                            if is_insert and rows:
                                first_row = dict(rows[0])
                                result['lastrowid'] = list(first_row.values())[0]
                        else:
                            result['data'] = [] if fetch else None

                result['success'] = True
            except Exception as e:
                result['error'] = str(e)
                logger.error(f"Query failed: {result['error']}")
    except Exception as outer:
        # Pool unavailable or connection error — never raise to callers
        result['error'] = str(outer)
        logger.error(f"execute_query connection error: {outer}")
    return result


def execute_many(query: str, params_list: List[Tuple]) -> Dict[str, Any]:
    result = {'success': False, 'rowcount': 0, 'error': None}
    try:
        with get_cursor() as cursor:
            try:
                cursor.executemany(query, params_list)
                result['rowcount'] = cursor.rowcount
                result['success'] = True
            except Exception as e:
                result['error'] = str(e)
                logger.error(f"Batch execution failed: {result['error']}")
    except Exception as outer:
        result['error'] = str(outer)
        logger.error(f"execute_many connection error: {outer}")
    return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_by_id(table: str, id_column: str, id_value: Any) -> Optional[Dict]:
    query = f"SELECT * FROM {table} WHERE {id_column} = %s"
    result = execute_query(query, (id_value,), fetch_one=True)
    return result['data'] if result['success'] else None

def get_all(table: str, where_clause: str = "", params: Tuple = ()) -> List[Dict]:
    query = f"SELECT * FROM {table} {where_clause}"
    result = execute_query(query, params)
    return result['data'] if result['success'] else []

def insert(table: str, data: Dict[str, Any]) -> Optional[int]:
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['%s'] * len(data))
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    result = execute_query(query, tuple(data.values()), fetch=False)
    return result['lastrowid'] if result['success'] else None

def update(table: str, id_column: str, id_value: Any, data: Dict[str, Any]) -> bool:
    set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
    query = f"UPDATE {table} SET {set_clause} WHERE {id_column} = %s"
    params = tuple(data.values()) + (id_value,)
    result = execute_query(query, params, fetch=False)
    return result['success']

def delete(table: str, id_column: str, id_value: Any) -> bool:
    query = f"DELETE FROM {table} WHERE {id_column} = %s"
    result = execute_query(query, (id_value,), fetch=False)
    return result['success']


# =============================================================================
# CONNECTION TEST
# =============================================================================

def test_connection() -> bool:
    try:
        with get_cursor() as cursor:
            cursor.execute("SELECT 1 AS test, current_database() AS db")
            result = cursor.fetchone()
            if result and dict(result).get('test') == 1:
                logger.info(f"✓ Connection OK: {dict(result).get('db')}")
                return True
    except Exception as e:
        logger.error(f"✗ Connection failed: {e}")
    return False


def get_table_counts() -> Dict[str, int]:
    tables = [
        'users', 'students', 'companies', 'eligibility_criteria',
        'applications', 'rounds', 'round_results', 'offers',
        'skills', 'student_skills', 'audit_logs', 'placement_policy'
    ]
    counts = {}
    for table in tables:
        result = execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch_one=True)
        counts[table] = result['data']['count'] if result['success'] and result['data'] else 0
    return counts


if __name__ == '__main__':
    print("=" * 60)
    print("DATABASE CONNECTION TEST (PostgreSQL/Supabase)")
    print("=" * 60)
    if test_connection():
        print("\n✓ Connection pool working")
        print("\nTable Row Counts:")
        print("-" * 40)
        for table, count in get_table_counts().items():
            print(f"  {table:25} : {count:5} rows")
    else:
        print("\n✗ Connection failed! Check .env credentials")
