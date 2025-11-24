import json
from typing import Dict, Any
from app.api.ai_client import AIClient
from app.api.state_manager import StateManager

class SituationAnalyzer:
    """
    状況整理コンポーネント。
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
        prompt = self._create_prompt(context)
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
        # This is a simplified prompt. In a real scenario, this should be more robust.
        return f"""
        あなたは自治体サービスの案内チャットボットの「状況整理」コンポーネントです。
        ユーザーの発話とこれまでの会話履歴から、住民プロファイルとサービスニーズを更新してください。

        現在の状態:
        {json.dumps(context['resident_profile'], ensure_ascii=False, indent=2)}
        {json.dumps(context['service_needs'], ensure_ascii=False, indent=2)}

        会話履歴:
        {json.dumps(context['dialog_history'], ensure_ascii=False, indent=2)}

        最新のユーザー発話:
        {context['user_message']}

        以下のJSON形式で出力してください:
        {{
            "resident_profile": {{ ... updated resident profile ... }},
            "service_needs": {{ ... updated service needs ... }}
        }}
        """
