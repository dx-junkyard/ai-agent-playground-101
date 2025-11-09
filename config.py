import os

# AI 設定
AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
AI_API_BASE = os.getenv("OPENAI_API_BASE") or None

# データベース設定
DB_HOST = "db"
DB_USER = "me"
DB_PASSWORD = "me"
DB_NAME = "mydb"
DB_PORT = 3306

