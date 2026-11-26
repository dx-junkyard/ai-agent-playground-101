import requests
import re
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any
import logging
import copy

from app.api.ai_client import AIClient
from app.api.db import DBClient

app = FastAPI()

# CORS設定（UIエミュレーターからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発環境では全許可（本番環境では適切に制限）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
# workflowモジュールのログレベルもINFOに設定
logging.getLogger("app.api.workflow").setLevel(logging.INFO)

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

# LINEのWebhookエンドポイント（LangGraphワークフロー使用）
@app.post("/api/v1/user-message")
async def post_usermessage(request: Request) -> str:
    logger.info("=" * 60)
    logger.info("APIリクエスト受信: /api/v1/user-message")
    try:
        body = await request.json()
        logger.info(f"リクエストボディ受信: {body}")
    except Exception as e:
        logger.error(f"JSON解析エラー: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid JSON")
   
    try:
        from app.api.workflow import WorkflowManager
        
        try:
            ai_client = AIClient()
            logger.info("AIClient初期化成功")
        except Exception as e:
            logger.warning(f"AIClient初期化エラー（続行）: {e}")
            # AIClientの初期化に失敗しても続行（workflow.pyでは実際には使用しないため）
            from unittest.mock import MagicMock
            ai_client = MagicMock()
            ai_client.create_response = MagicMock(return_value="モック応答")
        
        message = body.get("message", "")
        user_id = body.get("user_id")
        logger.info(f"メッセージ抽出: message='{message}', user_id='{user_id}'")
        
        # データベース接続（エラーが発生しても続行）
        conversation_history = []
        try:
            repo = DBClient()
            logger.info("データベース接続成功")
            
            if user_id:
                logger.info(f"ユーザー存在確認: user_id={user_id}")
                try:
                    repo.ensure_user_exists(user_id)
                    repo.insert_message(user_id, "user", message)
                    logger.info(f"ユーザーメッセージ保存完了: user_id={user_id}")
                except Exception as db_error:
                    logger.warning(f"データベース保存エラー（続行）: {db_error}")

            # 会話履歴を取得
            if user_id:
                logger.info(f"会話履歴取得開始: user_id={user_id}")
                try:
                    history_records = repo.get_user_messages(user_id=user_id, limit=20)
                    if history_records:
                        conversation_history = [
                            {"role": record['role'], "message": record['message']}
                            for record in reversed(history_records)
                        ]
                        logger.info(f"会話履歴取得完了: {len(conversation_history)}件")
                except Exception as db_error:
                    logger.warning(f"会話履歴取得エラー（続行）: {db_error}")
                    conversation_history = []
        except Exception as db_error:
            logger.warning(f"データベース接続エラー（続行）: {db_error}")
            # データベース接続に失敗してもワークフローは実行可能

        # LangGraphワークフローを実行
        logger.info("WorkflowManager初期化開始")
        workflow_manager = WorkflowManager(ai_client)
        logger.info("WorkflowManager初期化完了")
        
        initial_state = {
            "user_message": message,
            "conversation_history": conversation_history
        }
        logger.info(f"ワークフロー実行開始: initial_state keys={list(initial_state.keys())}")
        
        result = workflow_manager.invoke(initial_state)
        logger.info(f"ワークフロー実行完了: result keys={list(result.keys())}")
        
        ai_response = result.get("ai_response", "申し訳ありません。応答を生成できませんでした。")
        logger.info(f"AI応答生成: length={len(ai_response)}, preview='{ai_response[:100]}...'")
        logger.info(f"LangGraph workflow result: category={result.get('category')}, is_complete={result.get('is_complete')}")
        
        if user_id:
            try:
                repo = DBClient()
                logger.info(f"AI応答保存開始: user_id={user_id}")
                repo.insert_message(user_id, "ai", ai_response)
                logger.info(f"AI応答保存完了: user_id={user_id}")
                # 分析結果を保存（オプション）
                if result.get("department"):
                    dept_info = result['department'].get('dept', '不明')
                    logger.info(f"担当課情報: {dept_info}")
            except Exception as db_error:
                logger.warning(f"AI応答保存エラー（続行）: {db_error}")
        
        logger.info("=" * 60)
        return ai_response
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"APIエラー発生: {type(e).__name__}: {e}", exc_info=True)
        logger.error("=" * 60)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/v1/user-messages")
async def get_user_messages(user_id: str = Query(..., description="ユーザーID"), limit: int = Query(10, ge=1, le=100, description="取得件数")) -> List[Dict]:
    repo = DBClient()
    messages = repo.get_user_messages(user_id=user_id, limit=limit)
    return messages


# 青梅市向け報告内容整理エンドポイント
@app.post("/api/v1/oume/report")
async def post_oume_report(request: Request) -> Dict[str, Any]:
    """
    青梅市向けの報告内容整理エンドポイント
    LINE通報AI管理システム用のPoC
    """
    logger.info("=" * 60)
    logger.info("APIリクエスト受信: /api/v1/oume/report")
    try:
        body = await request.json()
        logger.info(f"リクエストボディ受信: {body}")
    except Exception as e:
        logger.error(f"JSON解析エラー: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    try:
        from app.api.workflow_oume import OumeWorkflowManager
        
        try:
            ai_client = AIClient()
            logger.info("AIClient初期化成功")
        except Exception as e:
            logger.warning(f"AIClient初期化エラー（続行）: {e}")
            from unittest.mock import MagicMock
            ai_client = MagicMock()
            ai_client.create_response = MagicMock(return_value="モック応答")
        
        message = (body.get("message") or "").strip()
        user_id = body.get("user_id")
        conversation_history = body.get("conversation_history", [])
        logger.info(f"メッセージ抽出: message='{message}', user_id='{user_id}'")
        
        if not message:
            logger.warning("空メッセージのため400を返却")
            raise HTTPException(status_code=400, detail="message is required and must be non-empty")
        
        # マルチターン用コンテキスト（前ターンの抽出結果・カテゴリを引き継ぐ場合に使用）
        context = body.get("context") or {}
        prev_extracted = context.get("extracted")
        prev_category = context.get("category")
        if prev_extracted is not None and not isinstance(prev_extracted, dict):
            prev_extracted = None
        if prev_category is not None and not isinstance(prev_category, str):
            prev_category = None
        
        # 青梅市向けワークフローを実行
        logger.info("OumeWorkflowManager初期化開始")
        workflow_manager = OumeWorkflowManager(ai_client)
        logger.info("OumeWorkflowManager初期化完了")
        
        initial_state = {
            "user_message": message,
            "conversation_history": conversation_history,
            "context": {"extracted": prev_extracted, "category": prev_category}
        }
        logger.info(f"ワークフロー実行開始: initial_state keys={list(initial_state.keys())}")
        
        result = workflow_manager.invoke(initial_state)
        logger.info(f"ワークフロー実行完了: result keys={list(result.keys())}")
        
        # レスポンスを構築
        response = {
            "ai_response": result.get("ai_response", "申し訳ありません。応答を生成できませんでした。"),
            "category": result.get("category"),
            "is_complete": result.get("is_complete", False),
            "missing_slots": result.get("missing_slots", []),
            "extracted": result.get("extracted", {}),
            "department": result.get("department"),
            "turn_labels": result.get("turn_labels", [])
        }
        
        logger.info(f"AI応答生成: length={len(response['ai_response'])}, category={response['category']}")
        logger.info("=" * 60)
        
        return response
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"APIエラー発生: {type(e).__name__}: {e}", exc_info=True)
        logger.error("=" * 60)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

