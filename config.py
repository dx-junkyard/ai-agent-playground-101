# config.py
# ここに設定を記載します

import os

AI_MODEL = "schroneko/llama-3.1-swallow-8b-instruct-v0.1:latest"
AI_URL = "http://host.docker.internal:11434"

DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = os.getenv("DB_USER", "me")
DB_PASSWORD = os.getenv("DB_PASSWORD", "me")
DB_NAME = os.getenv("DB_NAME", "mydb")
DB_PORT = int(os.getenv("DB_PORT", 3306))

