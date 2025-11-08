import logging
import os
import random
import re
import textwrap

import requests
import streamlit as st

from line_login import ensure_login

logger = logging.getLogger(__name__)

API_URL = os.environ.get("API_URL", "http://api:8000/api/v1/user-message")

INFO_ITEMS = [
    {
        "key": "residence",
        "label": "居住状況",
        "patterns": [r"市内", r"国分寺", r"在住", r"転入", r"転出", r"引っ越"],
        "hint": "国分寺市にお住まいか、転入・転出のご予定かを教えてください",
    },
    {
        "key": "address",
        "label": "住所・予定地",
        "patterns": [r"丁目", r"丁目", r"住所", r"町"],
        "hint": "差し支えなければ町名など大まかな住所を伺います",
    },
    {
        "key": "household",
        "label": "世帯構成",
        "patterns": [r"家族", r"夫", r"妻", r"子ども", r"世帯", r"同居"],
        "hint": "ご一緒にお住まいのご家族について教えてください",
    },
    {
        "key": "age_group",
        "label": "対象者の年齢層",
        "patterns": [r"歳", r"才", r"児童", r"高齢", r"学生"],
        "hint": "ご相談の対象となる方の年齢や世代を教えてください",
    },
    {
        "key": "purpose",
        "label": "相談目的",
        "patterns": [r"手続", r"申請", r"相談", r"証明", r"補助", r"支援"],
        "hint": "どのような手続きやご相談をご希望でしょうか",
    },
    {
        "key": "documents",
        "label": "必要書類",
        "patterns": [r"書類", r"必要", r"持参", r"持ち物"],
        "hint": "ご不明な書類があれば教えてください",
    },
    {
        "key": "urgency",
        "label": "期限・緊急度",
        "patterns": [r"いつまで", r"期限", r"早め", r"急", r"本日"],
        "hint": "いつ頃までに手続きを済ませたいか伺えますか",
    },
    {
        "key": "method",
        "label": "手続き方法",
        "patterns": [r"窓口", r"来庁", r"オンライン", r"郵送"],
        "hint": "来庁予定かオンライン・郵送などご希望の方法を教えてください",
    },
    {
        "key": "considerations",
        "label": "配慮事項",
        "patterns": [r"体", r"障害", r"言語", r"仕事", r"勤務", r"育児"],
        "hint": "特に配慮が必要な事情があればお知らせください",
    },
]

BADGES = [
    (3, "聞き取り上手"),
    (6, "市民サポーター"),
    (9, "窓口マスター"),
]

DAILY_MISSIONS = [
    "居住状況を聞き出そう",
    "相談目的を明確にしよう",
    "必要書類を確認しよう",
    "期限や希望日を確認しよう",
    "来庁かオンラインか希望を聞き出そう",
]


def _combine_user_messages(messages):
    return "\n".join(m["content"] for m in messages if m["role"] == "user").lower()


def _analyze_information(messages):
    combined = _combine_user_messages(messages)
    analysis = {}
    for item in INFO_ITEMS:
        found = any(re.search(pattern, combined) for pattern in item["patterns"])
        analysis[item["key"]] = found
    return analysis


def _calc_badges(completed_count):
    earned = [badge for threshold, badge in BADGES if completed_count >= threshold]
    for threshold, badge in BADGES:
        if completed_count < threshold:
            return earned, (threshold, badge)
    return earned, None


class ChatUI:
    """Main chat UI handling text and voice input."""

    @staticmethod
    def call_api(text: str) -> str:
        payload = {"message": text}
        if "user_id" in st.session_state:
            payload["user_id"] = st.session_state["user_id"]
        try:
            resp = requests.post(API_URL, json=payload)
            resp.raise_for_status()
            return resp.text.strip()
        except Exception as e:
            st.error(f"送信エラー: {e}")
            return "エラーが発生しました"

    def _rerun(self):
        """Rerun Streamlit script with backward compatibility."""
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            st.rerun()

    def _init_session(self):
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "ようこそ！国分寺市窓口チャレンジへ。質問にお答えいただくと進捗がたまります✨"}
            ]
        if "info_status" not in st.session_state:
            st.session_state.info_status = {item["key"]: False for item in INFO_ITEMS}
        if "daily_mission" not in st.session_state:
            st.session_state.daily_mission = random.choice(DAILY_MISSIONS)
        if "mission_completed" not in st.session_state:
            st.session_state.mission_completed = False

        st.session_state.info_status.update(_analyze_information(st.session_state.messages))

    def _render_sidebar(self):
        st.sidebar.image(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Kokubunji_city_logo.svg/512px-Kokubunji_city_logo.svg.png",
            width=120,
        )
        st.sidebar.title("窓口チャレンジ")

        completed = sum(1 for v in st.session_state.info_status.values() if v)
        total = len(INFO_ITEMS)
        st.sidebar.progress(completed / total)
        st.sidebar.caption(f"情報取得: {completed}/{total}")

        earned, next_badge = _calc_badges(completed)
        if earned:
            st.sidebar.success("🏅 獲得バッジ: " + " / ".join(earned))
        if next_badge:
            threshold, badge_name = next_badge
            remaining = threshold - completed
            st.sidebar.info(f"次のバッジ『{badge_name}』まであと {remaining} 項目")

        mission_text = st.session_state.daily_mission
        if st.session_state.mission_completed:
            st.sidebar.success(f"🎯 デイリーミッション達成！: {mission_text}")
        else:
            st.sidebar.warning(f"🎯 今日のミッション: {mission_text}")

        with st.sidebar.expander("情報チェックリスト", expanded=True):
            for item in INFO_ITEMS:
                status = "✅" if st.session_state.info_status[item["key"]] else "⏳"
                st.write(f"{status} {item['label']}")

    def _render_hint_bar(self):
        missing_items = [item for item in INFO_ITEMS if not st.session_state.info_status[item["key"]]]
        if not missing_items:
            st.success("必要な情報がそろいました！追加で気になることがあればお知らせください。")
            st.session_state.mission_completed = True
            return

        suggestions = textwrap.shorten(" / ".join(item["hint"] for item in missing_items[:2]), width=120)
        st.info(f"🏁 次の質問ヒント: {suggestions}")

    def run(self):
        st.set_page_config(page_title="国分寺市 窓口チャット", page_icon="🏢", layout="wide")
        ensure_login()
        self._init_session()
        self._render_sidebar()

        st.title("国分寺市役所 行政窓口チャット")
        self._render_hint_bar()

        if "last_audio" in st.session_state:
            text = self.voice.transcribe(st.session_state.pop("last_audio"))
            if text and not st.session_state.voice_processed:
                st.session_state.voice_processed = True
                st.session_state.messages.append({"role": "user", "content": text})
                reply = self.call_api(text)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                self._rerun()
            elif not text:
                st.session_state.voice_processed = False

        for m in st.session_state.messages:
            with st.chat_message("user" if m["role"] == "user" else "ai"):
                st.markdown(m["content"])

        prompt = st.chat_input("相談内容を入力してください。記入するたびにポイントが貯まります！")

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            reply = self.call_api(prompt)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            with st.chat_message("ai"):
                st.markdown(reply)

            st.session_state.info_status.update(_analyze_information(st.session_state.messages))
            if st.session_state.daily_mission and any(
                st.session_state.info_status[item["key"]]
                for item in INFO_ITEMS
                if item["label"] in st.session_state.daily_mission
            ):
                st.session_state.mission_completed = True

            self._rerun()


def main():
    ChatUI().run()


if __name__ == "__main__":
    main()
