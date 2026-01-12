#!/usr/bin/env python3
"""
福岡市版LangGraphワークフローのシミュレーター
対話的にワークフローを実行して動作を確認する
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import logging
from unittest.mock import MagicMock
from app.api.workflow import WorkflowManager

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class WorkflowSimulator:
    """ワークフローシミュレーター"""
    
    def __init__(self):
        """初期化"""
        try:
            # AIClientをモック化（workflow.pyでは実際には使用していないため）
            mock_ai_client = MagicMock()
            mock_ai_client.create_response = MagicMock(return_value="モック応答")
            self.ai_client = mock_ai_client
            self.workflow_manager = WorkflowManager(mock_ai_client)
            logger.info("ワークフローシミュレーター初期化完了（モックモード）")
        except Exception as e:
            logger.error(f"初期化エラー: {e}", exc_info=True)
            print(f"⚠️  初期化エラー: {e}")
            self.ai_client = None
            self.workflow_manager = None
    
    def print_graph_structure(self):
        """グラフ構造を表示"""
        if self.workflow_manager:
            self.workflow_manager.print_graph_structure()
    
    def simulate_single_turn(self, user_message: str, conversation_history: list = None) -> dict:
        """
        単一ターンのシミュレーション
        
        Args:
            user_message: ユーザーのメッセージ
            conversation_history: 会話履歴（オプション）
            
        Returns:
            ワークフローの実行結果
        """
        if not self.workflow_manager:
            return {
                "error": "ワークフローマネージャーが初期化されていません",
                "ai_response": "申し訳ありません。システムエラーが発生しました。"
            }
        
        try:
            initial_state = {
                "user_message": user_message,
                "conversation_history": conversation_history or []
            }
            
            result = self.workflow_manager.invoke(initial_state)
            return result
        except Exception as e:
            logger.error(f"シミュレーションエラー: {e}", exc_info=True)
            return {
                "error": str(e),
                "ai_response": "申し訳ありません。処理中にエラーが発生しました。"
            }
    
    def simulate_conversation(self):
        """対話型シミュレーション"""
        print("\n" + "=" * 60)
        print("福岡市版LangGraphワークフロー シミュレーター")
        print("=" * 60)
        print("\n使用方法:")
        print("  - メッセージを入力してEnterを押すと、ワークフローが実行されます")
        print("  - 'quit' または 'exit' で終了")
        print("  - 'graph' でグラフ構造を表示")
        print("  - 'history' で会話履歴を表示")
        print("  - 'clear' で会話履歴をクリア")
        print("-" * 60)
        
        conversation_history = []
        turn_count = 0
        
        while True:
            try:
                print("\n" + "-" * 60)
                user_input = input("ユーザー: ").strip()
                
                if not user_input:
                    continue
                
                # コマンド処理
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 シミュレーターを終了します。")
                    break
                
                if user_input.lower() == 'graph':
                    self.print_graph_structure()
                    continue
                
                if user_input.lower() == 'history':
                    print(f"\n📝 会話履歴 ({len(conversation_history)}件):")
                    for i, msg in enumerate(conversation_history, 1):
                        role = msg.get("role", "unknown")
                        message = msg.get("message", "")
                        print(f"  {i}. [{role}]: {message[:50]}...")
                    continue
                
                if user_input.lower() == 'clear':
                    conversation_history = []
                    turn_count = 0
                    print("\n✅ 会話履歴をクリアしました。")
                    continue
                
                # ワークフロー実行
                turn_count += 1
                print(f"\n🔄 ターン {turn_count}: ワークフロー実行中...")
                
                result = self.simulate_single_turn(user_input, conversation_history)
                
                # 結果表示
                ai_response = result.get("ai_response", "応答が生成されませんでした。")
                print(f"\n🤖 AI: {ai_response}")
                
                # 詳細情報の表示
                category = result.get("category")
                extracted = result.get("extracted", {})
                missing_slots = result.get("missing_slots", [])
                department = result.get("department")
                is_complete = result.get("is_complete", False)
                
                print(f"\n📊 詳細情報:")
                if category:
                    print(f"  カテゴリ: {category}")
                if extracted:
                    print(f"  抽出情報: {extracted}")
                if missing_slots:
                    print(f"  不足スロット: {missing_slots}")
                if department:
                    dept_info = department.get("dept", "不明")
                    print(f"  担当課: {dept_info}")
                print(f"  完了状態: {'✅ 完了' if is_complete else '❌ 未完了'}")
                
                # 会話履歴に追加
                conversation_history.append({
                    "role": "user",
                    "message": user_input
                })
                conversation_history.append({
                    "role": "ai",
                    "message": ai_response
                })
                
                # 最後の20件のみ保持
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]
                
            except KeyboardInterrupt:
                print("\n\n👋 シミュレーターを終了します。")
                break
            except Exception as e:
                logger.error(f"エラー: {e}", exc_info=True)
                print(f"\n❌ エラーが発生しました: {e}")


def run_test_cases():
    """テストケースを実行"""
    print("\n" + "=" * 60)
    print("テストケース実行")
    print("=" * 60)
    
    simulator = WorkflowSimulator()
    
    test_cases = [
        {
            "name": "テスト1: 道路損傷（区指定あり）",
            "message": "博多区の道路が破損しています。天神駅前です。"
        },
        {
            "name": "テスト2: 街路灯（区指定なし）",
            "message": "街路灯が故障しています。"
        },
        {
            "name": "テスト3: ごみ散乱",
            "message": "南区でごみが散乱しています。今日気づきました。"
        },
        {
            "name": "テスト4: 獣害",
            "message": "イノシシが出現しました。早良区です。"
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"テストケース {i}: {test_case['name']}")
        print(f"{'=' * 60}")
        print(f"入力: {test_case['message']}")
        
        result = simulator.simulate_single_turn(test_case['message'])
        
        print(f"\n結果:")
        print(f"  AI応答: {result.get('ai_response', 'N/A')[:100]}...")
        print(f"  カテゴリ: {result.get('category', 'N/A')}")
        print(f"  抽出情報: {result.get('extracted', {})}")
        print(f"  不足スロット: {result.get('missing_slots', [])}")
        print(f"  完了: {result.get('is_complete', False)}")
        
        if result.get('department'):
            print(f"  担当課: {result['department'].get('dept', 'N/A')}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="福岡市版LangGraphワークフローシミュレーター")
    parser.add_argument(
        "--test",
        action="store_true",
        help="テストケースを実行する（対話モードは実行しない）"
    )
    parser.add_argument(
        "--graph",
        action="store_true",
        help="グラフ構造のみを表示"
    )
    
    args = parser.parse_args()
    
    simulator = WorkflowSimulator()
    
    if args.graph:
        simulator.print_graph_structure()
    elif args.test:
        run_test_cases()
    else:
        simulator.simulate_conversation()

