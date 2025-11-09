import requests
import re
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, HTTPException, Query
from typing import Dict, List
import logging
import copy

from app.api.ai_client import AIClient
from app.api.db import DBClient

app = FastAPI()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROFILE_TEMPLATE = {
    "basic": {
        "full_name": "",
        "furigana": "",
        "gender": "",
        "birthdate": "",
        "age": "",
        "address": "",
        "phone": "",
        "email": "",
    },
    "household": {
        "household_members": "",
        "marital_status": "",
        "dependents": "",
    },
    "lifestyle": {
        "occupation": "",
        "workplace": "",
        "interests_hobbies": "",
        "exercise_history": "",
        "lifestyle_notes": "",
    },
    "health": {
        "medical_history": "",
        "allergies": "",
        "medications": "",
        "chronic_conditions": "",
        "special_considerations": "",
    },
    "beauty": {
        "hair_history": "",
        "hair_type": "",
        "styling_preferences": "",
        "last_salon_visit": "",
    },
    "municipal": {
        "window_selection": "",
        "desired_services": "",
        "documents_needed": "",
        "timeline": "",
        "preferred_contact_method": "",
        "notes": "",
    },
}

AGE_PATTERN = re.compile(r"(\d{1,3})\s*(歳|才)")
WINDOW_PATTERN = re.compile(r"(窓口選択|来庁窓口)[:：]\s*(.+)")
HOUSEHOLD_KEYWORDS = ["家族", "夫", "妻", "子ども", "世帯", "同居"]
RESIDENCE_KEYWORDS = ["市内", "国分寺", "在住", "転入", "転出", "引っ越"]
ADDRESS_KEYWORDS = ["丁目", "番地", "住所", "町"]
PURPOSE_KEYWORDS = ["手続", "申請", "相談", "証明", "補助", "支援"]
DOCUMENT_KEYWORDS = ["書類", "持参", "持ち物", "提出", "必要"]
URGENCY_KEYWORDS = ["いつまで", "期限", "急", "早め", "本日", "至急"]
METHOD_KEYWORDS = ["窓口", "来庁", "オンライン", "郵送", "電話"]
INTEREST_KEYWORDS = ["趣味", "好き", "興味", "楽し"]
EXERCISE_KEYWORDS = ["運動", "スポーツ", "トレーニング", "体操", "ランニング", "ウォーキング"]
CONSIDERATION_KEYWORDS = ["障害", "体調", "持病", "介護", "妊娠", "勤務", "言語", "育児"]


def _new_profile():
    return copy.deepcopy(PROFILE_TEMPLATE)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _maybe_update(target: Dict[str, str], key: str, value: str) -> bool:
    if not value:
        return False
    current = target.get(key)
    if current:
        return False
    target[key] = value
    return True


def _extract_profile_from_history(existing_profile: Dict, history_records: List[Dict]) -> (Dict, bool):
    profile = existing_profile or _new_profile()
    changed = False

    for record in reversed(history_records):
        if record["role"] != "user":
            continue
        text = record["message"]
        normalized = _normalize(text)

        match = AGE_PATTERN.search(text)
        if match:
            changed |= _maybe_update(profile["basic"], "age", match.group(1) + "歳")

        if any(keyword in text for keyword in HOUSEHOLD_KEYWORDS):
            changed |= _maybe_update(profile["household"], "household_members", normalized)

        if any(keyword in text for keyword in RESIDENCE_KEYWORDS + ADDRESS_KEYWORDS):
            changed |= _maybe_update(profile["basic"], "address", normalized)

        if any(keyword in text for keyword in PURPOSE_KEYWORDS):
            changed |= _maybe_update(profile["municipal"], "desired_services", normalized)

        if any(keyword in text for keyword in DOCUMENT_KEYWORDS):
            changed |= _maybe_update(profile["municipal"], "documents_needed", normalized)

        if any(keyword in text for keyword in URGENCY_KEYWORDS):
            changed |= _maybe_update(profile["municipal"], "timeline", normalized)

        if any(keyword in text for keyword in METHOD_KEYWORDS):
            changed |= _maybe_update(profile["municipal"], "preferred_contact_method", normalized)

        if any(keyword in text for keyword in INTEREST_KEYWORDS):
            changed |= _maybe_update(profile["lifestyle"], "interests_hobbies", normalized)

        if any(keyword in text for keyword in EXERCISE_KEYWORDS):
            changed |= _maybe_update(profile["lifestyle"], "exercise_history", normalized)

        if any(keyword in text for keyword in CONSIDERATION_KEYWORDS):
            changed |= _maybe_update(profile["health"], "special_considerations", normalized)

        window_match = WINDOW_PATTERN.search(text)
        if window_match:
            changed |= _maybe_update(profile["municipal"], "window_selection", window_match.group(2))

    return profile, changed


def _update_user_profile(repo: DBClient, user_id: str, history_records: List[Dict]):
    if not user_id:
        return
    existing = repo.get_user_profile(user_id) or _new_profile()
    profile, changed = _extract_profile_from_history(existing, history_records)
    if changed:
        repo.upsert_user_profile(user_id, profile)

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
        full_history = repo.get_user_messages(user_id=user_id, limit=50)
        _update_user_profile(repo, user_id, full_history)
    return ai_response

@app.get("/api/v1/user-messages")
async def get_user_messages(user_id: str = Query(..., description="ユーザーID"), limit: int = Query(10, ge=1, le=100, description="取得件数")) -> List[Dict]:
    repo = DBClient()
    messages = repo.get_user_messages(user_id=user_id, limit=limit)
    return messages

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

