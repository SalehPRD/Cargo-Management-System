import pymysql

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "cargo-system",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def call_sp(sp_name, args=()):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.callproc(sp_name, args)
            conn.commit()
            result = cursor.fetchall()
        return result
    except Exception as e:
        conn.rollback()
        print(f"SP Error [{sp_name}]: {e}")
        return []
    finally:
        conn.close()

def call_sp_one(sp_name, args=()):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.callproc(sp_name, args)
            conn.commit()
            result = cursor.fetchone()
        return result
    except Exception as e:
        conn.rollback()
        print(f"SP Error [{sp_name}]: {e}")
        return None
    finally:
        conn.close()
