# AI Agent 開発講座（LINE 連携編）

このプロジェクトは、AI エージェントと対話するための Web アプリケーションです。FastAPI バックエンドと Streamlit フロントエンドで構成されており、ブラウザからのチャット体験に加えて LINE ログインでユーザーを識別し、会話履歴を MySQL に保存できます。

## 学習内容

- Streamlit を使用した Web フロントエンドの構築
- FastAPI バックエンドとの連携
- LINE ログイン (OAuth2) を利用したユーザー認証
- データベースを用いた会話履歴の保存と取得
- 外部 LLM（Ollama 互換 API）との連携

## プロジェクト構成

```
.
├── app/
│   ├── api/                    # FastAPI バックエンド
│   │   ├── main.py             # API エンドポイント
│   │   ├── ai_client.py        # LLM への問い合わせロジック
│   │   └── db.py               # MySQL とのやり取り
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
│   └── ollama_test.sh          # LLM API 接続確認スクリプト
├── config.py                   # アプリ共通設定
├── requirements.api.txt        # API 用 Python 依存関係
├── requirements.ui.txt         # UI 用 Python 依存関係
├── Dockerfile.api              # API 用 Dockerfile
├── Dockerfile.ui               # UI 用 Dockerfile
├── docker-compose.yaml         # Docker Compose 設定
└── .env.example                # 環境変数サンプル
```

## 主要なコンポーネント

- **FastAPI バックエンド**: ユーザー登録、会話履歴の保存・取得、LLM への問い合わせを担当
- **Streamlit フロントエンド**: LINE ログインとチャット UI を提供
- **MySQL**: LINE アカウントと紐づくユーザー情報・会話履歴を保存
- **LLM 連携**: `config.py` で指定した Ollama 互換エンドポイントから応答を生成

## 実装のポイント

### バックエンド (FastAPI)
- `/api/v1/users`: LINE ログイン後に呼び出し、ユーザー ID を払い出す
- `/api/v1/user-message`: ユーザーのメッセージを受け取り LLM 応答を返却・DB に保存
- `/api/v1/user-messages`: 指定ユーザーの直近メッセージ履歴を取得

### フロントエンド (Streamlit)
- LINE ログインで取得したプロフィールをバックエンドに登録
- チャット UI から API を呼び出し、会話を表示
- `API_URL` 環境変数で接続先 API を切り替え可能

## セットアップ

### 前提条件

- Docker / Docker Compose が利用可能な環境
- LINE ログインチャネル（チャンネル ID・シークレット）
- Ollama などの LLM 推論エンドポイント（デフォルトは `http://host.docker.internal:11434`）

### セットアップ手順

1. **リポジトリのクローン**
    ```bash
    git clone https://github.com/dx-junkyard/ai-agent-playground-101.git
    cd ai-agent-playground-101
    ```

2. **環境変数の設定**
    - `.env.example` を `.env` にコピーし、以下を設定します
        - `OPENAI_API_KEY`: OpenAI へのアクセスキー
        - `OPENAI_MODEL`: 利用したい OpenAI モデル（既定は `gpt-4o-mini`）
        - `OPENAI_API_BASE`: OpenAI 互換エンドポイントを利用する場合のみ設定（通常は不要）
        - `LINE_PROVIDER_NAME`, `LINE_PROVIDER_ID`: 利用する LINE プロバイダー情報（既定は `ai-agent` / `2004639780`）
        - `LINE_CHANNEL_ID`, `LINE_CHANNEL_SECRET`: LINE ログインチャネルのクレデンシャル
        - `LINE_REDIRECT_URI`: LINE Developers に登録したコールバック URL（開発環境では `http://localhost:8080`）
        - `DISABLE_LINE_LOGIN`: 開発中に LINE ログインをスキップしたい場合は `true`
    - `config.py` では上記の環境変数からモデルやエンドポイントを参照するようになっています

    > ⚠️ LINE Developers で `ai-agent` プロバイダー（ID: `2004639780`）配下にチャネルを作成し、同チャネルの **チャネル ID** と **チャネルシークレット** を `.env` に転記してください。未設定の場合、UI 上でエラーが表示されログインできません。

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

### ローカルでの確認

- `test/api_test.sh`: API エンドポイントの疎通確認
- `test/db_connect.sh`: MySQL 接続確認

### トラブルシューティング

- OpenAI からの応答が得られない場合は `OPENAI_API_KEY` の設定、組織・プロジェクト権限、API 利用制限をご確認ください。
- PR 作成が失敗する場合は `scripts/debug_pr_creation.py` を実行し、Git のリモート設定やトークン設定など、よくある原因をチェックしてください。

### コード修正時のポイント

- `app/api/ai_client.py` のプロンプトは `static/prompt.txt` から読み込み
- `app/ui/line_login.py` で LINE OAuth のコールバック処理とユーザー登録を実施
- 依存関係を追加する場合は各 `requirements.*.txt` を更新してください

## 拡張アイデア

- 音声入力・読み上げ機能の追加
- 複数 LLM の切り替え UI
- 会話履歴の検索／エクスポート
- LINE 上での直接応答
- Streamlit フロントエンドには、窓口選択・進捗バー・バッジ・デイリーミッションなどのゲーミフィケーション要素を追加。
- 会話内容から年齢・家族構成・興味／運動歴などを抽出し、`user_profiles` テーブルにカルテとして保存。
- プロンプトを行政窓口仕様に刷新し、必須情報のヒアリングと案内フローを強化。

## ライセンス

このプロジェクトは [MIT ライセンス](LICENSE) の下で公開されています。
