# 報告内容整理機能 実装サマリー

## 実装完了日
2026年1月22日

## 実装内容

### 1. 青梅市向け設定ファイル
**ファイル**: `app/api/config/oume_city_config.py`

- カテゴリ定義（獣害中心）
  - `wildlife_damage`: 獣害
  - `infrastructure_damage`: インフラ損傷
  - `garbage_issue`: ごみ問題
  - `other`: その他

- スロット定義
  - 必須スロット: `location`, `time`, `species`, `details`, `damage_type`
  - オプションスロット: `urgency`, `photo_url`, `witness_info`, `contact_info`
  - 各スロットに質問文、検証ルール、抽出キーワードを定義

### 2. 報告内容整理機能
**ファイル**: `app/api/report_organizer.py`

- `CategoryManager`: カテゴリの分類と管理
- `SlotManager`: スロットの抽出、検証、質問生成
- `QuestionGenerator`: 対話的な質問生成
- `ReportOrganizer`: メインクラス（統合機能）

### 3. 青梅市向けワークフロー
**ファイル**: `app/api/workflow_oume.py`

- `OumeWorkflowManager`: LangGraphを使用したワークフロー管理
- ノード構成:
  - `intake`: 受付
  - `classify`: カテゴリ分類
  - `extract`: 情報抽出
  - `validate`: 不足スロット検出
  - `ask_missing`: 質問生成
  - `finalize`: 情報整理完了
  - `label_turn`: ターンラベリング

### 4. テスト
**ファイル**: 
- `tests/test_report_organizer.py`: ユニットテスト
- `scripts/test_oume_workflow.py`: 統合テストスクリプト

## 動作確認

### テストケース1: 情報不足の通報
**入力**: "イノシシが畑を荒らしています"

**結果**:
- カテゴリ: `wildlife_damage`
- 不足スロット: `location`, `time`, `species`, `damage_type`
- AI応答: "イノシシなどの動物を発見した場所を教えてください（住所またはGPS座標）"

### テストケース2: 情報充足の通報
**入力**: "イノシシが青梅市勝沼123の畑を荒らしています。今日の朝8時に発見しました。トウモロコシが食べられました。"

**結果**:
- カテゴリ: `wildlife_damage`
- 抽出情報: `details`が抽出される
- 不足スロット: 検出される（抽出精度は改善の余地あり）

## 拡張性

### 設定ファイルによる拡張
- カテゴリ定義を追加可能
- スロット定義を追加可能
- 自治体別の設定ファイルを切り替え可能

### プラグイン構造
- カテゴリごとの処理を分離
- 新しいカテゴリを追加しやすい構造

## 今後の改善点

1. **抽出精度の向上**
   - 現在はキーワードベースの簡易抽出
   - LLMを使用した高度な抽出への移行を検討

2. **GPS座標の処理**
   - FooQooさん側でGPS座標を取得する想定
   - 座標から住所への変換機能の追加

3. **対話履歴の活用**
   - 複数ターンにわたる対話の文脈を考慮
   - 会話履歴から情報を補完

4. **報告先振り分け機能**
   - 国、都道府県、区市町村の階層分け
   - 担当課・担当省庁別の振り分け

## 使用方法

### 基本的な使用例

```python
from app.api.workflow_oume import OumeWorkflowManager
from app.api.ai_client import AIClient

# ワークフローの初期化
ai_client = AIClient()
workflow = OumeWorkflowManager(ai_client)

# ワークフローの実行
initial_state = {
    "user_message": "イノシシが畑を荒らしています",
    "conversation_history": []
}

result = workflow.invoke(initial_state)
print(result["ai_response"])  # AIの応答
print(result["category"])     # カテゴリ
print(result["missing_slots"]) # 不足スロット
```

### APIエンドポイントへの統合

`app/api/main.py`に以下のエンドポイントを追加することを推奨:

```python
@app.post("/api/v1/oume/report")
async def post_oume_report(request: Request):
    # 青梅市向けの報告内容整理エンドポイント
    from app.api.workflow_oume import OumeWorkflowManager
    # ... 実装
```

## ファイル構成

```
app/api/
├── config/
│   └── oume_city_config.py      # 青梅市向け設定
├── report_organizer.py          # 報告内容整理機能
├── workflow_oume.py             # 青梅市向けワークフロー
└── main.py                      # APIエンドポイント（統合予定）

tests/
└── test_report_organizer.py     # ユニットテスト

scripts/
└── test_oume_workflow.py        # 統合テストスクリプト

docs/
├── issue_report_content_organization.md  # Issueドキュメント
└── implementation_summary.md             # 実装サマリー（本ファイル）
```

## 参考資料

- [LINE通報AI管理システム](https://airs-jet.vercel.app/analysis)
- [イベント検索ページ](https://airs-jet.vercel.app/event)
- LangGraph公式ドキュメント
