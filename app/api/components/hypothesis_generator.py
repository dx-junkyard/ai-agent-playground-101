import json
from typing import Dict, Any
from app.api.ai_client import AIClient

class HypothesisGenerator:
    """
    仮説生成コンポーネント。
    整理された状況情報から、必要なサービス候補群を仮説化する。
    """
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client

    def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        現在のコンテキストに基づいて仮説を生成する。

        Args:
            context (Dict[str, Any]): 現在の会話コンテキスト

        Returns:
            Dict[str, Any]: 仮説が追加されたコンテキスト
        """
        prompt = self._create_prompt(context)
        result = self.ai_client.generate_response(prompt)

        if result and "hypotheses" in result:
            context["hypotheses"] = result["hypotheses"]
        
        return context

    def _create_prompt(self, context: Dict[str, Any]) -> str:
        """
        LLMへのプロンプトを作成する。
        """
        return f"""
        あなたは自治体サービスの案内チャットボットの「仮説生成」コンポーネントです。
        現在の住民プロファイルとサービスニーズから、必要なサービス候補群を仮説化してください。

        現在の状態:
        {json.dumps(context['resident_profile'], ensure_ascii=False, indent=2)}
        {json.dumps(context['service_needs'], ensure_ascii=False, indent=2)}

        以下のJSON形式で出力してください:
        {{
            "hypotheses": [
                {{
                    "id": "H1",
                    "need_label": "ニーズのラベル",
                    "likely_services": ["サービス名候補1", "サービス名候補2"],
                    "confidence": 0.0から1.0の信頼度,
                    "missing_info": ["不足している情報1", "不足している情報2"],
                    "should_call_rag": true または false
                }}
            ]
        }}
        """
