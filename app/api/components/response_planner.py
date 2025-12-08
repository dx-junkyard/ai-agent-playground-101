import json
from pathlib import Path
from typing import Dict, Any, Tuple
from langchain_core.prompts import PromptTemplate
from app.api.ai_client import AIClient

class ResponsePlanner:
    """
    応答設計コンポーネント。
    分析結果と検索結果をもとに、ユーザーへの応答を計画・生成する。
    """
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        # プロンプトファイルのパス解決 (project_root/static/prompts/response_planning.txt)
        prompt_path = Path(__file__).resolve().parents[3] / "static/prompts/response_planning.txt"
        self.prompt_template = PromptTemplate.from_file(prompt_path)

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
        # テンプレートに渡す変数を事前にJSON文字列化
        resident_profile_str = json.dumps(context['resident_profile'], ensure_ascii=False, indent=2)
        service_needs_str = json.dumps(context['service_needs'], ensure_ascii=False, indent=2)
        hypotheses_str = json.dumps(context.get('hypotheses', []), ensure_ascii=False, indent=2)
        retrieval_evidence_str = json.dumps(context.get('retrieval_evidence', {}), ensure_ascii=False, indent=2)

        return self.prompt_template.format(
            resident_profile=resident_profile_str,
            service_needs=service_needs_str,
            hypotheses=hypotheses_str,
            retrieval_evidence=retrieval_evidence_str
        )
