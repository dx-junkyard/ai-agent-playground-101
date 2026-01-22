# 報告内容整理機能の実装（青梅市向けPoC）

## 概要

LINE通報AI管理システムにおいて、通報内容をAIが効率的に整理・ヒアリングする機能を実装しました。
本PRは青梅市のデータセットを使用したPoC（Proof of Concept）として、特に**獣害通報を中心**に実装しています。

## 実装内容

### 新規ファイル

- `app/api/config/oume_city_config.py` - 青梅市向け設定ファイル（カテゴリ、スロット定義）
- `app/api/report_organizer.py` - 報告内容整理機能のコア実装
  - `CategoryManager`: カテゴリ分類
  - `SlotManager`: スロット抽出・検証
  - `QuestionGenerator`: 質問生成
  - `ReportOrganizer`: 統合オーケストレーター
- `app/api/workflow_oume.py` - 青梅市向けLangGraphワークフロー
- `tests/test_report_organizer.py` - 単体テスト
- `scripts/test_oume_workflow.py` - ワークフローテストスクリプト

### 修正ファイル

- `app/api/main.py` - 青梅市向けAPIエンドポイント追加 (`/api/v1/oume/report`)
- `scripts/ui_emulator.html` - 青梅市向けUIエミュレーター

### ドキュメント

- `docs/ai_agent_design.md` - AIエージェント設計書（詳細）
- `docs/issue_report_content_organization.md` - Issueドキュメント
- `docs/implementation_summary.md` - 実装サマリー
- `docs/implementation_report.md` - 実装レポート

## 機能

### 1. カテゴリ分類

ユーザーのメッセージから通報カテゴリを自動分類します。
- `wildlife_damage`: 獣害（イノシシ、サル、カラス等）
- `infrastructure_damage`: インフラ損傷
- `garbage_issue`: ごみ問題
- `other`: その他

### 2. 情報抽出

メッセージから必要な情報を抽出します。
- `location`: 場所（住所またはGPS座標）
- `time`: 発見日時
- `species`: 動物種
- `details`: 詳細状況
- `damage_type`: 被害種別
- その他

### 3. 不足情報の検出と質問生成

必須スロットが不足している場合、優先順位に従って質問を生成します。
優先順位: `location` → `time` → `species` → `damage_type` → `details` → ...

### 4. 対話的ヒアリング

LangGraphを使用したマルチターン対話により、必要な情報を段階的に収集します。

## 技術スタック

- **LangGraph**: ワークフロー管理
- **FastAPI**: APIエンドポイント
- **Python 3.11+**: 実装言語

## テスト

### 単体テスト

```bash
python -m pytest tests/test_report_organizer.py -v
```

### ワークフローテスト

```bash
python scripts/test_oume_workflow.py
```

### APIテスト

```bash
curl -X POST http://localhost:8080/api/v1/oume/report \
  -H "Content-Type: application/json" \
  -d '{"message": "イノシシが畑を荒らしています", "user_id": "test_user"}'
```

## 使用例

### ケース1: 基本通報

**入力**: "イノシシが畑を荒らしています"

**対話フロー**:
1. AI: "場所を教えてください（住所またはGPS座標）"
2. ユーザー: "青梅市勝沼123"
3. AI: "いつ頃（いつから）被害に気づきましたか？"
4. ユーザー: "今日の朝"
5. AI: "どのような被害ですか？（例：農作物が荒らされた、ゴミが散乱した、人への威嚇 など）"
6. ユーザー: "トウモロコシが食べられました"
7. AI: "情報を確認しました。担当部署に連絡します。"

**出力**:
```json
{
  "category": "wildlife_damage",
  "extracted": {
    "location": "青梅市勝沼123",
    "time": "今日の朝",
    "species": "イノシシ",
    "details": "トウモロコシが食べられた",
    "damage_type": "農作物が荒らされた"
  },
  "is_complete": true,
  "ai_response": "情報を確認しました。担当部署に連絡します。"
}
```

## 拡張性

- カテゴリ定義とスロット定義を設定ファイル化
- 自治体別の設定を切り替え可能
- 報告先振り分け機能は後から追加可能な設計

## 今後の拡張計画

- [ ] 報告先振り分け機能（国、都道府県、区市町村別）
- [ ] GPS座標の自動取得
- [ ] 写真・動画のアップロード対応
- [ ] 他の自治体への展開

## 参考資料

- [LINE通報AI管理システム](https://airs-jet.vercel.app/analysis)
- [AIエージェント設計書](docs/ai_agent_design.md)
- [実装サマリー](docs/implementation_summary.md)

## 確認事項

- [ ] コードレビューをお願いします
- [ ] テストの追加が必要な場合はご指摘ください
- [ ] ドキュメントの追加・修正が必要な場合はご指摘ください
