# AI Agent 開発講座（LINE 連携編）

このプロジェクトは、**自治体サービスカタログの検索と案内**を主目的とした、AI エージェント対話型 Web アプリケーションです。FastAPI バックエンドと Streamlit フロントエンドで構成されており、住民が自然言語で相談することで、適切な行政サービスを提案します。LINE ログインでユーザーを識別し、会話履歴に基づいた継続的なサポートが可能です。

バックエンドは **LangGraph** を用いたコンポーネントベースのアーキテクチャを採用しており、状況整理、仮説生成、情報検索 (RAG)、応答設計といったプロセスを構造化して実行します。

## 学習内容

- Streamlit を使用した Web フロントエンドの構築
- FastAPI バックエンドとの連携
- LINE ログイン (OAuth2) を利用したユーザー認証
- データベースを用いた会話履歴の保存と取得
- 外部 LLM（Ollama 互換 API または OpenAI API）との連携
- **LangGraph を用いたエージェントワークフローの構築**
- **コンポーネントベースのバックエンド設計**

## プロジェクト構成

```
.
├── app/
│   ├── api/                    # FastAPI バックエンド
│   │   ├── main.py             # API エンドポイント
│   │   ├── workflow.py         # LangGraph ワークフロー定義
│   │   ├── ai_client.py        # LLM への問い合わせロジック
│   │   ├── db.py               # MySQL とのやり取り
│   │   ├── state_manager.py    # 会話状態管理
│   │   └── components/         # エージェントコンポーネント
│   │       ├── situation_analyzer.py   # 状況整理
│   │       ├── hypothesis_generator.py # 仮説生成
│   │       ├── rag_manager.py          # 情報検索 (RAG)
│   │       └── response_planner.py     # 応答設計
│   └── ui/                     # Streamlit フロントエンド
│       ├── ui.py               # チャット画面
│       └── line_login.py       # LINE ログインフロー
├── static/prompts/             # LLM プロンプトテンプレート
├── mysql/
│   ├── my.cnf                  # MySQL 設定
│   └── db/
│       ├── schema.sql          # users テーブル DDL
│       └── user_messages.sql   # user_messages テーブル DDL
├── scripts/                # スクリプト群
│   ├── ops/                # 運用ツール (reset_catalog.sh 等)
│   └── test/
│       ├── manual/         # 手動検証用スクリプト
│       └── system/         # システムテスト実行スクリプト
├── test/                   # (空: scripts/test/system に移動済み)
├── config.py                   # アプリ共通設定
├── requirements.api.txt        # API 用 Python 依存関係
├── requirements.ui.txt         # UI 用 Python 依存関係
├── Dockerfile.api              # API 用 Dockerfile
├── Dockerfile.ui               # UI 用 Dockerfile
├── docker-compose.yaml         # Docker Compose 設定
└── .env.example                # 環境変数サンプル
```

## 主要なコンポーネント

### バックエンドアーキテクチャ (LangGraph)

バックエンドは以下の4つのコンポーネントと、それらを統括するワークフローで構成されています。

1.  **SituationAnalyzer（状況整理）**: ユーザーの発話と会話履歴から、住民プロファイルとサービスニーズを更新します。
2.  **HypothesisGenerator（仮説生成）**: 整理された状況から、必要なサービス候補の仮説を生成します。
3.  **RAGManager（情報検索）**: Qdrant (Vector DB) を使用して、仮説に基づいたサービス情報を検索します。
4.  **ResponsePlanner（応答設計）**: 分析結果と検索結果をもとに、ユーザーへの応答を計画・生成します。

これらは `app/api/workflow.py` で定義されたグラフに従って実行されます。

- **FastAPI バックエンド**: API エンドポイントを提供し、ワークフローを実行
- **Streamlit フロントエンド**: LINE ログインとチャット UI を提供
- **MySQL**: LINE アカウントと紐づくユーザー情報・会話履歴・分析結果、および**サービスカタログ**を保存
- **Qdrant**: サービスカタログのベクトルインデックスを保存し、セマンティック検索を提供
- LLM 連携: OpenAI API または Ollama 互換エンドポイントを利用

## リクエスト処理フロー

ユーザーからのメッセージがどのように処理され、応答が生成されるかの流れは以下の通りです。

1.  **API 受信 (`/api/v1/user-message`)**
    - フロントエンドからユーザー ID とメッセージを受け取ります。
    - メッセージを `user_messages` テーブルに保存します。

2.  **状態のロード**
    - `users` テーブルから、そのユーザーの「住民プロファイル」と「サービスニーズ」の最新状態を読み込みます。
    - 直近の会話履歴を取得します。

3.  **ワークフロー実行 (LangGraph)**
    - `WorkflowManager` が初期化され、以下のグラフを実行します：
        - **Situation Analysis (状況整理)**: ユーザーの最新の発話と履歴から、プロファイルとニーズを更新・洗練させます。
        - **Hypothesis Generation (仮説生成)**: 整理された状況に基づき、「どのような行政サービスが提案できそうか」という仮説を複数生成します。
        - **RAG Retrieval (情報検索 - 条件付き)**: 生成された仮説の中に「詳細情報の検索が必要」と判断されたものがあれば、Qdrant (Vector DB) を検索して裏付けとなるサービス情報を取得します。
        - **Response Planning (応答設計)**: 分析結果、仮説、(あれば) 検索結果を統合し、ユーザーへの最終的な応答メッセージを生成します。

