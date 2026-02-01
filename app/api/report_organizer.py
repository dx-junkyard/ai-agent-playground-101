"""
報告内容整理機能
AIが対話形式で通報内容をヒアリングし、必要な情報を収集・整理する
"""

from typing import Dict, Any, List, Optional
import logging
import re
from datetime import datetime

from app.api.config.oume_city_config import (
    CATEGORIES,
    SLOT_DEFINITIONS,
    SLOT_PRIORITY,
    CATEGORY_SPECIFIC_QUESTIONS
)

logger = logging.getLogger(__name__)


class CategoryManager:
    """カテゴリ管理クラス"""
    
    def __init__(self):
        self.categories = {cat["key"]: cat for cat in CATEGORIES}
    
    def find_category(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        ユーザーメッセージからカテゴリを判定
        
        Args:
            user_message: ユーザーのメッセージ
            
        Returns:
            カテゴリ定義（見つからない場合はNone）
        """
        user_message_lower = user_message.lower()
        
        # キーワードベースで分類
        for category in CATEGORIES:
            keywords = category.get("keywords", [])
            if any(kw in user_message_lower for kw in keywords):
                logger.info(f"カテゴリ判定: {category['key']} ({category['name']})")
                return category
        
        # デフォルトは"other"
        logger.info("カテゴリ判定: other (デフォルト)")
        return self.categories.get("other")
    
    def get_category(self, category_key: str) -> Optional[Dict[str, Any]]:
        """カテゴリキーからカテゴリ定義を取得"""
        return self.categories.get(category_key)
    
    def get_required_slots(self, category_key: str) -> List[str]:
        """カテゴリの必須スロットを取得"""
        category = self.get_category(category_key)
        if not category:
            return []
        return category.get("required_slots", [])


class SlotManager:
    """スロット管理クラス"""
    
    def __init__(self):
        self.slot_definitions = SLOT_DEFINITIONS
        self.slot_priority = SLOT_PRIORITY
    
    def get_slot_definition(self, slot_key: str) -> Optional[Dict[str, Any]]:
        """スロット定義を取得"""
        return self.slot_definitions.get(slot_key)
    
    def get_question(self, slot_key: str, category_key: Optional[str] = None) -> str:
        """
        スロットに対する質問文を生成
        
        Args:
            slot_key: スロットキー
            category_key: カテゴリキー（カテゴリ固有の質問がある場合）
            
        Returns:
            質問文
        """
        # カテゴリ固有の質問を優先
        if category_key and category_key in CATEGORY_SPECIFIC_QUESTIONS:
            category_questions = CATEGORY_SPECIFIC_QUESTIONS[category_key]
            if slot_key in category_questions:
                return category_questions[slot_key]
        
        # デフォルトの質問
        slot_def = self.get_slot_definition(slot_key)
        if slot_def:
            return slot_def.get("question", f"{slot_key}について教えてください。")
        
        return f"{slot_key}について教えてください。"
    
    def extract_slot_value(self, slot_key: str, user_message: str) -> Optional[Any]:
        """
        ユーザーメッセージからスロット値を抽出
        
        Args:
            slot_key: スロットキー
            user_message: ユーザーのメッセージ
            
        Returns:
            抽出された値（抽出できない場合はNone）
        """
        slot_def = self.get_slot_definition(slot_key)
        if not slot_def:
            return None
        
        extraction_keywords = slot_def.get("extraction_keywords", [])
        slot_type = slot_def.get("type")
        
        # キーワードベースの簡易抽出
        if any(kw in user_message for kw in extraction_keywords):
            if slot_type == "enum":
                # 選択肢から該当するものを探す
                options = slot_def.get("options", [])
                for option in options:
                    if option in user_message:
                        return option
            elif slot_type == "location":
                # 住所パターンを抽出（簡易版）
                # 実際はより高度な抽出が必要
                return user_message
            elif slot_type == "datetime":
                # 日時パターンを抽出（簡易版）
                return user_message
            else:
                return user_message
        
        return None
    
    def validate_slot_value(self, slot_key: str, value: Any) -> bool:
        """
        スロット値の検証
        
        Args:
            slot_key: スロットキー
            value: 検証する値
            
        Returns:
            検証結果（True: 有効、False: 無効）
        """
        slot_def = self.get_slot_definition(slot_key)
        if not slot_def:
            return False
        
        slot_type = slot_def.get("type")
        
        if slot_type == "enum":
            options = slot_def.get("options", [])
            return value in options
        elif slot_type == "url":
            # URLパターンの簡易検証
            return isinstance(value, str) and ("http://" in value or "https://" in value)
        elif slot_type == "text":
            return isinstance(value, str) and len(value.strip()) > 0
        elif slot_type == "location":
            return isinstance(value, str) and len(value.strip()) > 0
        elif slot_type == "datetime":
            return isinstance(value, str) and len(value.strip()) > 0
        
        return True


class QuestionGenerator:
    """質問生成クラス"""
    
    def __init__(self, category_manager: CategoryManager, slot_manager: SlotManager):
        self.category_manager = category_manager
        self.slot_manager = slot_manager
    
    def generate_question(self, missing_slots: List[str], category_key: Optional[str] = None) -> str:
        """
        不足スロットに対する質問を生成
        
        Args:
            missing_slots: 不足しているスロットのリスト
            category_key: カテゴリキー
            
        Returns:
            質問文
        """
        if not missing_slots:
            return "ありがとうございます。情報を確認しました。"
        
        # 優先順位に従って最初の不足スロットを質問
        # SLOT_PRIORITYに従ってソート
        sorted_slots = sorted(
            missing_slots,
            key=lambda s: self.slot_manager.slot_priority.index(s) 
            if s in self.slot_manager.slot_priority 
            else 999
        )
        
        first_missing = sorted_slots[0]
        question = self.slot_manager.get_question(first_missing, category_key)
        
        logger.info(f"質問生成: {first_missing} -> {question[:50]}...")
        return question
    
    def generate_confirmation(self, extracted: Dict[str, Any], category_key: str) -> str:
        """
        収集した情報の確認メッセージを生成
        
        Args:
            extracted: 抽出された情報
            category_key: カテゴリキー
            
        Returns:
            確認メッセージ
        """
        category = self.category_manager.get_category(category_key)
        if not category:
            return "情報を確認しました。"
        
        category_name = category.get("name", "通報")
        parts = [f"{category_name}の通報内容を確認しました。"]
        
        # 主要な情報を列挙
        important_slots = ["location", "time", "species", "damage_type"]
        for slot_key in important_slots:
            if slot_key in extracted:
                slot_def = self.slot_manager.get_slot_definition(slot_key)
                if slot_def:
                    slot_name = slot_def.get("question", slot_key).split("を")[0] if "を" in slot_def.get("question", "") else slot_key
                    parts.append(f"- {slot_name}: {extracted[slot_key]}")
        
        parts.append("\n担当部署に連絡いたします。")
        return "\n".join(parts)


class ReportOrganizer:
    """報告内容整理機能のメインクラス"""
    
    def __init__(self):
        self.category_manager = CategoryManager()
        self.slot_manager = SlotManager()
        self.question_generator = QuestionGenerator(
            self.category_manager,
            self.slot_manager
        )
    
    def classify(self, user_message: str) -> Optional[str]:
        """
        カテゴリを分類
        
        Args:
            user_message: ユーザーのメッセージ
            
        Returns:
            カテゴリキー
        """
        category = self.category_manager.find_category(user_message)
        return category["key"] if category else "other"
    
    def extract(self, user_message: str, category_key: str, existing_extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        ユーザーメッセージから情報を抽出
        
        Args:
            user_message: ユーザーのメッセージ
            category_key: カテゴリキー
            existing_extracted: 既に抽出されている情報
            
        Returns:
            抽出された情報（既存情報とマージ）
        """
        extracted = existing_extracted.copy()
        category = self.category_manager.get_category(category_key)
        
        if not category:
            return extracted
        
        # 必須スロットとオプションスロットを取得
        all_slots = category.get("required_slots", []) + category.get("optional_slots", [])
        
        # 各スロットを抽出
        for slot_key in all_slots:
            if slot_key not in extracted:  # 既に抽出済みの場合はスキップ
                value = self.slot_manager.extract_slot_value(slot_key, user_message)
                if value:
                    # 検証
                    if self.slot_manager.validate_slot_value(slot_key, value):
                        extracted[slot_key] = value
                        logger.info(f"スロット抽出: {slot_key} = {value}")
        
        # detailsは常にユーザーメッセージから抽出（簡易版）
        if "details" not in extracted:
            extracted["details"] = user_message
        
        return extracted
    
    def validate(self, category_key: str, extracted: Dict[str, Any]) -> List[str]:
        """
        不足スロットを検出
        
        Args:
            category_key: カテゴリキー
            extracted: 抽出された情報
            
        Returns:
            不足しているスロットのリスト
        """
        required_slots = self.category_manager.get_required_slots(category_key)
        missing_slots = []
        
        for slot_key in required_slots:
            if slot_key not in extracted or not extracted[slot_key]:
                missing_slots.append(slot_key)
        
        logger.info(f"検証結果: 不足スロット={missing_slots}")
        return missing_slots
    
    def ask_missing(self, missing_slots: List[str], category_key: str) -> str:
        """
        不足スロットに対する質問を生成
        
        Args:
            missing_slots: 不足しているスロットのリスト
            category_key: カテゴリキー
            
        Returns:
            質問文
        """
        return self.question_generator.generate_question(missing_slots, category_key)
    
    def finalize(self, category_key: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        情報整理を完了し、最終的な構造化データを返す
        
        Args:
            category_key: カテゴリキー
            extracted: 抽出された情報
            
        Returns:
            整理された通報データ
        """
        category = self.category_manager.get_category(category_key)
        if not category:
            category = self.category_manager.get_category("other")
        
        # 最終的な構造化データ
        report_data = {
            "category": category_key,
            "category_name": category.get("name", "その他"),
            "extracted": extracted,
            "timestamp": datetime.now().isoformat(),
            "is_complete": True
        }
        
        # 確認メッセージを生成
        confirmation_message = self.question_generator.generate_confirmation(extracted, category_key)
        report_data["confirmation_message"] = confirmation_message
        
        logger.info(f"情報整理完了: category={category_key}, slots={list(extracted.keys())}")
        return report_data
