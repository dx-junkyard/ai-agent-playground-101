from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
import logging
import re
from datetime import datetime

from app.api.ai_client import AIClient

logger = logging.getLogger(__name__)


# ============================================================================
# 福岡市の窓口マップ設定
# ============================================================================

# 区役所：道路・街路灯など（地域整備部系）
WARD_CONTACTS_INFRA = {
    "東区": {"dept": "東区役所 地域整備部 維持管理課", "tel": "092-645-1056", "email": "ijikanri.HIWO@city.fukuoka.lg.jp"},
    "博多区": {"dept": "博多区役所 地域整備部 地域整備課", "tel": "092-419-1057", "email": "chiikiseibi.HAWO@city.fukuoka.lg.jp"},
    "中央区": {"dept": "中央区役所 地域整備部 地域整備課", "tel": "092-718-1072", "email": "chiikiseibi.CWO@city.fukuoka.lg.jp"},
    "南区": {"dept": "南区役所 地域整備部 維持管理課", "tel": "092-559-5091", "email": "ijikanri.MWO@city.fukuoka.lg.jp"},
    "城南区": {"dept": "城南区役所 地域整備部 維持管理課", "tel": "092-833-4077", "email": "ijikanri.JWO@city.fukuoka.lg.jp"},
    "早良区": {"dept": "早良区役所 地域整備部 維持管理課", "tel": "092-833-4336", "email": "ijikanri.SWO@city.fukuoka.lg.jp"},
    "西区": {"dept": "西区役所 地域整備部 土木第１課 / 土木第２課", "tel": "092-895-7047(第1) / 092-806-0411(第2)", "email": "doboku1.NWO@city.fukuoka.lg.jp / doboku2.NWO@city.fukuoka.lg.jp"},
}

# 区役所：ごみ散乱・不法投棄（生活環境課）
WARD_CONTACTS_ENV = {
    "東区": {"dept": "東区役所 生活環境課", "tel": "092-645-1061", "email": "seikatsukankyo.HIWO@city.fukuoka.lg.jp"},
    "博多区": {"dept": "博多区役所 生活環境課", "tel": "092-419-1068", "email": "seikatsukankyo.HAWO@city.fukuoka.lg.jp"},
    "中央区": {"dept": "中央区役所 生活環境課", "tel": "092-718-1091", "email": "seikatsukankyo.CWO@city.fukuoka.lg.jp"},
    "南区": {"dept": "南区役所 生活環境課", "tel": "092-559-5374", "email": "seikatsukankyo.MWO@city.fukuoka.lg.jp"},
    "城南区": {"dept": "城南区役所 生活環境課", "tel": "092-833-4086", "email": "seikatsukankyo.JWO@city.fukuoka.lg.jp"},
    "早良区": {"dept": "早良区役所 生活環境課", "tel": "092-833-4340", "email": "seikatsukankyo.SWO@city.fukuoka.lg.jp"},
    "西区": {"dept": "西区役所 生活環境課", "tel": "092-895-7050", "email": "(市ページ参照)"},
}

# 市の窓口（不法投棄の選択肢）
ENV_CITY_CONTACTS = {
    "industrial_waste_guidance": {"dept": "環境局 産業廃棄物指導課", "tel": "092-711-4303"},
}

# 獣害（農林水産局側）
WILDLIFE_CONTACT = {
    "dept": "農林水産局 総務農林部（農業振興・イノシシ等対策）",
    "tel": "092-711-4852",
    "email": "n-shinko-inoshishi.AFFB@city.fukuoka.lg.jp"
}


# ============================================================================
# カテゴリ定義（区が必要かどうかを明示）
# ============================================================================

CATEGORIES = [
    # インフラ（区で分岐）
    {"key": "road_damage", "dept_resolver": "infra_by_ward", "required": ["ward", "location", "details"]},
    {"key": "road_sinkhole", "dept_resolver": "infra_by_ward", "required": ["ward", "location", "details", "hazard_level"]},
    {"key": "streetlight_out", "dept_resolver": "infra_by_ward", "required": ["ward", "location", "details"]},
    {"key": "park_damage", "dept_resolver": "infra_by_ward", "required": ["ward", "location", "details"]},
    {"key": "river_drain_issue", "dept_resolver": "infra_by_ward", "required": ["ward", "location", "details"]},
    
    # ごみ・不法投棄（区で分岐）
    {"key": "garbage_scatter", "dept_resolver": "env_by_ward", "required": ["ward", "location", "details", "time"]},
    {"key": "illegal_dumping", "dept_resolver": "env_by_ward_or_city", "required": ["ward", "location", "details", "time", "evidence"]},
    
    # 獣害（市の窓口で一本化）
    {"key": "wildlife_damage", "dept_resolver": "wildlife_city", "required": ["location", "details", "time", "species"]},
    
    # その他
    {"key": "other", "dept_resolver": "general", "required": ["details"]},
]


