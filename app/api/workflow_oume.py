"""
青梅市向けのLangGraphワークフロー
報告内容整理機能を中心とした実装
"""

from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
import logging

from app.api.ai_client import AIClient
from app.api.report_organizer import ReportOrganizer
from app.api.config.oume_city_config import OUME_CITY_CONTACTS

logger = logging.getLogger(__name__)


# ============================================================================
# GraphState定義（青梅市版）
# ============================================================================

class OumeGraphState(TypedDict):
    """
    グラフの状態を保持する型定義（青梅市版）。
    報告内容整理に特化。
    """
    user_message: str  # ユーザーからのメッセージ
    conversation_history: List[Dict[str, Any]]  # 会話履歴
    extracted: Dict[str, Any]  # 抽出された情報
    category: Optional[str]  # 分類されたカテゴリ
    missing_slots: List[str]  # 不足しているスロット
    department: Optional[Dict[str, Any]]  # 担当部署情報
    ai_response: Optional[str]  # AIの応答
    turn_labels: List[Dict[str, Any]]  # ターンごとのラベル
    is_complete: bool  # 情報収集が完了したか


# ============================================================================
# WorkflowManager（青梅市版）
# ============================================================================

class OumeWorkflowManager:
    """
    青梅市向けのLangGraphワークフロー管理クラス。
    報告内容整理機能を中心に実装。
    """
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        self.report_organizer = ReportOrganizer()
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """
        ステートグラフを構築してコンパイルする。
        """
        workflow = StateGraph(OumeGraphState)
        
        # ノードの定義
        workflow.add_node("intake", self._intake_node)
        workflow.add_node("classify", self._classify_node)
        workflow.add_node("extract", self._extract_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("ask_missing", self._ask_missing_node)
        workflow.add_node("finalize", self._finalize_node)
        workflow.add_node("label_turn", self._label_turn_node)
        
        # エッジの定義
        workflow.set_entry_point("intake")
        workflow.add_edge("intake", "classify")
        workflow.add_edge("classify", "extract")
        workflow.add_edge("extract", "validate")
        
        # 条件付きエッジ: 不足スロットがあるかどうか
        workflow.add_conditional_edges(
            "validate",
            self._check_complete,
            {
                "ask": "ask_missing",
                "complete": "finalize"
            }
        )
        
        workflow.add_edge("ask_missing", "label_turn")
        workflow.add_edge("label_turn", END)
        workflow.add_edge("finalize", "label_turn")
        
        return workflow.compile()
    
    # ========================================================================
    # ノード関数
    # ========================================================================
    
    def _intake_node(self, state: OumeGraphState) -> Dict[str, Any]:
        """受付ノード：初期化"""
        try:
            logger.info("  [intake] 受付ノード実行開始")
            user_message = state.get("user_message", "")
            conversation_history = state.get("conversation_history", [])
            logger.info(f"  [intake] user_message: '{user_message[:50]}...' (length={len(user_message)})")
            logger.info(f"  [intake] conversation_history: {len(conversation_history)}件")
            
            result = {
                "user_message": user_message,
                "conversation_history": conversation_history,
                "extracted": state.get("extracted", {}),
                "turn_labels": state.get("turn_labels", [])
            }
            logger.info(f"  [intake] 受付ノード完了")
            return result
        except Exception as e:
            logger.error(f"  [intake] 受付ノードエラー: {type(e).__name__}: {e}", exc_info=True)
            return {}
    
    def _classify_node(self, state: OumeGraphState) -> Dict[str, Any]:
        """分類ノード：カテゴリを判定"""
        try:
            logger.info("  [classify] 分類ノード実行開始")
            user_message = state.get("user_message", "")
            category = state.get("category")
            logger.info(f"  [classify] 入力メッセージ: '{user_message[:50]}...'")
            logger.info(f"  [classify] 既存category: {category}")
            
            # 既に分類されていればそのまま
            if category:
                logger.info(f"  [classify] 既存カテゴリを使用: {category}")
                return {"category": category}
            
            # ReportOrganizerで分類
            category_key = self.report_organizer.classify(user_message)
            logger.info(f"  [classify] 分類完了: {category_key}")
            return {"category": category_key}
        except Exception as e:
            logger.error(f"  [classify] 分類ノードエラー: {type(e).__name__}: {e}", exc_info=True)
            return {"category": "other"}
    
    def _extract_node(self, state: OumeGraphState) -> Dict[str, Any]:
        """抽出ノード：情報を抽出"""
        try:
            logger.info("  [extract] 抽出ノード実行開始")
            user_message = state.get("user_message", "")
            category_key = state.get("category", "other")
            extracted = state.get("extracted", {}).copy()
            logger.info(f"  [extract] 入力メッセージ: '{user_message[:50]}...'")
            logger.info(f"  [extract] category: {category_key}")
            logger.info(f"  [extract] 既存extracted: {extracted}")
            
            # ReportOrganizerで抽出
            extracted = self.report_organizer.extract(user_message, category_key, extracted)
            logger.info(f"  [extract] 抽出完了: {extracted}")
            return {"extracted": extracted}
        except Exception as e:
            logger.error(f"  [extract] 抽出ノードエラー: {type(e).__name__}: {e}", exc_info=True)
            return {"extracted": state.get("extracted", {})}
    
    def _validate_node(self, state: OumeGraphState) -> Dict[str, Any]:
        """検証ノード：不足スロットを算出"""
        try:
            logger.info("  [validate] 検証ノード実行開始")
            category_key = state.get("category", "other")
            extracted = state.get("extracted", {})
            logger.info(f"  [validate] category: {category_key}")
            logger.info(f"  [validate] extracted: {extracted}")
            
            # ReportOrganizerで検証
            missing_slots = self.report_organizer.validate(category_key, extracted)
            is_complete = len(missing_slots) == 0
            
            logger.info(f"  [validate] 検証完了: missing_slots={missing_slots}, is_complete={is_complete}")
            return {
                "missing_slots": missing_slots,
                "is_complete": is_complete
            }
        except Exception as e:
            logger.error(f"  [validate] 検証ノードエラー: {type(e).__name__}: {e}", exc_info=True)
            return {"missing_slots": [], "is_complete": False}
    
    def _ask_missing_node(self, state: OumeGraphState) -> Dict[str, Any]:
        """不足質問ノード：不足スロットを質問"""
        try:
            logger.info("  [ask_missing] 不足質問ノード実行開始")
            missing_slots = state.get("missing_slots", [])
            category_key = state.get("category", "other")
            logger.info(f"  [ask_missing] missing_slots: {missing_slots}")
            
            if not missing_slots:
                logger.info("  [ask_missing] 不足スロットなし")
                return {"ai_response": "ありがとうございます。情報を確認しました。"}
            
            # ReportOrganizerで質問生成
            question = self.report_organizer.ask_missing(missing_slots, category_key)
            logger.info(f"  [ask_missing] 不足質問生成: '{question[:50]}...'")
            return {"ai_response": question}
        except Exception as e:
            logger.error(f"  [ask_missing] 不足質問ノードエラー: {type(e).__name__}: {e}", exc_info=True)
            return {"ai_response": "もう一度お聞かせください。"}
    
    def _finalize_node(self, state: OumeGraphState) -> Dict[str, Any]:
        """確定ノード：情報整理完了"""
        try:
            logger.info("  [finalize] 確定ノード実行開始")
            category_key = state.get("category", "other")
            extracted = state.get("extracted", {})
            logger.info(f"  [finalize] category: {category_key}")
            logger.info(f"  [finalize] extracted: {extracted}")
            
            # ReportOrganizerで最終化
            report_data = self.report_organizer.finalize(category_key, extracted)
            
            # 担当部署を決定（暫定実装）
            dept_resolver = self._resolve_department(category_key)
            
            ai_response = report_data.get("confirmation_message", "情報を確認しました。")
            
            logger.info(f"  [finalize] 確定完了: department={dept_resolver.get('dept', '不明')}")
            return {
                "department": dept_resolver,
                "ai_response": ai_response,
                "is_complete": True,
                "extracted": extracted  # 最終的な抽出情報も含める
            }
        except Exception as e:
            logger.error(f"  [finalize] 確定ノードエラー: {type(e).__name__}: {e}", exc_info=True)
            return {
                "department": {},
                "ai_response": f"申し訳ありません。処理中にエラーが発生しました: {str(e)}",
                "is_complete": True
            }
    
    def _label_turn_node(self, state: OumeGraphState) -> Dict[str, Any]:
        """ラベリングノード：ターンごとのラベルを付与"""
        try:
            logger.info("  [label_turn] ラベリングノード実行開始")
            category = state.get("category", "other")
            extracted = state.get("extracted", {})
            missing_slots = state.get("missing_slots", [])
            is_complete = state.get("is_complete", False)
            turn_labels = state.get("turn_labels", [])
            
            # ターンラベルを生成
            turn_label = {
                "dialog_act": "confirm" if is_complete else "ask_clarify",
                "topic_category": category,
                "slots_filled": list(extracted.keys()),
                "missing_slots": missing_slots,
                "confidence": 0.8 if is_complete else 0.6
            }
            
            turn_labels.append(turn_label)
            logger.info(f"  [label_turn] ラベリング完了: {turn_label}")
            return {"turn_labels": turn_labels}
        except Exception as e:
            logger.error(f"  [label_turn] ラベリングノードエラー: {type(e).__name__}: {e}", exc_info=True)
            return {"turn_labels": state.get("turn_labels", [])}
    
    def _check_complete(self, state: OumeGraphState) -> str:
        """完了チェック：不足スロットがあるかどうか"""
        missing_slots = state.get("missing_slots", [])
        if missing_slots:
            return "ask"
        return "complete"
    
    def _resolve_department(self, category_key: str) -> Dict[str, Any]:
        """担当部署を決定（暫定実装）"""
        # カテゴリからdept_resolverを取得
        from app.api.config.oume_city_config import CATEGORIES
        category = next((c for c in CATEGORIES if c["key"] == category_key), None)
        if category:
            dept_resolver_key = category.get("dept_resolver", "general")
            return OUME_CITY_CONTACTS.get(dept_resolver_key, OUME_CITY_CONTACTS["general"])
        return OUME_CITY_CONTACTS["general"]
    
    # ========================================================================
    # 公開メソッド
    # ========================================================================
    
    def invoke(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        ワークフローを実行する。
        
        Args:
            initial_state: 初期状態
            
        Returns:
            実行後の最終状態
        """
        try:
            user_message = initial_state.get("user_message", "")
            conversation_history = initial_state.get("conversation_history", [])
            logger.info("=" * 60)
            logger.info("Workflow開始（青梅市版）")
            logger.info(f"  user_message: '{user_message[:100]}...' (length={len(user_message)})")
            logger.info(f"  conversation_history: {len(conversation_history)}件")
            
            # 初期状態をOumeGraphStateに合わせる
            graph_state: OumeGraphState = {
                "user_message": user_message,
                "conversation_history": conversation_history,
                "extracted": {},
                "category": None,
                "missing_slots": [],
                "department": None,
                "ai_response": None,
                "turn_labels": [],
                "is_complete": False
            }
            logger.info(f"GraphState初期化完了: keys={list(graph_state.keys())}")
            
            logger.info("LangGraph実行開始...")
            result = self.graph.invoke(graph_state)
            logger.info("LangGraph実行完了")
            
            ai_response = result.get("ai_response")
            category = result.get("category")
            is_complete = result.get("is_complete")
            missing_slots = result.get("missing_slots", [])
            
            logger.info("Workflow完了")
            logger.info(f"  ai_response: '{ai_response[:100] if ai_response else None}...'")
            logger.info(f"  category: {category}")
            logger.info(f"  is_complete: {is_complete}")
            logger.info(f"  missing_slots: {missing_slots}")
            if result.get("department"):
                logger.info(f"  department: {result['department'].get('dept', '不明')}")
            logger.info("=" * 60)
            
            return result
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"Workflow実行エラー: {type(e).__name__}: {e}", exc_info=True)
            logger.error("=" * 60)
            return {
                **initial_state,
                "ai_response": f"申し訳ありません。処理中にエラーが発生しました: {str(e)}",
                "error": str(e)
            }
