#!/bin/bash
# FooQoo/airs へのPull Request作成スクリプト

set -e

UPSTREAM_REPO="FooQoo/airs"
UPSTREAM_BASE="main"
CURRENT_BRANCH="mutsu-dev"

echo "📋 FooQoo/airs へのPull Requestを作成します"
echo ""

# GitHub CLI認証確認
if ! gh auth status &> /dev/null; then
    echo "❌ GitHub CLIの認証が必要です"
    echo ""
    echo "以下のコマンドで認証してください:"
    echo "  gh auth login"
    exit 1
fi

echo "✅ GitHub CLI認証済み"
echo ""

# 現在のユーザー名を取得
GITHUB_USER=$(gh api user --jq .login)
echo "👤 GitHubユーザー: $GITHUB_USER"
echo ""

# フォークしたリポジトリ名
FORK_REPO="$GITHUB_USER/airs"

# フォークの確認
echo "🔍 フォークを確認中..."
if ! gh repo view "$FORK_REPO" &> /dev/null; then
    echo "📦 フォークを作成中..."
    gh repo fork "$UPSTREAM_REPO" --clone=false
    echo "✅ フォーク作成完了: $FORK_REPO"
else
    echo "✅ フォーク済み: $FORK_REPO"
fi
echo ""

# リモートの確認・追加
echo "🔍 リモートを確認中..."
if ! git remote get-url foogoo-fork &> /dev/null; then
    echo "📝 リモート 'foogoo-fork' を追加中..."
    git remote add foogoo-fork "https://github.com/$FORK_REPO.git"
    echo "✅ リモート追加完了"
else
    echo "✅ リモート 'foogoo-fork' は既に存在します"
fi
echo ""

# 現在のブランチを確認
CURRENT_BRANCH=$(git branch --show-current)
echo "🌿 現在のブランチ: $CURRENT_BRANCH"
echo ""

# フォークしたリポジトリにプッシュ
echo "📤 フォークしたリポジトリにプッシュ中..."
git push foogoo-fork "$CURRENT_BRANCH" --force-with-lease 2>&1 | head -10

if [ $? -eq 0 ]; then
    echo "✅ プッシュ完了"
else
    echo "❌ プッシュ失敗"
    exit 1
fi
echo ""

# Pull Request作成
echo "📦 Pull Requestを作成中..."
PR_URL=$(gh pr create \
    --repo "$UPSTREAM_REPO" \
    --base "$UPSTREAM_BASE" \
    --head "$GITHUB_USER:$CURRENT_BRANCH" \
    --title "報告内容整理機能の実装（青梅市向けPoC）" \
    --body-file docs/pr_description.md \
    --json url --jq .url)

if [ $? -eq 0 ]; then
    echo "✅ Pull Request作成完了"
    echo "   URL: $PR_URL"
else
    echo "❌ Pull Request作成失敗"
    exit 1
fi

echo ""
echo "🎉 完了しました！"
echo ""
echo "【次のステップ】"
echo "1. Pull RequestのURLを確認: $PR_URL"
echo "2. FooQooさんにレビュー依頼をしてください"
