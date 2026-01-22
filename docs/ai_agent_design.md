# AIエージェント設計書

## 青梅市向け報告内容整理AIエージェント

**設計者**: MutsuK  
**設計日**: 2026年1月22日  
**対象システム**: LINE通報AI管理システム  
**対象自治体**: 青梅市（PoC）

---

## 1. エージェント概要

### 1.1 目的

LINE通報AI管理システムにおいて、通報内容をAIエージェントが対話形式でヒアリングし、必要な情報を自動的に収集・整理する。特に**獣害通報を中心**に、不足情報を段階的に収集し、構造化されたデータとして出力する。

### 1.2 設計方針

- **対話的ヒアリング**: ユーザーとの対話を通じて情報を段階的に収集
- **拡張可能な設計**: カテゴリやスロット定義を設定ファイル化し、後から追加可能
- **優先順位ベースの質問**: 重要度の高い情報から順に質問
- **エラーハンドリング**: 各処理ステップでエラーが発生しても続行可能

---

## 2. アーキテクチャ

### 2.1 全体構成

```
┌─────────────────────────────────────────────────────────┐
│                    LINE通報受信                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              AIエージェント（LangGraph）                 │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  intake  │→ │ classify │→ │ extract  │            │
│  └──────────┘  └──────────┘  └──────────┘            │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ validate │→ │ask_missing│→ │ finalize │            │
│  └──────────┘  └──────────┘  └──────────┘            │
│                                                          │
│  ┌──────────┐                                          │
│  │label_turn│                                          │
│  └──────────┘                                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              構造化された通報データ                       │
│  - category: カテゴリ                                   │
│  - extracted: 抽出された情報                            │
│  - missing_slots: 不足スロット                          │
│  - department: 担当部署                                 │
└─────────────────────────────────────────────────────────┘
```

### 2.2 コンポーネント構成

```
app/api/
├── config/
│   └── oume_city_config.py      # 設定ファイル（カテゴリ・スロット定義）
├── report_organizer.py          # 報告内容整理機能
│   ├── CategoryManager          # カテゴリ管理
│   ├── SlotManager              # スロット管理
│   ├── QuestionGenerator        # 質問生成
│   └── ReportOrganizer           # 統合クラス
├── workflow_oume.py            # LangGraphワークフロー
│   └── OumeWorkflowManager      # ワークフロー管理
└── main.py                      # APIエンドポイント
```

---

## 3. ワークフロー設計

### 3.1 ノード構成

| ノード | 役割 | 入力 | 出力 |
|--------|------|------|------|
| `intake` | 受付・初期化 | user_message, conversation_history | 初期状態 |
| `classify` | カテゴリ分類 | user_message | category |
| `extract` | 情報抽出 | user_message, category | extracted |
| `validate` | 不足スロット検出 | category, extracted | missing_slots, is_complete |
| `ask_missing` | 質問生成 | missing_slots, category | ai_response |
| `finalize` | 情報整理完了 | category, extracted | ai_response, department |
| `label_turn` | ターンラベリング | 全状態 | turn_labels |

### 3.2 フロー制御

```
intake → classify → extract → validate
                              │
                              ├─ missing_slotsあり → ask_missing → label_turn → END
                              │
                              └─ missing_slotsなし → finalize → label_turn → END
```

### 3.3 状態管理

**GraphState** (TypedDict):
```python
{
    "user_message": str,              # ユーザーメッセージ
    "conversation_history": List[Dict], # 会話履歴
    "extracted": Dict[str, Any],      # 抽出された情報
    "category": Optional[str],         # カテゴリ
    "missing_slots": List[str],       # 不足スロット
    "department": Optional[Dict],     # 担当部署
    "ai_response": Optional[str],      # AI応答
    "turn_labels": List[Dict],        # ターンラベル
    "is_complete": bool               # 完了フラグ
}
```

---

## 4. カテゴリ設計

### 4.1 カテゴリ定義構造

```python
{
    "key": "wildlife_damage",           # カテゴリキー
    "name": "獣害",                      # カテゴリ名
    "description": "野生動物による被害",  # 説明
    "dept_resolver": "wildlife_city",    # 部署解決キー
    "required_slots": [...],             # 必須スロット
    "optional_slots": [...],             # オプションスロット
    "keywords": [...]                    # 分類キーワード
}
```

