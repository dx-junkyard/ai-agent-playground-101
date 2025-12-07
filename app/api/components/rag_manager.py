import os
from typing import Dict, Any, List
from qdrant_client import QdrantClient
from app.api.db import DBClient
from app.api.ai_client import AIClient

class RAGManager:
    """
    RAG（検索拡張生成）管理コンポーネント。
    """
    def __init__(self, ai_client: AIClient):
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.collection_name = "service_catalog"
        self.qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        self.db_client = DBClient()
        self.ai_client = ai_client

    def retrieve_knowledge(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        仮説に基づいて知識を検索する。
        """
        hypotheses = context.get("hypotheses", [])
        retrieval_evidence = {"service_candidates": []}

        for hypothesis in hypotheses:
            if hypothesis.get("should_call_rag"):
                candidates = self._search_services(hypothesis)
                retrieval_evidence["service_candidates"].extend(candidates)
        
        context["retrieval_evidence"] = retrieval_evidence
        return context

    def _get_embedding(self, text: str) -> List[float]:
        text = text.replace("\n", " ")
        # Changed from self.openai_client to self.ai_client based on the __init__ modification
        return self.ai_client.get_embedding(text)

    def _search_services(self, hypothesis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        仮説に基づいてサービスを検索する。
        """
        # 修正箇所: search_query を優先的に使用
        query_text = hypothesis.get("search_query")
        
        # search_queryが無い場合のフォールバック（reasoning や likely_services を連結）
        if not query_text:
            parts = []
            if hypothesis.get("reasoning"):
                parts.append(hypothesis.get("reasoning"))
            if hypothesis.get("likely_services"):
                parts.extend(hypothesis.get("likely_services"))
            query_text = " ".join(parts)

        if not query_text:
            return []

        try:
            # クエリのベクトル化と検索
            query_vector = self._get_embedding(query_text)
            
            search_result = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=3
            )
            
            results = []
            for hit in search_result.points:
                service_id = hit.id
                service_details = self.db_client.get_service_by_id(service_id)
                
                if service_details:
                    results.append({
                        "hypothesis_id": hypothesis.get("id"),
                        "service_id": service_id,
                        "name": service_details.get("title"),
                        "summary": service_details.get("service_content") or service_details.get("conditions") or "詳細なし",
                        "conditions": {
                            "target": service_details.get("target"),
                            "conditions": service_details.get("conditions")
                        },
                        "score": hit.score
                    })
            return results
            
        except Exception as e:
            print(f"[✗] RAG Search Error: {e}")
            return []