4.  **状態の保存**
    - 更新された「住民プロファイル」と「サービスニーズ」を DB に保存します (次回のターンで使用するため)。
    - 今回の分析結果 (仮説や検索結果など) をログとして保存します。

5.  **応答**
    - 生成された応答メッセージを DB に保存し、API レスポンスとして返却します。

## 実装のポイント

### バックエンド (FastAPI)
- `/api/v1/users`: LINE ログイン後に呼び出し、ユーザー ID を払い出す
- `/api/v1/user-message`: ユーザーのメッセージを受け取り、LangGraph ワークフローを実行して応答を返却
- **`/api/v1/user-message-stream`**: LangGraph の実行状況と応答をリアルタイムでストリーミング配信 (NDJSON)
- `/api/v1/user-messages`: 指定ユーザーの直近メッセージ履歴を取得

### 管理 API (Admin - Port 8087)
- **`/api/v1/service-catalog/import`**: サービスカタログ (JSON) をインポートし、Embedding を生成して DB/Qdrant に保存
- **`/api/v1/service-catalog/reset`**: サービスカタログデータをリセット (DELETE)

### フロントエンド (Streamlit)
- LINE ログインで取得したプロフィールをバックエンドに登録
- チャット UI から API を呼び出し、会話を表示
- **リアルタイム処理状況表示**: ストリーミング API を利用し、AI の思考プロセス（状況整理、仮説生成など）を可視化
- `API_URL` 環境変数で接続先 API を切り替え可能

## セットアップ

### 前提条件

- Docker / Docker Compose が利用可能な環境
- LINE ログインチャネル（チャンネル ID・シークレット）
- **OpenAI API Key** (RAG の Embedding 生成に必須)
- Ollama などの LLM 推論エンドポイント (オプション、推論に OpenAI を使わない場合)

### セットアップ手順

1. **リポジトリのクローン**
    ```bash
    git clone -b streaming-response [https://github.com/dx-junkyard/ai-agent-playground-101.git](https://github.com/dx-junkyard/ai-agent-playground-101.git)
    cd ai-agent-playground-101
    ```

2. **環境変数の設定**
    - `.env.example` を `.env` にコピーし、以下を設定します
        - `OPENAI_API_KEY`: **必須** (Embedding 生成および LLM 推論に使用)
        - `LINE_CHANNEL_ID`, `LINE_CHANNEL_SECRET`, `LINE_REDIRECT_URI`
    - `config.py` の `LLM_MODEL` / `AI_URL` を使用する LLM に合わせて変更します

3. **コンテナの起動**
    ```bash
    docker compose up --build
    ```
    ※ 初回起動時は MySQL と Qdrant の初期化が行われます。

4. **アプリケーションへのアクセス**
    - UI: http://localhost:8080
    - API: http://localhost:8086
    - Admin API: http://localhost:8087
    - MySQL: localhost:3306（ユーザー名 `me`、パスワード `me`）
    - Qdrant: http://localhost:6333

## 使い方

### Web インターフェース

1. ブラウザで http://localhost:8080 にアクセス
2. 表示される LINE ログインリンクから認証
3. チャット欄にメッセージを入力して送信
4. AI からの応答と会話履歴が画面に表示されます

### サービスカタログの管理

#### インポート
RAG 機能を使用するには、事前にサービスカタログデータをインポートする必要があります。
`static/data/service_catalog.json` が用意されていることを確認し、以下のスクリプトを実行してください。

```bash
sh ./scripts/ops/import_catalog.sh
```

#### リセット
カタログデータを全て消去して初期状態に戻す場合に使用します。

```bash
```bash
curl -X DELETE "http://localhost:8087/api/v1/service-catalog/reset"
```
```

### API の直接利用

#### メッセージ送信

```bash
curl http://localhost:8086/api/v1/user-message \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "message": "こんにちは！",
    "user_id": "<LINE ログインで払い出された user_id>"
  }'
```

#### 履歴の取得

```bash
curl 'http://localhost:8086/api/v1/user-messages?user_id=<user_id>&limit=10'
```

## 開発



### テストの実行

#### システムテスト (pytest)
```bash
# 仮想環境の作成と依存関係のインストール
python -m venv venv
source venv/bin/activate
pip install -r requirements.api.txt
pip install pytest

# テストの実行
./scripts/test/system/run_tests.sh
```

#### 手動テスト・検証
`scripts/test/manual/` 配下に検証用スクリプトがあります。
- `api_test.sh`: API エンドポイントの動作確認
- `db_connect.sh`: DB 接続確認
- `ollama_test.sh`: LLM 接続確認
- `test_rag.py`: RAG 検索ロジックの検証

### 運用ツール
`scripts/ops/` 配下に運用スクリプトがあります。
- `reset_catalog.sh`: サービスカタログのリセット
- `import_catalog.sh`: サービスカタログのリセット

### トラブルシューティング

- PR 作成が失敗する場合は `scripts/debug_pr_creation.py` を実行し、Git のリモート設定やトークン設定など、よくある原因をチェックしてください。

### コード修正時のポイント

- コンポーネントのロジックは `app/api/components/` 配下の各ファイルを修正してください。
- ワークフローの定義は `app/api/workflow.py` にあります。
- `app/api/ai_client.py` は LLM との通信を抽象化しています。

## 拡張アイデア

- 複数 LLM の切り替え UI
- 会話履歴の検索／エクスポート
- LINE 上での直接応答

## ライセンス

このプロジェクトは [MIT ライセンス](LICENSE) の下で公開されています。
