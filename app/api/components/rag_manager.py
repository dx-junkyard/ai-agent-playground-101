import os
from typing import Dict, Any, List
from qdrant_client import QdrantClient
from app.api.db import DBClient
from app.api.ai_client import AIClient

class RAGManager:
    """
    RAG（検索拡張生成）管理コンポーネント。
    必要な仮説に対し、サービスカタログ等から候補情報を取得する。
    """
    def __init__(self):
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.collection_name = "service_catalog"
        self.qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        self.db_client = DBClient()
        # We need an AIClient to generate embeddings for queries
        # Assuming AIClient has a method for embeddings or we use OpenAI directly here
        # For consistency, let's instantiate AIClient if it has embedding capability, 
        # but looking at ai_client.py it might be just for chat.
        # Let's use OpenAI client directly for embeddings as in the ingestion script
        # or better, check if AIClient supports it. 
        # Since we don't have AIClient passed in __init__ in workflow.py, we might need to instantiate it or use openai directly.
        # For now, let's assume we use openai directly for query embedding to match the ingestion script's logic (which used pre-computed embeddings but implies openai).
        from openai import OpenAI
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def retrieve_knowledge(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        仮説に基づいて知識を検索する。

        Args:
            context (Dict[str, Any]): 現在の会話コンテキスト

        Returns:
            Dict[str, Any]: 検索結果が追加されたコンテキスト
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
        return self.openai_client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

    def _search_services(self, hypothesis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        仮説に基づいてサービスを検索する。
        """
        query_text = hypothesis.get("reasoning", "") or hypothesis.get("hypothesis", "")
        if not query_text:
            return []

        try:
            query_vector = self._get_embedding(query_text)
            
            search_result = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=3
            )
            
            results = []
            for hit in search_result.points:
                service_id = hit.id
                # Fetch full details from MySQL
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
