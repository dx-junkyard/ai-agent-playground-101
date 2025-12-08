from copy import deepcopy
from typing import Any, Dict, List, Optional

class StateManager:
    DEFAULT_RESIDENT_PROFILE: Dict[str, Any] = {
        "basic": {
            "age": None,
            "gender": None,
            "address_area": None,
            "family_structure": None,
            "household_type": None,
        },
        "lifestyle": {
            "employment_status": None,
            "work_style": None,
            "recent_life_events": [],
        },
        "economic": {
            "income_level": None,
            "financial_difficulty": False,
        },
        "health": {
            "health_issues": [],
            "disabilities": [],
            "mobility": "public_transport_only",
        },
        "behavior": {
            "frequent_places": [],
            "outing_frequency": None,
            "hobbies": [],
            "active_hours": "morning_person",
        },
        "hypothesis": None,
        "labels": [],
    }

    DEFAULT_SERVICE_NEEDS: Dict[str, Any] = {
        "explicit_needs": {
            "current_problems": [],
            "desired_services": [],
            "goals": [],
        },
        "implicit_needs": {
            "inferred_issues": [],
            "risk_indicators": [],
        },
        "constraints": {
            "time": [],
            "distance": "within_2km",
            "budget_preference": "low_cost",
        },
        "priority": {
            "top_priority_area": None,
            "secondary_priorities": [],
        },
        "hypothesis": None,
        "labels": [],
    }

    @staticmethod
    def deep_merge(default: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        辞書を再帰的にマージする。
        
        Args:
            default (Dict[str, Any]): デフォルト値の辞書
            updates (Dict[str, Any]): 更新値の辞書
            
        Returns:
            Dict[str, Any]: マージされた辞書
        """
        result = deepcopy(default)
        if not isinstance(updates, dict):
            return result
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = StateManager.deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @classmethod
    def get_state_with_defaults(cls, stored_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        保存された状態にデフォルト値を適用して取得する。
        
        Args:
            stored_state (Optional[Dict[str, Any]]): 保存された状態
            
        Returns:
            Dict[str, Any]: デフォルト値が適用された状態
        """
        resident_updates = (stored_state or {}).get("resident_profile", {})
        service_updates = (stored_state or {}).get("service_needs", {})
        resident_profile = cls.deep_merge(cls.DEFAULT_RESIDENT_PROFILE, resident_updates)
        service_needs = cls.deep_merge(cls.DEFAULT_SERVICE_NEEDS, service_updates)
        return {
            "resident_profile": resident_profile,
            "service_needs": service_needs,
        }

    @classmethod
    def normalize_analysis(cls, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        分析結果を正規化し、デフォルト構造に合わせる。
        
        Args:
            analysis (Dict[str, Any]): 分析結果
            
        Returns:
            Optional[Dict[str, Any]]: 正規化された分析結果、またはNone
        """
        resident_profile = analysis.get("resident_profile")
        service_needs = analysis.get("service_needs")
        
        if isinstance(resident_profile, dict) and isinstance(service_needs, dict):
            normalized_resident = cls.deep_merge(cls.DEFAULT_RESIDENT_PROFILE, resident_profile)
            normalized_service = cls.deep_merge(cls.DEFAULT_SERVICE_NEEDS, service_needs)
            normalized_analysis = {**analysis}
            normalized_analysis["resident_profile"] = normalized_resident
            normalized_analysis["service_needs"] = normalized_service
            return normalized_analysis
        return None

    @classmethod
    def init_conversation_context(
        cls, 
        user_message: str, 
        dialog_history: List[Dict[str, Any]], 
        resident_profile: Dict[str, Any], 
        service_needs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        会話コンテキストを初期化する。
        
        Args:
            user_message (str): ユーザーのメッセージ
            dialog_history (List[Dict[str, Any]]): 会話履歴
            resident_profile (Dict[str, Any]): 住民プロファイル
            service_needs (Dict[str, Any]): サービスニーズ
            
        Returns:
            Dict[str, Any]: 初期化されたコンテキスト
        """
        return {
            "user_message": user_message,
            "dialog_history": dialog_history,
            "resident_profile": cls.deep_merge(cls.DEFAULT_RESIDENT_PROFILE, resident_profile),
            "service_needs": cls.deep_merge(cls.DEFAULT_SERVICE_NEEDS, service_needs),
            "hypotheses": [],
            "retrieval_evidence": {},
            "conversation_summary": "",
            "bot_message": None
        }
