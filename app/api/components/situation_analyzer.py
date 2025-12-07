import json
from typing import Dict, Any, List
from app.api.ai_client import AIClient
from app.api.state_manager import StateManager

class SituationAnalyzer:
    """
    状況整理コンポーネント。
    static/prompt.txt で定義されたプロンプトを使用して、
    ユーザーの発話と会話履歴をもとに、住民プロファイルとサービスニーズを更新する。
    """
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        ユーザーのメッセージを分析し、コンテキストを更新する。

        Args:
            context (Dict[str, Any]): 現在の会話コンテキスト

        Returns:
            Dict[str, Any]: 更新されたコンテキスト
        """
        current_state = {
            "resident_profile": context.get("resident_profile", {}),
            "service_needs": context.get("service_needs", {})
        }
        
        # Use AIClient's analyze_interaction which uses prompt.txt
        analysis_result = self.ai_client.analyze_interaction(
            history=context.get("dialog_history", []),
            current_state=current_state,
            latest_user_message=context.get("user_message", "")
        )

        if analysis_result:
            normalized_analysis = StateManager.normalize_analysis(analysis_result)
            if normalized_analysis:
                context["resident_profile"] = normalized_analysis["resident_profile"]
                context["service_needs"] = normalized_analysis["service_needs"]
        return context