import requests
import logging
from pathlib import Path
from config import AI_MODEL, AI_URL

# ログ設定（必要に応じてレベルを DEBUG に変更可能）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)
class AIClient:
    """
    ユーザーの発言に対して、会話を盛り上げる返答を生成するクラス。
    """

    PROMPT_PATH = Path(__file__).resolve().parents[2] / "static" / "prompt.txt"

    def __init__(self, model: str = AI_MODEL, base_url: str = AI_URL, prompt_path: Path = None):
        self.model = model
        self.api_url = f"{base_url}/api/generate"
        self.prompt_path = Path(prompt_path) if prompt_path else self.PROMPT_PATH
        logging.info(
            f"AIClient initialized with model: {model} and endpoint: {self.api_url}, prompt: {self.prompt_path}"
        )

    def _load_prompt(self) -> str:
        try:
            return self.prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read prompt template: {e}")
            return "以下はユーザーの発言です。会話が盛り上がるよう、自然な返答をしてください。\n【ユーザー発言】:\n{user_message}\n"

    def create_response(self, user_message: str, conversation_history: str = "") -> str:
        """
        ユーザーの発言に対するAIの回答を生成
        """

        prompt_template = self._load_prompt()
        history_block = conversation_history.strip() or "（まだ会話履歴はありません）"
        prompt = prompt_template.format(
            user_message=user_message,
            conversation_history=history_block,
        )
        logger.info(f"Prompt sent to LLM: {prompt}")

        try:
            response = requests.post(self.api_url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            })
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            logging.error(f"[✗] 返答生成失敗: {e}")
            return "すみません、AIが回答できませんでした。"
