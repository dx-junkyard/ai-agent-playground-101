from fastapi import FastAPI, HTTPException, UploadFile, File
import logging
import json
import os
from dotenv import load_dotenv

from app.api.components.catalog_manager import CatalogManager

# .env ファイルを読み込む
load_dotenv()

app = FastAPI()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/api/v1/service-catalog/import")
async def import_service_catalog(file: UploadFile = File(...)):
    """
    サービスカタログ（JSON）をインポートする。
    EmbeddingはLLM APIを使用して生成される。
    """
    try:
        content = await file.read()
        catalog_data = json.loads(content)
        
        if not isinstance(catalog_data, list):
            raise HTTPException(status_code=400, detail="JSON must be a list of service entries")
            
        manager = CatalogManager()
        result = manager.import_catalog(catalog_data)
        
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/service-catalog/reset")
async def reset_service_catalog():
    """
    サービスカタログをリセットする（DBとQdrantをクリア）。
    """
    try:
        manager = CatalogManager()
        result = manager.reset_catalog()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result)
            
        return result
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("admin:app", host="0.0.0.0", port=8000, reload=True)
