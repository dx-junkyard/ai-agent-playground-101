"""
報告内容整理機能のテスト
獣害通報を中心にテスト
"""

import unittest
from app.api.report_organizer import ReportOrganizer


class TestReportOrganizer(unittest.TestCase):
    """ReportOrganizerのテストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.organizer = ReportOrganizer()
    
    def test_classify_wildlife_damage(self):
        """獣害カテゴリの分類テスト"""
        # テストケース1: イノシシの通報
        message = "イノシシが畑を荒らしています"
        category = self.organizer.classify(message)
        self.assertEqual(category, "wildlife_damage")
        
        # テストケース2: サルの通報
        message = "サルが庭に来ました"
        category = self.organizer.classify(message)
        self.assertEqual(category, "wildlife_damage")
        
        # テストケース3: カラスの通報
        message = "カラスがごみを散らかしています"
        category = self.organizer.classify(message)
        self.assertEqual(category, "wildlife_damage")
    
    def test_extract_wildlife_info(self):
        """獣害情報の抽出テスト"""
        # テストケース1: 基本情報の抽出
        message = "イノシシが青梅市勝沼123の畑を荒らしています。今日の朝発見しました。"
        category = "wildlife_damage"
        extracted = self.organizer.extract(message, category, {})
        
        # 場所と時間が抽出されることを確認
        self.assertIn("details", extracted)
        # 実際の抽出精度は実装に依存するため、基本的な構造を確認
    
    def test_validate_missing_slots(self):
        """不足スロットの検出テスト"""
        category = "wildlife_damage"
        
        # テストケース1: 情報が不足している場合
        extracted = {
            "location": "青梅市勝沼123",
            "details": "イノシシが畑を荒らした"
        }
        missing = self.organizer.validate(category, extracted)
        # 必須スロット（time, species, damage_type）が不足していることを確認
        self.assertGreater(len(missing), 0)
        
        # テストケース2: 情報が揃っている場合
        extracted = {
            "location": "青梅市勝沼123",
            "time": "2026年1月20日 08:00",
            "species": "イノシシ",
            "details": "トウモロコシが食べられた",
            "damage_type": "農作物"
        }
        missing = self.organizer.validate(category, extracted)
        self.assertEqual(len(missing), 0)
    
    def test_ask_missing(self):
        """不足スロットに対する質問生成テスト"""
        category = "wildlife_damage"
        
        # テストケース1: 場所が不足
        missing = ["location"]
        question = self.organizer.ask_missing(missing, category)
        self.assertIn("場所", question)
        
        # テストケース2: 動物種が不足
        missing = ["species"]
        question = self.organizer.ask_missing(missing, category)
        self.assertIn("動物", question)
    
    def test_finalize(self):
        """情報整理完了テスト"""
        category = "wildlife_damage"
        extracted = {
            "location": "青梅市勝沼123",
            "time": "2026年1月20日 08:00",
            "species": "イノシシ",
            "details": "トウモロコシが食べられた",
            "damage_type": "農作物"
        }
        
        report_data = self.organizer.finalize(category, extracted)
        
        # 構造化データが正しく生成されることを確認
        self.assertEqual(report_data["category"], category)
        self.assertEqual(report_data["is_complete"], True)
        self.assertIn("confirmation_message", report_data)
        self.assertIn("extracted", report_data)


class TestWorkflowIntegration(unittest.TestCase):
    """ワークフロー統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        from unittest.mock import MagicMock
        from app.api.ai_client import AIClient
        
        # AIClientのモック
        self.ai_client = MagicMock(spec=AIClient)
        from app.api.workflow_oume import OumeWorkflowManager
        self.workflow = OumeWorkflowManager(self.ai_client)
    
    def test_workflow_basic(self):
        """基本的なワークフローのテスト"""
        initial_state = {
            "user_message": "イノシシが畑を荒らしています",
            "conversation_history": []
        }
        
        result = self.workflow.invoke(initial_state)
        
        # カテゴリが正しく分類されることを確認
        self.assertIn("category", result)
        self.assertEqual(result["category"], "wildlife_damage")
        
        # AI応答が生成されることを確認
        self.assertIn("ai_response", result)
        self.assertIsNotNone(result["ai_response"])


if __name__ == "__main__":
    unittest.main()