### 4.2 実装カテゴリ

#### 1. `wildlife_damage` (獣害) - 優先度高
- **必須スロット**: `location`, `time`, `species`, `details`, `damage_type`
- **オプション**: `urgency`, `photo_url`, `witness_info`, `contact_info`
- **キーワード**: イノシシ、サル、カラス、シカ、動物、獣害、野生、害獣

#### 2. `infrastructure_damage` (インフラ損傷)
- **必須スロット**: `location`, `time`, `details`, `damage_type`
- **キーワード**: 道路、橋、施設、破損、損傷、陥没

#### 3. `garbage_issue` (ごみ問題)
- **必須スロット**: `location`, `time`, `details`
- **キーワード**: ごみ、散乱、不法投棄、廃棄物

#### 4. `other` (その他)
- **必須スロット**: `location`, `details`

---

## 5. スロット設計

### 5.1 スロット定義構造

```python
{
    "type": "location",                  # スロットタイプ
    "question": "場所を教えてください...", # 質問文
    "validation": "location_validator",   # 検証関数
    "extraction_keywords": [...],        # 抽出キーワード
    "priority": 1                        # 優先順位
}
```

### 5.2 スロットタイプ

| タイプ | 説明 | 例 |
|--------|------|-----|
| `location` | 場所情報 | 住所、GPS座標 |
| `datetime` | 日時情報 | "今日の朝8時" |
| `enum` | 選択肢 | イノシシ、サル、カラス |
| `text` | 自由文 | 詳細説明 |
| `url` | URL | 写真URL |

### 5.3 優先順位

スロットの質問順序（優先度順）:
1. `location` (場所)
2. `time` (時間)
3. `species` (動物種)
4. `details` (詳細)
5. `damage_type` (被害種別)
6. その他

---

## 6. 情報抽出設計

### 6.1 抽出方法

**現在の実装**: キーワードベースの簡易抽出

```python
def extract_slot_value(slot_key, user_message):
    # キーワードマッチング
    # パターンマッチング
    # 簡易的な構造化
```

**将来の改善**: LLMベースの高度な抽出
- 文脈を考慮した抽出
- 曖昧な表現の解釈
- 会話履歴からの補完

### 6.2 抽出精度向上の方向性

1. **LLM統合**
   - OpenAI APIやOllamaを使用
   - 構造化抽出のプロンプト設計

2. **NER (Named Entity Recognition)**
   - 場所名、日時、動物種の自動抽出

3. **対話履歴の活用**
   - 前のターンで言及された情報を補完

---

## 7. 質問生成設計

### 7.1 質問生成ロジック

```python
def generate_question(missing_slots, category):
    # 1. 優先順位に従ってソート
    sorted_slots = sort_by_priority(missing_slots)
    
    # 2. 最初の不足スロットを選択
    first_missing = sorted_slots[0]
    
    # 3. カテゴリ固有の質問を優先
    if category_specific_question_exists(category, first_missing):
        return get_category_specific_question(category, first_missing)
    
    # 4. デフォルトの質問を返す
    return get_default_question(first_missing)
```

### 7.2 カテゴリ固有の質問

**例: 獣害カテゴリ**
- `location`: "イノシシなどの動物を発見した場所を教えてください（住所またはGPS座標）"
- `species`: "どんな動物でしたか？（イノシシ/サル/カラス/シカ/その他）"
- `damage_type`: "どのような被害がありましたか？（農作物/人身/建物/その他）"

---

## 8. エラーハンドリング設計

### 8.1 エラー処理方針

- **各ノードでエラーが発生しても続行**
- **エラーは警告として記録**
- **ユーザーには分かりやすいエラーメッセージを返す**

### 8.2 エラーケース

| エラーケース | 処理 |
|-------------|------|
| AIClient初期化失敗 | モックを使用して続行 |
| データベース接続失敗 | 警告を出して続行（ワークフローは実行可能） |
| カテゴリ分類失敗 | デフォルトカテゴリ（other）を使用 |
| 情報抽出失敗 | 空の抽出結果で続行 |
| 質問生成失敗 | デフォルト質問を返す |

---

## 9. 拡張性設計