# ============================================================================
# 不足質問テンプレート
# ============================================================================

SLOT_QUESTIONS = {
    "ward": "福岡市のどの区の内容ですか？（東区／博多区／中央区／南区／城南区／早良区／西区）",
    "location": "場所はどこですか？（住所／近くの施設名／交差点名／地図リンクなど）",
    "time": "いつ頃（いつから）気づきましたか？（例：今日の朝／昨日から など）",
    "details": "状況をもう少し詳しく教えてください。（何が、どのくらい、どんな状態か）",
    "hazard_level": "危険度はどの程度ですか？（通行に支障あり／転倒しそう／危険は小さい、など）",
    "evidence": "写真や動画はありますか？（あれば添付またはURL共有できます）",
    "species": "どんな動物ですか？分かる範囲で教えてください。（例：イノシシ／カラス／サル など）",
}


# ============================================================================
# 不足質問の優先順位
# ============================================================================

SLOT_PRIORITY = ["ward", "location", "time", "details", "hazard_level", "evidence", "species"]


# ============================================================================
# GraphState定義
# ============================================================================

class GraphState(TypedDict):
    """
    グラフの状態を保持する型定義（福岡市版）。
    """
    user_message: str  # ユーザーからのメッセージ
    conversation_history: List[Dict[str, Any]]  # 会話履歴
    extracted: Dict[str, Any]  # 抽出された情報（ward, location, time, details等）
    category: Optional[str]  # 分類されたカテゴリ
    missing_slots: List[str]  # 不足しているスロット
    department: Optional[Dict[str, Any]]  # 担当課情報
    ai_response: Optional[str]  # AIの応答
    turn_labels: List[Dict[str, Any]]  # 会話ラベル
    is_complete: bool  # 情報収集が完了したか


# ============================================================================
# 窓口Resolver
# ============================================================================

def resolve_department(category_key: str, extracted: dict) -> dict:
    """
    カテゴリと抽出情報から担当課を決定する。
    
    Args:
        category_key: カテゴリキー
        extracted: 抽出された情報（ward等を含む）
        
    Returns:
        担当課情報（dept, tel, email, alt等）
    """
    ward = extracted.get("ward")
    
    if category_key in ["road_damage", "road_sinkhole", "streetlight_out", "park_damage", "river_drain_issue"]:
        return WARD_CONTACTS_INFRA.get(ward, {"dept": "区役所（地域整備部）", "tel": None})
    
    if category_key == "garbage_scatter":
        return WARD_CONTACTS_ENV.get(ward, {"dept": "区役所 生活環境課", "tel": None})
    
    if category_key == "illegal_dumping":
        # 原則：区役所生活環境課。状況により産廃指導課も提示可能
        base = WARD_CONTACTS_ENV.get(ward, {"dept": "区役所 生活環境課", "tel": None})
        return {
            "dept": base["dept"],
            "tel": base.get("tel"),
            "email": base.get("email"),
            "alt": ENV_CITY_CONTACTS["industrial_waste_guidance"]
        }
    
    if category_key == "wildlife_damage":
        return WILDLIFE_CONTACT
    
    return {"dept": "福岡市 市民相談（総合案内）", "tel": "092-711-4111"}


# ============================================================================
# WorkflowManager
# ============================================================================

