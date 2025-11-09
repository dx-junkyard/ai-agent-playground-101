import logging
from pathlib import Path
import os

from openai import OpenAI

from config import AI_MODEL, AI_API_BASE

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

    def __init__(self, model: str = AI_MODEL, prompt_path: Path = None):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY が設定されていません。応答生成に失敗します。")
        self.model = model
        self.prompt_path = Path(prompt_path) if prompt_path else self.PROMPT_PATH
        self.client = OpenAI(api_key=api_key, base_url=AI_API_BASE)
        logger.info(
            "AIClient initialized with OpenAI model: %s (base_url=%s), prompt: %s",
            model,
            AI_API_BASE or "default",
            self.prompt_path,
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
        logger.info(f"Prompt sent to OpenAI model {self.model}: {prompt}")

        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                temperature=0.6,
            )
            output_text = response.output_text.strip()
            output_text = output_text.replace("\\n", "\n")
            logger.debug("Raw OpenAI response: %s", output_text)
            return output_text
        except Exception as e:
            logger.error(f"[✗] 返答生成失敗 (OpenAI): {e}")
            return "すみません、現在応答を生成できませんでした。少し時間をおいてお試しください。"