### 9.1 設定ファイルによる拡張

**カテゴリ追加**:
```python
# oume_city_config.py に追加
CATEGORIES.append({
    "key": "new_category",
    "name": "新カテゴリ",
    "required_slots": [...],
    "keywords": [...]
})
```

**スロット追加**:
```python
SLOT_DEFINITIONS["new_slot"] = {
    "type": "text",
    "question": "...",
    "priority": 10
}
```

### 9.2 プラグイン構造

将来的には、カテゴリごとの処理をプラグイン化:
```
app/api/plugins/
├── wildlife_damage_plugin.py
├── infrastructure_damage_plugin.py
└── ...
```

### 9.3 自治体別設定の切り替え

```python
# 設定ファイルの切り替え
from app.api.config import oume_city_config  # 青梅市
from app.api.config import fukuoka_city_config  # 福岡市

config = oume_city_config if city == "oume" else fukuoka_city_config
```

---

## 10. パフォーマンス設計

### 10.1 処理時間

- **カテゴリ分類**: < 10ms（キーワードベース）
- **情報抽出**: < 50ms（キーワードベース）
- **質問生成**: < 10ms
- **全体ワークフロー**: < 100ms（LLM呼び出しなしの場合）

### 10.2 最適化の方向性

1. **キャッシュ**
   - カテゴリ分類結果のキャッシュ
   - スロット定義のメモリキャッシュ

2. **並列処理**
   - 複数スロットの同時抽出

3. **LLM呼び出しの最適化**
   - バッチ処理
   - ストリーミング応答

---

## 11. セキュリティ設計

### 11.1 入力検証

- **メッセージ長制限**: 最大10,000文字
- **JSON検証**: リクエストボディの検証
- **SQLインジェクション対策**: パラメータ化クエリ

### 11.2 データ保護

- **個人情報の取り扱い**: 必要最小限の情報のみ収集
- **ログ出力**: 個人情報を含むログはマスキング

---

## 12. テスト設計

### 12.1 テスト戦略

- **ユニットテスト**: 各コンポーネントの個別テスト
- **統合テスト**: ワークフロー全体のテスト
- **E2Eテスト**: APIエンドポイント経由のテスト

### 12.2 テストケース

1. **情報不足の通報**: 段階的なヒアリング
2. **情報充足の通報**: 即座に完了
3. **対話的な情報収集**: 複数ターン
4. **エラーケース**: 各エラーケースのテスト

---

## 13. ログ設計

### 13.1 ログレベル

- **INFO**: 正常な処理フロー
- **WARNING**: エラーが発生したが続行
- **ERROR**: エラーが発生（スタックトレース付き）

### 13.2 ログ出力内容

- 各ノードの実行開始・完了
- 抽出された情報
- 不足スロット
- エラー詳細

---

## 14. 今後の拡張計画

### 14.1 短期（1-2ヶ月）

1. **抽出精度の向上**
   - LLMを使用した高度な抽出
   - NERの統合

2. **GPS座標の処理**
   - 座標から住所への変換
   - 逆ジオコーディング

### 14.2 中期（3-6ヶ月）

1. **報告先振り分け機能**
   - 国、都道府県、区市町村の階層分け
   - 担当課・担当省庁別の振り分け

2. **多言語対応**
   - 英語、中国語などへの対応

### 14.3 長期（6ヶ月以上）

1. **マルチモーダル対応**
   - 画像からの情報抽出
   - 音声入力対応

2. **学習機能**
   - ユーザーフィードバックからの学習
   - 抽出精度の自動改善

---

## 15. 技術スタック

### 15.1 使用技術

- **言語**: Python 3.9
- **フレームワーク**: LangGraph, FastAPI
- **テスト**: pytest
- **ログ**: Python logging

### 15.2 依存関係

```
langgraph>=0.0.1
langchain-core>=0.1.0
fastapi>=0.100.0
uvicorn>=0.20.0
```

---

## 16. 参考資料

- [LangGraph公式ドキュメント](https://langchain-ai.github.io/langgraph/)
- [LINE通報AI管理システム](https://airs-jet.vercel.app/analysis)
- [イベント検索ページ](https://airs-jet.vercel.app/event)

---

**設計者**: MutsuK  
**最終更新**: 2026年1月22日