class WorkflowManager:
    """
    LangGraphを使用した対話フローの管理クラス（福岡市版）。
    区の確定を最優先にし、担当課への振り分けと会話ラベリングを行う。
    """
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        self.graph = self._build_graph()

    def _build_graph(self):
        """
        ステートグラフを構築してコンパイルする。
        """
        workflow = StateGraph(GraphState)

        # ノードの定義
        workflow.add_node("intake", self._intake_node)
        workflow.add_node("extract", self._extract_node)
        workflow.add_node("classify", self._classify_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("ask_missing", self._ask_missing_node)
        workflow.add_node("finalize", self._finalize_node)
        workflow.add_node("label_turn", self._label_turn_node)

        # エッジの定義
        workflow.set_entry_point("intake")
        workflow.add_edge("intake", "extract")
        workflow.add_edge("extract", "classify")
        workflow.add_edge("classify", "validate")
        
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
        workflow.add_edge("finalize", "label_turn")
        workflow.add_edge("label_turn", END)

        compiled_graph = workflow.compile()
        logger.info("LangGraph構築完了: 7ノード（福岡市版）")
        return compiled_graph

    # 条件付きエッジ関数
    def _check_complete(self, state: GraphState) -> str:
        """情報収集が完了したかどうかを判定"""
        missing_slots = state.get("missing_slots", [])
        if missing_slots:
            return "ask"
        return "complete"

    # ノード関数
    def _intake_node(self, state: GraphState) -> Dict[str, Any]:
        """受付ノード：初期化"""
        try:
            logger.debug("受付ノード実行中...")
            user_message = state.get("user_message", "")
            conversation_history = state.get("conversation_history", [])
            
            # 会話履歴に現在のメッセージを追加（ここではまだ追加しない）
            return {
                "user_message": user_message,
                "conversation_history": conversation_history,
                "extracted": state.get("extracted", {}),
                "turn_labels": state.get("turn_labels", [])
            }
        except Exception as e:
            logger.error(f"受付ノードエラー: {e}", exc_info=True)
            return {}

    def _extract_node(self, state: GraphState) -> Dict[str, Any]:
        """抽出ノード：ward/location/time/details等を抽出"""
        try:
            logger.debug("抽出ノード実行中...")
            user_message = state.get("user_message", "")
            extracted = state.get("extracted", {}).copy()
            
            # 区の抽出
            wards = ["東区", "博多区", "中央区", "南区", "城南区", "早良区", "西区"]
            for ward in wards:
                if ward in user_message:
                    extracted["ward"] = ward
                    break
            
            # 場所の抽出（簡易版：住所パターンや施設名を検出）
            # ここではLLMを使わず、キーワードベースで抽出
            location_keywords = ["駅", "通り", "丁目", "番地", "交差点", "公園", "川"]
            if any(kw in user_message for kw in location_keywords):
                # 簡易抽出（実際はLLMでより詳細に抽出する）
                if "location" not in extracted:
                    extracted["location"] = user_message
            
            # 時間の抽出
            time_keywords = ["今日", "昨日", "先週", "朝", "昼", "夜", "最近"]
            if any(kw in user_message for kw in time_keywords):
                if "time" not in extracted:
                    extracted["time"] = user_message
            
            # details（簡易版：ユーザーメッセージ全体をdetailsとして保持）
            if "details" not in extracted:
                extracted["details"] = user_message
            
            logger.debug(f"抽出完了: {extracted}")
            return {"extracted": extracted}
        except Exception as e:
            logger.error(f"抽出ノードエラー: {e}", exc_info=True)
            return {"extracted": state.get("extracted", {})}

    def _classify_node(self, state: GraphState) -> Dict[str, Any]:
        """分類ノード：カテゴリを判定"""
        try:
            logger.debug("分類ノード実行中...")
            user_message = state.get("user_message", "").lower()
            category = state.get("category")
            
            # 既に分類されていればそのまま
            if category:
                return {"category": category}
            
            # キーワードベースで分類（実際はLLMで分類する）
            if any(kw in user_message for kw in ["道路", "傷み", "破損", "穴"]):
                category = "road_damage"
            elif any(kw in user_message for kw in ["陥没", "沈下"]):
                category = "road_sinkhole"
            elif any(kw in user_message for kw in ["街灯", "街路灯", "照明"]):
                category = "streetlight_out"
            elif any(kw in user_message for kw in ["公園", "遊具"]):
                category = "park_damage"
            elif any(kw in user_message for kw in ["河川", "排水", "側溝"]):
                category = "river_drain_issue"
            elif any(kw in user_message for kw in ["ごみ", "散乱", "落ちてる"]):
                category = "garbage_scatter"
            elif any(kw in user_message for kw in ["不法投棄", "捨ててる"]):
                category = "illegal_dumping"
            elif any(kw in user_message for kw in ["イノシシ", "野生", "動物", "害獣"]):
                category = "wildlife_damage"
            else:
                category = "other"
            
            logger.debug(f"分類完了: {category}")
            return {"category": category}
        except Exception as e:
            logger.error(f"分類ノードエラー: {e}", exc_info=True)
            return {"category": "other"}

    def _validate_node(self, state: GraphState) -> Dict[str, Any]:
        """検証ノード：required不足を算出"""
        try:
            logger.debug("検証ノード実行中...")
            category_key = state.get("category", "other")
            extracted = state.get("extracted", {})
            
            # カテゴリに対応するrequiredを取得
            category_info = next((c for c in CATEGORIES if c["key"] == category_key), None)
            if not category_info:
                category_info = next((c for c in CATEGORIES if c["key"] == "other"), None)
            
            required = category_info.get("required", ["details"])
            missing_slots = []
            
            # 不足スロットをチェック（優先順位順）
            for slot in SLOT_PRIORITY:
                if slot in required and not extracted.get(slot):
                    missing_slots.append(slot)
            
            logger.debug(f"検証完了: missing_slots={missing_slots}")
            return {
                "missing_slots": missing_slots,
                "is_complete": len(missing_slots) == 0
            }
        except Exception as e:
            logger.error(f"検証ノードエラー: {e}", exc_info=True)
            return {"missing_slots": [], "is_complete": False}

    def _ask_missing_node(self, state: GraphState) -> Dict[str, Any]:
        """不足質問ノード：不足スロットを質問（wardを最優先）"""
        try:
            logger.debug("不足質問ノード実行中...")
            missing_slots = state.get("missing_slots", [])
            
            if not missing_slots:
                return {"ai_response": "ありがとうございます。情報を確認しました。"}
            
            # 優先順位に従って最初の不足スロットを質問
            first_missing = missing_slots[0]
            question = SLOT_QUESTIONS.get(first_missing, f"{first_missing}について教えてください。")
            
            logger.debug(f"不足質問: {first_missing}")
            return {"ai_response": question}
        except Exception as e:
            logger.error(f"不足質問ノードエラー: {e}", exc_info=True)
            return {"ai_response": "もう一度お聞かせください。"}

    def _finalize_node(self, state: GraphState) -> Dict[str, Any]:
        """確定ノード：窓口確定・payload作成"""
        try:
            logger.debug("確定ノード実行中...")
            category = state.get("category", "other")
            extracted = state.get("extracted", {})
            
            # 担当課を決定
            department = resolve_department(category, extracted)
            
            # 応答メッセージを作成
            dept_info = department.get("dept", "担当課")
            tel_info = department.get("tel", "")
            
            response_parts = [
                f"お問い合わせ内容を確認しました。",
                f"担当は「{dept_info}」です。"
            ]
            
            if tel_info:
                response_parts.append(f"お電話でのお問い合わせは {tel_info} までお願いいたします。")
            
            if department.get("alt"):
                alt_dept = department["alt"].get("dept", "")
                alt_tel = department["alt"].get("tel", "")
                response_parts.append(f"または「{alt_dept}」（{alt_tel}）にもご相談いただけます。")
            
            response_parts.append("\nご不明な点がございましたら、お気軽にお問い合わせください。")
            
            ai_response = "\n".join(response_parts)
            
            logger.debug(f"確定完了: department={dept_info}")
            return {
                "department": department,
                "ai_response": ai_response,
                "is_complete": True
            }
        except Exception as e:
            logger.error(f"確定ノードエラー: {e}", exc_info=True)
            return {
                "department": {},
                "ai_response": "申し訳ありません。処理中にエラーが発生しました。",
                "is_complete": True
            }

    def _label_turn_node(self, state: GraphState) -> Dict[str, Any]:
        """ラベル付けノード：会話をターンごとにラベリング"""
        try:
            logger.debug("ラベル付けノード実行中...")
            turn_labels = state.get("turn_labels", []).copy()
            
            # ターンラベルを作成
            dialog_act = "route_result" if state.get("is_complete") else "ask_clarify"
            category = state.get("category", "other")
            missing_slots = state.get("missing_slots", [])
            extracted = state.get("extracted", {})
            
            # 埋まったスロットを計算
            category_info = next((c for c in CATEGORIES if c["key"] == category), None)
            required = category_info.get("required", ["details"]) if category_info else ["details"]
            slots_filled = [slot for slot in required if extracted.get(slot)]
            
            turn_label = {
                "dialog_act": dialog_act,
                "topic_category": category,
                "slots_filled": slots_filled,
                "missing_slots": missing_slots,
                "confidence": 0.8,  # 簡易版では固定値（実際はLLMで算出）
                "timestamp": datetime.now().isoformat()
            }
            
            turn_labels.append(turn_label)
            
            logger.debug(f"ラベル付け完了: {len(turn_labels)}件")
            return {"turn_labels": turn_labels}
        except Exception as e:
            logger.error(f"ラベル付けノードエラー: {e}", exc_info=True)
            return {"turn_labels": state.get("turn_labels", [])}

    def invoke(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        ワークフローを実行する。
        
        Args:
            initial_state (Dict[str, Any]): 初期状態
            
        Returns:
            Dict[str, Any]: 実行後の最終状態
        """
        try:
            logger.info("Workflow開始: user_message='%s'", initial_state.get("user_message", "")[:50])
            
            # 初期状態をGraphStateに合わせる
            graph_state: GraphState = {
                "user_message": initial_state.get("user_message", ""),
                "conversation_history": initial_state.get("conversation_history", []),
                "extracted": {},
                "category": None,
                "missing_slots": [],
                "department": None,
                "ai_response": None,
                "turn_labels": [],
                "is_complete": False
            }
            
            result = self.graph.invoke(graph_state)
            logger.info("Workflow完了: ai_response生成済み")
            return result
        except Exception as e:
            logger.error(f"Workflow実行エラー: {e}", exc_info=True)
            return {
                **initial_state,
                "ai_response": "申し訳ありません。処理中にエラーが発生しました。もう一度お試しください。",
                "error": str(e)
            }

    def stream(self, initial_state: Dict[str, Any]):
        """
        ワークフローをストリーミング実行する（実行中の状態を逐次取得）。
        
        Args:
            initial_state (Dict[str, Any]): 初期状態
            
        Yields:
            Dict[str, Any]: 各ステップの実行結果
        """
        try:
            logger.info("Workflowストリーミング開始: user_message='%s'", initial_state.get("user_message", "")[:50])
            
            graph_state: GraphState = {
                "user_message": initial_state.get("user_message", ""),
                "conversation_history": initial_state.get("conversation_history", []),
                "extracted": {},
                "category": None,
                "missing_slots": [],
                "department": None,
                "ai_response": None,
                "turn_labels": [],
                "is_complete": False
            }
            
            for event in self.graph.stream(graph_state):
                logger.debug("Workflowイベント: %s", list(event.keys()))
                yield event
            logger.info("Workflowストリーミング完了")
        except Exception as e:
            logger.error(f"Workflowストリーミングエラー: {e}", exc_info=True)
            yield {
                "__error__": {
                    "message": str(e),
                    "state": initial_state
                }
            }

    def get_graph_visualization(self) -> str:
        """
        グラフ構造を可視化するためのMermaid形式の文字列を返す。
        
        Returns:
            str: Mermaid形式のグラフ定義
        """
        return """
        graph TD
            START[開始] --> intake[受付]
            intake --> extract[抽出]
            extract --> classify[分類]
            classify --> validate[検証]
            validate --> |不足あり| ask_missing[不足質問]
            validate --> |完了| finalize[確定]
            ask_missing --> label_turn[ラベル付け]
            finalize --> label_turn
            label_turn --> END[終了]
        """
    
    def print_graph_structure(self):
        """
        グラフ構造をコンソールに出力する（デバッグ用）。
        """
        print("\n=== LangGraph 構造（福岡市版） ===")
        print(self.get_graph_visualization())
        print("\nノード一覧:")
        print("  1. intake - 受付")
        print("  2. extract - 抽出（ward/location/time/details等）")
        print("  3. classify - 分類")
        print("  4. validate - 検証（required不足を算出）")
        print("  5. ask_missing - 不足質問（wardを最優先）")
        print("  6. finalize - 確定（窓口確定・payload作成）")
        print("  7. label_turn - ラベル付け（会話ラベリング）")
        print("\n条件付きエッジ:")
        print("  validate -> check_complete -> (ask: ask_missing | complete: finalize)")
        print("=" * 40 + "\n")
