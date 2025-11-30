from copy import deepcopy
import json
from fastapi import FastAPI, Request, HTTPException, Query
from typing import Any, Dict, List, Optional
import logging
import os
from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

from app.api.ai_client import AIClient
from app.api.db import DBClient
from app.api.state_manager import StateManager

app = FastAPI()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_OPENING_QUESTION = "何かお困りのことはありますか？"




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

from app.api.workflow import WorkflowManager

# ... (imports)

# LINEのWebhookエンドポイント
@app.post("/api/v1/user-message")
async def post_usermessage(request: Request) -> str:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    ai_client = AIClient()
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

    # Initialize WorkflowManager
    workflow_manager = WorkflowManager(ai_client)

    # Load state and history
    history = repo.get_recent_conversation(user_id)
    stored_state = repo.get_user_state(user_id)
    current_state = StateManager.get_state_with_defaults(stored_state)

    # Initialize context
    initial_state = StateManager.init_conversation_context(
        user_message=message,
        dialog_history=history,
        resident_profile=current_state["resident_profile"],
        service_needs=current_state["service_needs"]
    )

    # Invoke workflow
    final_state = workflow_manager.invoke(initial_state)
    bot_message = final_state.get("bot_message", "申し訳ありません、エラーが発生しました。")

    # Save updated state
    repo.upsert_user_state(
        user_id, 
        final_state["resident_profile"], 
        final_state["service_needs"]
    )
    
    # Save analysis result
    analysis_to_save = {
        "resident_profile": final_state["resident_profile"],
        "service_needs": final_state["service_needs"],
        "hypotheses": final_state.get("hypotheses"),
        "response_plan": final_state.get("response_plan")
    }
    repo.record_analysis(user_id, user_message_id, analysis_to_save)

    repo.insert_message(user_id, "ai", bot_message)
    return bot_message

@app.get("/api/v1/user-messages")
async def get_user_messages(user_id: str = Query(..., description="ユーザーID"), limit: int = Query(10, ge=1, le=100, description="取得件数")) -> List[Dict]:
    repo = DBClient()
    messages = repo.get_user_messages(user_id=user_id, limit=limit)
    return messages

from fastapi import UploadFile, File
from app.api.components.catalog_manager import CatalogManager

@app.post("/api/v1/service-catalog/import")
async def import_service_catalog(file: UploadFile = File(...)):
    """
    サービスカタログ（JSON）をインポートする。
    EmbeddingはLLM APIを使用して生成される。
    """
    try:
        content = await file.read()
        catalog_data = json.loads(content)
        
        if not isinstance(catalog_data, list):
            # Try to handle if wrapped in a key like "services" or similar, or just error
            # Based on previous file, it was a list.
            raise HTTPException(status_code=400, detail="JSON must be a list of service entries")
            
        manager = CatalogManager()
        result = manager.import_catalog(catalog_data)
        
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/service-catalog/reset")
async def reset_service_catalog():
    """
    サービスカタログをリセットする（DBとQdrantをクリア）。
    """
    try:
        manager = CatalogManager()
        result = manager.reset_catalog()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result)
            
        return result
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

