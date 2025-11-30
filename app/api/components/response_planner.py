import json
from typing import Dict, Any, Tuple
from app.api.ai_client import AIClient

class ResponsePlanner:
    """
    応答設計コンポーネント。
    分析結果と検索結果をもとに、ユーザーへの応答を計画・生成する。
    """
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client

    def plan_response(self, context: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        応答を計画し、最終的なメッセージを生成する。

        Args:
            context (Dict[str, Any]): 現在の会話コンテキスト

        Returns:
            Tuple[Dict[str, Any], str]: 応答計画が追加されたコンテキストと、ボットのメッセージ
        """
        prompt = self._create_prompt(context)
        result = self.ai_client.generate_response(prompt)

        bot_message = "申し訳ありません、うまく応答を生成できませんでした。"
        if result:
            context["response_plan"] = result.get("response_plan")
            # In a real system, we might use a template engine or another LLM call to generate the natural language message from the plan.
            # Here, we'll assume the LLM also returns the message or we construct it simply.
            # For simplicity, let's ask the LLM to include the message in the JSON or just use the plan to generate it.
            # Let's modify the prompt to ask for the message text as well.
            bot_message = result.get("message_text", bot_message)
        
        return context, bot_message

    def _create_prompt(self, context: Dict[str, Any]) -> str:
        """
        LLMへのプロンプトを作成する。
        """
        return f"""
        あなたは自治体サービスの案内チャットボットの「応答設計」コンポーネントです。
        これまでの分析結果と検索結果をもとに、ユーザーへの応答を生成してください。

        現在の状態:
        {json.dumps(context['resident_profile'], ensure_ascii=False, indent=2)}
        {json.dumps(context['service_needs'], ensure_ascii=False, indent=2)}

        仮説:
        {json.dumps(context.get('hypotheses', []), ensure_ascii=False, indent=2)}

        検索結果:
        {json.dumps(context.get('retrieval_evidence', {}), ensure_ascii=False, indent=2)}

        以下のJSON形式で出力してください:
        {{
            "response_plan": {{
                "main_hypothesis_id": "対象とする仮説ID",
                "cases": [
                    {{
                        "label": "ケース分け（例：未就学児の場合）",
                        "services_to_show": ["提示するサービス名"]
                    }}
                ],
                "followup_questions": [
                    {{
                        "id": "Q_id",
                        "text": "追加質問のテキスト"
                    }}
                ]
            }},
            "message_text": "ユーザーに表示する最終的な応答メッセージテキスト"
        }}
        """
