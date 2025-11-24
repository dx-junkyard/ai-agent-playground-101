# AI Agent 開発講座（LINE 連携編）

このプロジェクトは、AI エージェントと対話するための Web アプリケーションです。FastAPI バックエンドと Streamlit フロントエンドで構成されており、ブラウザからのチャット体験に加えて LINE ログインでユーザーを識別し、会話履歴を MySQL に保存できます。

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
├── static/prompt.txt           # LLM へ送るプロンプトテンプレート
├── mysql/
│   ├── my.cnf                  # MySQL 設定
│   └── db/
│       ├── schema.sql          # users テーブル DDL
│       └── user_messages.sql   # user_messages テーブル DDL
├── test/
│   ├── api_test.sh             # API 動作確認用スクリプト
│   ├── db_connect.sh           # DB 接続確認スクリプト
│   ├── ollama_test.sh          # LLM API 接続確認スクリプト
│   ├── test_components.py      # コンポーネント単体テスト
│   ├── test_workflow.py        # ワークフロー統合テスト
│   └── test_create_user.py     # ユーザー作成テスト
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
3.  **RAGManager（情報検索）**: 必要に応じて、仮説に基づいたサービス情報を検索します（現在はモック実装）。
4.  **ResponsePlanner（応答設計）**: 分析結果と検索結果をもとに、ユーザーへの応答を計画・生成します。

これらは `app/api/workflow.py` で定義されたグラフに従って実行されます。

- **FastAPI バックエンド**: API エンドポイントを提供し、ワークフローを実行
- **Streamlit フロントエンド**: LINE ログインとチャット UI を提供
- **MySQL**: LINE アカウントと紐づくユーザー情報・会話履歴・分析結果を保存
- **LLM 連携**: OpenAI API または Ollama 互換エンドポイントを利用

## 実装のポイント

### バックエンド (FastAPI)
- `/api/v1/users`: LINE ログイン後に呼び出し、ユーザー ID を払い出す
- `/api/v1/user-message`: ユーザーのメッセージを受け取り、LangGraph ワークフローを実行して応答を返却
- `/api/v1/user-messages`: 指定ユーザーの直近メッセージ履歴を取得

### フロントエンド (Streamlit)
- LINE ログインで取得したプロフィールをバックエンドに登録
- チャット UI から API を呼び出し、会話を表示
- `API_URL` 環境変数で接続先 API を切り替え可能

## セットアップ

### 前提条件

- Docker / Docker Compose が利用可能な環境
- LINE ログインチャネル（チャンネル ID・シークレット）
- OpenAI API Key または Ollama などの LLM 推論エンドポイント

### セットアップ手順

1. **リポジトリのクローン**
    ```bash
    git clone https://github.com/dx-junkyard/ai-agent-playground-101.git
    cd ai-agent-playground-101
    ```

2. **環境変数の設定**
    - `.env.example` を `.env` にコピーし、以下を設定します
        - `OPENAI_API_KEY`: LLM アクセス用キー（設定されている場合は優先的に使用されます）
        - `LINE_CHANNEL_ID`, `LINE_CHANNEL_SECRET`, `LINE_REDIRECT_URI`
    - `config.py` の `AI_URL` / `AI_MODEL` を使用する LLM に合わせて変更します

3. **コンテナの起動**
    ```bash
    docker compose up --build
    ```

4. **アプリケーションへのアクセス**
    - UI: http://localhost:8080
    - API: http://localhost:8086
    - MySQL: localhost:3306（ユーザー名 `me`、パスワード `me`）

## 使い方

### Web インターフェース

1. ブラウザで http://localhost:8080 にアクセス
2. 表示される LINE ログインリンクから認証
3. チャット欄にメッセージを入力して送信
4. AI からの応答と会話履歴が画面に表示されます

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

```bash
# 仮想環境の作成と依存関係のインストール
python -m venv venv
source venv/bin/activate
pip install -r requirements.api.txt
pip install pytest

# テストの実行
python -m pytest test/
```

### トラブルシューティング

- PR 作成が失敗する場合は `scripts/debug_pr_creation.py` を実行し、Git のリモート設定やトークン設定など、よくある原因をチェックしてください。

### コード修正時のポイント

- コンポーネントのロジックは `app/api/components/` 配下の各ファイルを修正してください。
- ワークフローの定義は `app/api/workflow.py` にあります。
- `app/api/ai_client.py` は LLM との通信を抽象化しています。

## 拡張アイデア

- RAGManager の実実装（Vector DB との連携）
- 複数 LLM の切り替え UI
- 会話履歴の検索／エクスポート
- LINE 上での直接応答

## ライセンス

このプロジェクトは [MIT ライセンス](LICENSE) の下で公開されています。
