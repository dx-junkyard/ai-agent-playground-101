import json
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector import errorcode

from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

class DBClient:
    def __init__(self):
        self.config = {
            'host': DB_HOST,
            'user': DB_USER,
            'password': DB_PASSWORD,
            'database': DB_NAME,
            'port': DB_PORT,
            'charset': 'utf8mb4'
        }

    def create_user(self, line_user_id=None):
        import uuid
        user_id = str(uuid.uuid4())
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (id, line_user_id) VALUES (%s,%s)",
                (user_id, line_user_id),
            )
            conn.commit()
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_DUP_ENTRY:
                cursor.execute(
                    "SELECT id FROM users WHERE line_user_id=%s",
                    (line_user_id,),
                )
                row = cursor.fetchone()
                user_id = row[0] if row else user_id
            else:
                print(f"[✗] MySQL Error: {err}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return user_id

    def insert_message(self, user_id, role, message):
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()

            query = """
                INSERT INTO user_messages (user_id, role, message)
                VALUES (%s, %s, %s)
            """
            values = (user_id, role, message)
            cursor.execute(query, values)
            conn.commit()

            print(f"[✓] Inserted user_messages for user_id={user_id} role={role}")
            return cursor.lastrowid

        except mysql.connector.Error as err:
            print(f"[✗] MySQL Error: {err}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_user_messages(self, user_id, limit=10):
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT user_id, role, message
                FROM user_messages
                WHERE user_id = %s
                ORDER BY id DESC
                LIMIT %s
            """
            cursor.execute(query, (user_id, limit))
            messages = cursor.fetchall()
            return messages
        except mysql.connector.Error as err:
            print(f"[✗] MySQL Error: {err}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def get_recent_conversation(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT id, user_id, role, message, created_at
                FROM (
                    SELECT id, user_id, role, message, created_at
                    FROM user_messages
                    WHERE user_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                ) AS recent
                ORDER BY id ASC
            """
            cursor.execute(query, (user_id, limit))
            return cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"[✗] MySQL Error: {err}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_user_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            query = """
                SELECT resident_profile, service_needs
                FROM user_states
                WHERE user_id = %s
            """
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            resident_profile = json.loads(row[0]) if row[0] else None
            service_needs = json.loads(row[1]) if row[1] else None
            return {
                "resident_profile": resident_profile,
                "service_needs": service_needs,
            }
        except mysql.connector.Error as err:
            print(f"[✗] MySQL Error: {err}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def upsert_user_state(self, user_id: str, resident_profile: Dict[str, Any], service_needs: Dict[str, Any]) -> None:
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            query = """
                INSERT INTO user_states (user_id, resident_profile, service_needs)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    resident_profile = VALUES(resident_profile),
                    service_needs = VALUES(service_needs)
            """
            cursor.execute(
                query,
                (
                    user_id,
                    json.dumps(resident_profile, ensure_ascii=False),
                    json.dumps(service_needs, ensure_ascii=False),
                ),
            )
            conn.commit()
        except mysql.connector.Error as err:
            print(f"[✗] MySQL Error: {err}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def record_analysis(self, user_id: str, user_message_id: int, analysis: Dict[str, Any]) -> None:
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            query = """
                INSERT INTO user_message_analyses (user_id, user_message_id, analysis)
                VALUES (%s, %s, %s)
            """
            cursor.execute(
                query,
                (
                    user_id,
                    user_message_id,
                    json.dumps(analysis, ensure_ascii=False),
                ),
            )
            conn.commit()
        except mysql.connector.Error as err:
            print(f"[✗] MySQL Error: {err}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

