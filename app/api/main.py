import requests
import re
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, HTTPException, Query
from typing import Dict, List
import logging

from app.api.ai_client import AIClient
from app.api.db import DBClient

app = FastAPI()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ユーザー登録エンドポイント
@app.post("/api/v1/users")
async def create_user(request: Request) -> Dict[str, str]:
    try:
        data = await request.json()
    except Exception:
        data = {}
    line_user_id = data.get("line_user_id")
    repo = DBClient()
    user_id = repo.create_user(line_user_id=line_user_id)
    return {"user_id": user_id}

# LINEのWebhookエンドポイント
@app.post("/api/v1/user-message")
async def post_usermessage(request: Request) -> str:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
   
    ai_generator = AIClient()
    message = body.get("message", "")
    user_id = body.get("user_id")
    repo = DBClient()
    if user_id:
        repo.insert_message(user_id, "user", message)

    conversation_history = ""
    if user_id:
        history_records = repo.get_user_messages(user_id=user_id, limit=20)
        if history_records:
            conversation_history = "\n".join(
                f"{'利用者' if record['role'] == 'user' else '職員'}: {record['message']}"
                for record in reversed(history_records)
            )

    ai_response = ai_generator.create_response(message, conversation_history)
    logger.info(f"AI response: {ai_response}")
    if user_id:
        repo.insert_message(user_id, "ai", ai_response)
    return ai_response

@app.get("/api/v1/user-messages")
async def get_user_messages(user_id: str = Query(..., description="ユーザーID"), limit: int = Query(10, ge=1, le=100, description="取得件数")) -> List[Dict]:
    repo = DBClient()
    messages = repo.get_user_messages(user_id=user_id, limit=limit)
    return messages

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

