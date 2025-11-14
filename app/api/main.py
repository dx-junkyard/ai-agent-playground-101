from copy import deepcopy
from fastapi import FastAPI, Request, HTTPException, Query
from typing import Any, Dict, List, Optional
import logging

from app.api.ai_client import AIClient
from app.api.db import DBClient

app = FastAPI()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_OPENING_QUESTION = "何かお困りのことはありますか？"

DEFAULT_RESIDENT_PROFILE: Dict[str, Any] = {
    "basic": {
        "age": None,
        "gender": None,
        "address_area": None,
        "family_structure": None,
        "household_type": None,
    },
    "lifestyle": {
        "employment_status": None,
        "work_style": None,
        "recent_life_events": [],
    },
    "economic": {
        "income_level": None,
        "financial_difficulty": False,
    },
    "health": {
        "health_issues": [],
        "disabilities": [],
        "mobility": "public_transport_only",
    },
    "behavior": {
        "frequent_places": [],
        "outing_frequency": None,
        "hobbies": [],
        "active_hours": "morning_person",
    },
    "hypothesis": None,
    "labels": [],
}

DEFAULT_SERVICE_NEEDS: Dict[str, Any] = {
    "explicit_needs": {
        "current_problems": [],
        "desired_services": [],
        "goals": [],
    },
    "implicit_needs": {
        "inferred_issues": [],
        "risk_indicators": [],
    },
    "constraints": {
        "time": [],
        "distance": "within_2km",
        "budget_preference": "low_cost",
    },
    "priority": {
        "top_priority_area": None,
        "secondary_priorities": [],
    },
    "hypothesis": None,
    "labels": [],
}


def _deep_merge(default: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(default)
    if not isinstance(updates, dict):
        return result
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _state_with_defaults(stored_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    resident_updates = (stored_state or {}).get("resident_profile", {})
    service_updates = (stored_state or {}).get("service_needs", {})
    resident_profile = _deep_merge(DEFAULT_RESIDENT_PROFILE, resident_updates)
    service_needs = _deep_merge(DEFAULT_SERVICE_NEEDS, service_updates)
    return {
        "resident_profile": resident_profile,
        "service_needs": service_needs,
    }


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
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    if message is None:
        raise HTTPException(status_code=400, detail="message is required")

    repo = DBClient()
    user_message_id = repo.insert_message(user_id, "user", message)
    if not user_message_id:
        raise HTTPException(status_code=500, detail="Failed to store user message")

    history = repo.get_recent_conversation(user_id)
    current_state = _state_with_defaults(repo.get_user_state(user_id))

    analysis = ai_generator.analyze_interaction(history, current_state, message)
    next_question = DEFAULT_OPENING_QUESTION

    if isinstance(analysis, dict):
        normalized_analysis = None
        resident_profile = analysis.get("resident_profile")
        service_needs = analysis.get("service_needs")
        if isinstance(resident_profile, dict) and isinstance(service_needs, dict):
            normalized_resident = _deep_merge(DEFAULT_RESIDENT_PROFILE, resident_profile)
            normalized_service = _deep_merge(DEFAULT_SERVICE_NEEDS, service_needs)
            normalized_analysis = {**analysis}
            normalized_analysis["resident_profile"] = normalized_resident
            normalized_analysis["service_needs"] = normalized_service
            repo.record_analysis(user_id, user_message_id, normalized_analysis)
            repo.upsert_user_state(user_id, normalized_resident, normalized_service)
        else:
            logger.warning("Analysis response missing resident_profile or service_needs: %s", analysis)
        source = normalized_analysis or analysis
        next_candidate = source.get("next_question") if isinstance(source, dict) else None
        if isinstance(next_candidate, str):
            next_question = next_candidate.strip() or DEFAULT_OPENING_QUESTION

    repo.insert_message(user_id, "ai", next_question)
    return next_question

@app.get("/api/v1/user-messages")
async def get_user_messages(user_id: str = Query(..., description="ユーザーID"), limit: int = Query(10, ge=1, le=100, description="取得件数")) -> List[Dict]:
    repo = DBClient()
    messages = repo.get_user_messages(user_id=user_id, limit=limit)
    return messages

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

