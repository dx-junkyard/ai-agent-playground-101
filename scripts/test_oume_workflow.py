"""
青梅市向けワークフローのテストスクリプト
対話的なテストを実行
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import MagicMock
from app.api.workflow_oume import OumeWorkflowManager
from app.api.ai_client import AIClient


def simulate_conversation():
    """対話シミュレーション"""
    print("=" * 60)
    print("青梅市向け報告内容整理機能 テスト")
    print("=" * 60)
    
    # AIClientのモック
    ai_client = MagicMock(spec=AIClient)
    workflow = OumeWorkflowManager(ai_client)
    
    # テストケース1: 獣害通報（情報不足）
    print("\n【テストケース1】獣害通報（情報不足）")
    print("-" * 60)
    
    initial_state = {
        "user_message": "イノシシが畑を荒らしています",
        "conversation_history": []
    }
    
    result = workflow.invoke(initial_state)
    print(f"カテゴリ: {result.get('category')}")
    print(f"AI応答: {result.get('ai_response')}")
    print(f"不足スロット: {result.get('missing_slots')}")
    print(f"抽出情報: {result.get('extracted')}")
    
    # テストケース2: 情報が揃っている場合
    print("\n【テストケース2】獣害通報（情報充足）")
    print("-" * 60)
    
    initial_state = {
        "user_message": "イノシシが青梅市勝沼123の畑を荒らしています。今日の朝8時に発見しました。トウモロコシが食べられました。",
        "conversation_history": []
    }
    
    result = workflow.invoke(initial_state)
    print(f"カテゴリ: {result.get('category')}")
    print(f"AI応答: {result.get('ai_response')}")
    print(f"不足スロット: {result.get('missing_slots')}")
    print(f"抽出情報: {result.get('extracted')}")
    print(f"完了: {result.get('is_complete')}")
    if result.get('department'):
        print(f"担当部署: {result['department'].get('dept')}")
    
    # テストケース3: 対話的な情報収集
    print("\n【テストケース3】対話的な情報収集")
    print("-" * 60)
    
    conversation_history = []
    
    # 1ターン目: 初期メッセージ
    initial_state = {
        "user_message": "動物がいます",
        "conversation_history": conversation_history
    }
    result1 = workflow.invoke(initial_state)
    print(f"ターン1 - ユーザー: {initial_state['user_message']}")
    print(f"ターン1 - AI: {result1.get('ai_response')}")
    print(f"ターン1 - 不足: {result1.get('missing_slots')}")
    
    # 2ターン目: 動物種を回答
    conversation_history.append({
        "role": "user",
        "message": initial_state["user_message"]
    })
    conversation_history.append({
        "role": "ai",
        "message": result1.get('ai_response')
    })
    
    initial_state = {
        "user_message": "イノシシです",
        "conversation_history": conversation_history
    }
    result2 = workflow.invoke(initial_state)
    print(f"\nターン2 - ユーザー: {initial_state['user_message']}")
    print(f"ターン2 - AI: {result2.get('ai_response')}")
    print(f"ターン2 - 不足: {result2.get('missing_slots')}")
    print(f"ターン2 - 抽出: {result2.get('extracted')}")
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)


if __name__ == "__main__":
    simulate_conversation()
