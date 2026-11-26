#!/bin/bash
# IssueとPull Request作成スクリプト

set -e

REPO="dx-junkyard/ai-agent-playground-101"
BRANCH="mutsu-dev"
BASE="main"

echo "📋 IssueとPull Requestを作成します"
echo ""

# GitHub CLI認証確認
if ! gh auth status &> /dev/null; then
    echo "❌ GitHub CLIの認証が必要です"
    echo ""
    echo "以下の手順で認証してください:"
    echo "1. ブラウザで https://github.com/login/device を開く"
    echo "2. 認証コードを入力（gh auth login で表示されます）"
    echo "3. 認証完了後、このスクリプトを再実行してください"
    echo ""
    echo "認証を開始するには:"
    echo "  gh auth login"
    exit 1
fi

echo "✅ GitHub CLI認証済み"
echo ""

# Issue作成
echo "📝 Issueを作成中..."
ISSUE_NUMBER=$(gh issue create \
    --repo "$REPO" \
    --title "報告内容整理機能の実装（青梅市向けPoC）" \
    --body-file docs/github_issue_template.md \
    --json number --jq .number)

if [ $? -eq 0 ]; then
    echo "✅ Issue作成完了: #$ISSUE_NUMBER"
    echo "   URL: https://github.com/$REPO/issues/$ISSUE_NUMBER"
else
    echo "❌ Issue作成失敗"
    exit 1
fi

echo ""

# Pull Request作成
echo "📦 Pull Requestを作成中..."
PR_NUMBER=$(gh pr create \
    --repo "$REPO" \
    --base "$BASE" \
    --head "$BRANCH" \
    --title "報告内容整理機能の実装（青梅市向けPoC）" \
    --body-file docs/pr_description.md \
    --json number --jq .number)

if [ $? -eq 0 ]; then
    echo "✅ Pull Request作成完了: #$PR_NUMBER"
    echo "   URL: https://github.com/$REPO/pull/$PR_NUMBER"
else
    echo "❌ Pull Request作成失敗"
    exit 1
fi

echo ""
echo "🎉 完了しました！"
