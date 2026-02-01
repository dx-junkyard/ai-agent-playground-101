import json
import logging
import mysql.connector
from mysql.connector import errorcode
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

logger = logging.getLogger(__name__)

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
        self._ensure_profile_table()

    def _ensure_profile_table(self):
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id VARCHAR(255) PRIMARY KEY,
                    profile JSON NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
                    CONSTRAINT fk_user_profiles_user
                        FOREIGN KEY (user_id) REFERENCES users(id)
                        ON DELETE CASCADE
                )
                """
            )
            conn.commit()
        except mysql.connector.Error as err:
            logger.error("Failed ensuring user_profiles table: %s", err)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def create_user(self, line_user_id=None):
        import uuid
        user_id = str(uuid.uuid4())
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (id, line_user_id) VALUES (%s,%s)",
                (user_id, line_user_id),
            )
            conn.commit()
            logger.info("Created user %s (line_user_id=%s)", user_id, line_user_id)
        except mysql.connector.Error as err:
            logger.error("MySQL error on create_user: %s", err)
            if err.errno == errorcode.ER_DUP_ENTRY and cursor:
                cursor.execute(
                    "SELECT id FROM users WHERE line_user_id=%s",
                    (line_user_id,),
                )
                row = cursor.fetchone()
                user_id = row[0] if row else user_id
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return user_id

    def ensure_user_exists(self, user_id, line_user_id=None):
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT IGNORE INTO users (id, line_user_id) VALUES (%s, %s)",
                (user_id, line_user_id),
            )
            conn.commit()
            logger.debug("Ensured user exists: %s", user_id)
        except mysql.connector.Error as err:
            logger.error("MySQL error on ensure_user_exists (user_id=%s): %s", user_id, err)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def insert_message(self, user_id, role, message):
        conn = None
        cursor = None
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

            logger.debug("Inserted message for user_id=%s role=%s", user_id, role)

        except mysql.connector.Error as err:
            logger.error("MySQL error on insert_message (user_id=%s role=%s): %s", user_id, role, err)
            raise
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
            logger.error("MySQL error on get_user_messages (user_id=%s): %s", user_id, err)
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def get_user_profile(self, user_id):
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT profile FROM user_profiles WHERE user_id = %s",
                (user_id,)
            )
            row = cursor.fetchone()
            if row and row.get("profile"):
                return json.loads(row["profile"])
        except mysql.connector.Error as err:
            logger.error("MySQL error on get_user_profile (user_id=%s): %s", user_id, err)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return None

    def upsert_user_profile(self, user_id, profile_data):
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_profiles (user_id, profile)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE profile = VALUES(profile)
                """,
                (user_id, json.dumps(profile_data, ensure_ascii=False))
            )
            conn.commit()
            logger.info("Updated user profile for user_id=%s", user_id)
        except mysql.connector.Error as err:
            logger.error("MySQL error on upsert_user_profile (user_id=%s): %s", user_id, err)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

