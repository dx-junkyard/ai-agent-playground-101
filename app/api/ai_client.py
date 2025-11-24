import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI

from config import AI_MODEL, AI_URL

# ログ設定（必要に応じてレベルを DEBUG に変更可能）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


class AIClient:
    """LLM を利用してユーザー情報の整理と次の質問を生成するクラス。"""

    PROMPT_PATH = Path(__file__).resolve().parents[2] / "static" / "prompt.txt"

    def __init__(self, model: str = AI_MODEL, base_url: str = AI_URL, prompt_path: Optional[Path] = None) -> None:
        self.model = model
        self.api_url = f"{base_url}/api/generate"
        self.prompt_path = Path(prompt_path) if prompt_path else self.PROMPT_PATH
        
        self.openai_client = None
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
            logger.info("AIClient initialized with OpenAI API")
        else:
            logger.info(
                "AIClient initialized with local LLM model: %s endpoint: %s prompt: %s",
                model,
                self.api_url,
                self.prompt_path,
            )

    def _load_prompt(self) -> str:
        try:
            return self.prompt_path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - ログ用
            logger.error("Failed to read prompt template: %s", exc)
            return (
                "あなたは住民との対話を分析するアシスタントです。"
                "\n現在の状態: {current_state}\n会話履歴: {conversation_history}\n最新発言: {latest_user_message}"
            )

    @staticmethod
    def _format_history(history: List[Dict[str, Any]]) -> str:
        if not history:
            return "会話履歴はまだありません。"
        lines: List[str] = []
        for item in history:
            role = "ユーザー" if item.get("role") == "user" else "AI"
            message = item.get("message", "")
            lines.append(f"{role}: {message}")
        return "\n".join(lines)

    @staticmethod
    def _extract_json(payload: str) -> Optional[Dict[str, Any]]:
        text = payload.strip()
        if not text:
            return None

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, count=1).strip()
            if text.endswith("```"):
                text = text[:-3].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return None
        return None

    def analyze_interaction(
        self,
        history: List[Dict[str, Any]],
        current_state: Dict[str, Any],
        latest_user_message: str,
    ) -> Optional[Dict[str, Any]]:
        """
        ユーザーとの対話を分析する（旧メソッド）。
        
        Args:
            history (List[Dict[str, Any]]): 会話履歴
            current_state (Dict[str, Any]): 現在の状態
            latest_user_message (str): 最新のユーザーメッセージ
            
        Returns:
            Optional[Dict[str, Any]]: 分析結果
        """
        prompt_template = self._load_prompt()
        state_dump = json.dumps(current_state, ensure_ascii=False, indent=2)
        history_text = self._format_history(history)
        prompt = prompt_template.format(
            current_state=state_dump,
            conversation_history=history_text,
            latest_user_message=latest_user_message,
        )
        logger.info("Prompt sent to LLM: %s", prompt)

        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",  # You might want to make this configurable
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."}, # System prompt could be refined
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                raw_text = response.choices[0].message.content.strip()
                logger.info("OpenAI response raw text: %s", raw_text)
            except Exception as exc:
                logger.error("[✗] OpenAI API request failed: %s", exc)
                return None
        else:
            try:
                response = requests.post(
                    self.api_url,
                    json={"model": self.model, "prompt": prompt, "stream": False},
                    timeout=120,
                )
                response.raise_for_status()
                raw_text = response.json().get("response", "").strip()
                logger.info("Local LLM response raw text: %s", raw_text)
            except Exception as exc:  # pragma: no cover - 通信失敗時のログ
                logger.error("[✗] LLM へのリクエストに失敗しました: %s", exc)
                return None

        parsed = self._extract_json(raw_text)
        if parsed is None:
            logger.error("LLM からの応答を JSON として解析できませんでした。")
        return parsed

    def generate_response(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        LLMを使用して応答を生成する汎用メソッド。
        
        Args:
            prompt (str): プロンプト
            
        Returns:
            Optional[Dict[str, Any]]: 生成されたJSONレスポンス
        """
        logger.info("Prompt sent to LLM: %s", prompt)

        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                raw_text = response.choices[0].message.content.strip()
                logger.info("OpenAI response raw text: %s", raw_text)
            except Exception as exc:
                logger.error("[✗] OpenAI API request failed: %s", exc)
                return None
        else:
            try:
                response = requests.post(
                    self.api_url,
                    json={"model": self.model, "prompt": prompt, "stream": False},
                    timeout=120,
                )
                response.raise_for_status()
                raw_text = response.json().get("response", "").strip()
                logger.info("Local LLM response raw text: %s", raw_text)
            except Exception as exc:
                logger.error("[✗] LLM へのリクエストに失敗しました: %s", exc)
                return None

        parsed = self._extract_json(raw_text)
        if parsed is None:
            logger.error("LLM からの応答を JSON として解析できませんでした。")
        return parsed
