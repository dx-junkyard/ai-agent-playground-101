import os
import json
import hashlib
import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

from app.api.db import DBClient
from app.api.ai_client import AIClient
from config import EMBEDDING_DIMENSION

class CatalogManager:
    """
    サービスカタログの管理を行うコンポーネント。
    データのインポート、Embedding生成、DB/Qdrantへの保存を行う。
    """
    def __init__(self):
        self.db_client = DBClient()
        self.ai_client = AIClient()
        
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.collection_name = "service_catalog"
        self.qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        self.vector_size = EMBEDDING_DIMENSION # Configurable vector size

    def _setup_qdrant_collection(self):
        """Qdrantのコレクションが存在しない場合は作成する"""
        if not self.qdrant_client.collection_exists(self.collection_name):
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

    def import_catalog(self, catalog_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        カタログデータをインポートする。
        
        Args:
            catalog_data (List[Dict[str, Any]]): カタログデータのリスト
            
        Returns:
            Dict[str, Any]: 処理結果（成功数、失敗数など）
        """
        self.db_client.create_service_catalog_table()
        self._setup_qdrant_collection()
        
        success_count = 0
        error_count = 0
        points = []
        
        for entry in catalog_data:
            try:
                # Generate ID (UUID from MD5)
                unique_str = entry.get("タイトル", "") + entry.get("URL", {}).get("items", "")
                md5_hash = hashlib.md5(unique_str.encode()).hexdigest()
                entry_id = str(uuid.UUID(hex=md5_hash))
                entry["id"] = entry_id
                
                # Insert into MySQL
                self.db_client.insert_service_catalog_entry(entry)
                
                # Generate Embedding
                # Embedding対象のテキストを作成（タイトル + サービス内容 + 対象者 + 条件）
                text_to_embed = f"{entry.get('タイトル', '')} {entry.get('サービス内容', '')} {entry.get('対象者', '')} {entry.get('条件・申し込み方法', '')}"
                vector = self.ai_client.get_embedding(text_to_embed)
                
                if vector:
                    points.append(PointStruct(
                        id=entry_id,
                        vector=vector,
                        payload={
                            "title": entry.get("タイトル"),
                            "service_labels": entry.get("サービスラベル", []),
                            "target_labels": entry.get("対象者ラベル", [])
                        }
                    ))
                    success_count += 1
                else:
                    print(f"[!] Failed to generate embedding for {entry.get('タイトル')}")
                    error_count += 1
                    
            except Exception as e:
                print(f"[✗] Error processing entry {entry.get('タイトル')}: {e}")
                error_count += 1

        # Upload to Qdrant
        if points:
            try:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    wait=True,
                    points=points
                )
            except Exception as e:
                print(f"[✗] Qdrant upsert failed: {e}")
                # Note: DB inserts might have succeeded even if Qdrant fails. 
                # In a production system, we might want transactionality or compensation.
                return {"status": "partial_failure", "success": success_count, "error": error_count, "qdrant_error": str(e)}

        return {"status": "completed", "success": success_count, "error": error_count}

    def reset_catalog(self) -> Dict[str, Any]:
        """
        カタログデータをリセットする（DBとQdrantの両方をクリア）。
        
        Returns:
            Dict[str, Any]: 処理結果
        """
        # 1. Truncate MySQL table
        db_success = self.db_client.truncate_service_catalog()
        
        # 2. Delete Qdrant collection
        qdrant_success = False
        try:
            if self.qdrant_client.collection_exists(self.collection_name):
                self.qdrant_client.delete_collection(self.collection_name)
                # Re-create empty collection immediately to be ready for next import
                self._setup_qdrant_collection()
                qdrant_success = True
            else:
                # If collection doesn't exist, we can consider it "cleared" (or just setup new one)
                self._setup_qdrant_collection()
                qdrant_success = True
        except Exception as e:
            print(f"[✗] Qdrant reset failed: {e}")
            qdrant_success = False

        if db_success and qdrant_success:
            return {"status": "success", "message": "Catalog reset successfully."}
        else:
            return {
                "status": "error", 
                "message": "Failed to reset catalog.", 
                "details": {"db_truncated": db_success, "qdrant_cleared": qdrant_success}
            }
