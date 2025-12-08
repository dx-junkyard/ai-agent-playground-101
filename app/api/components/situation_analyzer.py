import json
from pathlib import Path
from typing import Dict, Any, List
from langchain_core.prompts import PromptTemplate
from app.api.ai_client import AIClient
from app.api.state_manager import StateManager

class SituationAnalyzer:
    """
    状況整理コンポーネント。
    static/prompts/situation_analysis.txt で定義されたプロンプトを使用して、
    ユーザーの発話と会話履歴をもとに、住民プロファイルとサービスニーズを更新する。
    """
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        # プロンプトファイルのパス解決 (project_root/static/prompts/situation_analysis.txt)
        prompt_path = Path(__file__).resolve().parents[3] / "static/prompts/situation_analysis.txt"
        self.prompt_template = PromptTemplate.from_file(prompt_path)

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        現状の分析を実行する。
        static/prompts/situation_analysis.txt で定義されたプロンプトを使用して、
        AIClient経由で分析を行う。

        Args:
            context (Dict[str, Any]): 現在の会話コンテキスト

        Returns:
            Dict[str, Any]: 更新されたコンテキスト
        """
        prompt = self._create_prompt(context)
        
        # Use generic generate_response instead of analyze_interaction
        analysis_result = self.ai_client.generate_response(prompt)

        if analysis_result:
            normalized_analysis = StateManager.normalize_analysis(analysis_result)
            if normalized_analysis:
                context["resident_profile"] = normalized_analysis["resident_profile"]
                context["service_needs"] = normalized_analysis["service_needs"]
        return context

    def _create_prompt(self, context: Dict[str, Any]) -> str:
        """
        LLMへのプロンプトを作成する。
        """
        current_state = {
            "resident_profile": context.get("resident_profile", {}),
            "service_needs": context.get("service_needs", {})
        }
        
        state_dump = json.dumps(current_state, ensure_ascii=False, indent=2)
        history_text = self._format_history(context.get("dialog_history", []))
        latest_user_message = context.get("user_message", "")

        return self.prompt_template.format(
            current_state=state_dump,
            conversation_summary=history_text,
            latest_user_message=latest_user_message
        )

    def _format_history(self, history: List[Dict[str, Any]]) -> str:
        """
        会話履歴をテキスト形式に整形する。
        """
        if not history:
            return "会話履歴はまだありません。"
        lines: List[str] = []
        for item in history:
            role = "ユーザー" if item.get("role") == "user" else "AI"
            message = item.get("message", "")
            lines.append(f"{role}: {message}")
        return "\n".join(lines)