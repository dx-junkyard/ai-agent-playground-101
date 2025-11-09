import logging
import os
import random
import re
import textwrap

import requests
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards

from line_login import ensure_login

logger = logging.getLogger(__name__)

API_URL = os.environ.get("API_URL", "http://api:8000/api/v1/user-message")

INFO_ITEMS = [
    {
        "key": "age",
        "label": "年齢",
        "patterns": [r"\b\d{1,3}\s*(歳|才)"],
        "hint": "ご本人様や対象の方の年齢を教えてください",
    },
    {
        "key": "household",
        "label": "家族構成",
        "patterns": [r"家族", r"夫", r"妻", r"子ども", r"世帯", r"同居"],
        "hint": "一緒にお住まいのご家族について伺ってもよろしいでしょうか",
    },
    {
        "key": "residence",
        "label": "居住状況",
        "patterns": [r"市内", r"国分寺", r"在住", r"転入", r"転出", r"引っ越"],
        "hint": "国分寺市にお住まいか、転入・転出のご予定かを教えてください",
    },
    {
        "key": "address",
        "label": "住所・予定地",
        "patterns": [r"丁目", r"番地", r"住所", r"町"],
        "hint": "差し支えなければ町名など大まかな住所を伺います",
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
        "key": "interests",
        "label": "興味・関心",
        "patterns": [r"趣味", r"好き", r"興味", r"楽し"],
        "hint": "差し支えなければ好きなことや興味のあることを伺えますか",
    },
    {
        "key": "exercise",
        "label": "運動歴",
        "patterns": [r"運動", r"スポーツ", r"トレーニング", r"体操"],
        "hint": "普段されている運動やスポーツがあれば教えてください",
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
    {"key": "age", "text": "年齢を伺おう"},
    {"key": "household", "text": "家族構成を把握しよう"},
    {"key": "interests", "text": "興味のあることを聞き出そう"},
    {"key": "exercise", "text": "運動歴を確認しよう"},
    {"key": "residence", "text": "居住状況を確認しよう"},
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
                {
                    "role": "assistant",
                    "content": "こんにちは。国分寺市役所オンライン相談窓口です。お困りごとがスムーズに解決できるよう、一緒に進めてまいりますね。",
                    "summary": "初回案内: 利用者に寄り添った挨拶",
                }
            ]
        if "info_status" not in st.session_state:
            st.session_state.info_status = {item["key"]: False for item in INFO_ITEMS}
        if "daily_mission" not in st.session_state:
            st.session_state.daily_mission = random.choice(DAILY_MISSIONS)
        if "mission_completed" not in st.session_state:
            st.session_state.mission_completed = False
        if "window_selected" not in st.session_state:
            st.session_state.window_selected = None
        if "confirmation_required" not in st.session_state:
            st.session_state.confirmation_required = False
        if "awaiting_feedback" not in st.session_state:
            st.session_state.awaiting_feedback = False

        self._refresh_progress()

    def _refresh_progress(self):
        st.session_state.info_status.update(_analyze_information(st.session_state.messages))
        mission_key = st.session_state.daily_mission["key"]
        if st.session_state.info_status.get(mission_key):
            st.session_state.mission_completed = True

    def _render_sidebar(self):
        st.sidebar.image(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Kokubunji_city_logo.svg/512px-Kokubunji_city_logo.svg.png",
            width=120,
        )
        st.sidebar.title("ご相談ナビゲーター")

        completed = sum(1 for v in st.session_state.info_status.values() if v)
        total = len(INFO_ITEMS)
        st.sidebar.progress(completed / total)
        st.sidebar.caption(f"確認が進んだ項目: {completed}/{total}")

        earned, next_badge = _calc_badges(completed)
        if earned:
            st.sidebar.success("🌟 これまでに確認できたこと: " + " / ".join(earned))
        if next_badge:
            threshold, badge_name = next_badge
            remaining = threshold - completed
            st.sidebar.info(f"あと {remaining} 項目ほど伺えれば『{badge_name}』レベルです")

        mission = st.session_state.daily_mission
        if st.session_state.mission_completed:
            st.sidebar.success(f"🎯 本日の確認ポイント達成: {mission['text']}")
        else:
            st.sidebar.warning(f"🎯 本日の確認ポイント: {mission['text']} (お手続きがスムーズになります)")

        with st.sidebar.expander("これまで伺えた内容", expanded=True):
            for item in INFO_ITEMS:
                status = "✅" if st.session_state.info_status[item["key"]] else "⏳"
                st.write(f"{status} {item['label']}")

    def _render_hint_bar(self):
        missing_items = [item for item in INFO_ITEMS if not st.session_state.info_status[item["key"]]]
        if not missing_items:
            st.success("必要な情報はそろいました。続けて気になる点があれば遠慮なくお知らせください。")
            st.session_state.mission_completed = True
            return

        suggestions = textwrap.shorten(" / ".join(item["hint"] for item in missing_items[:2]), width=120)
        st.info(f"📌 次に伺うとお役に立てそうな内容: {suggestions}")

    def _ensure_window_selection(self):
        if st.session_state.window_selected:
            return

        st.header("まずはご相談内容に近い窓口をお選びください")
        options = [
            "住民票・印鑑証明", "戸籍・転入転出", "子育て・教育", "高齢者支援", "国民健康保険・年金",
            "税金・納付", "事業者向け相談", "その他総合案内",
        ]
        choice = st.radio("以下から最も近いものをお選びいただくと、ご案内がスムーズになります。", options, index=0)
        if st.button("この内容で相談を進める", type="primary"):
            st.session_state.window_selected = choice
            st.session_state.messages.append({"role": "user", "content": f"窓口選択: {choice}"})
            self._refresh_progress()
            self._rerun()
        st.stop()

    def _render_confirmation_prompt(self):
        if not st.session_state.messages or not st.session_state.confirmation_required:
            return

        st.success("直前のご案内について、内容をご確認ください。問題がなければ『大丈夫』を、修正が必要な場合は『修正してほしい』を選んでください。")
        cols = st.columns(2)
        with cols[0]:
            if st.button("大丈夫です", key="confirm_ok"):
                st.session_state.confirmation_required = False
                st.session_state.messages.append({"role": "user", "content": "OK: 内容に問題はありません。"})
                self._refresh_progress()
                self._rerun()
        with cols[1]:
            if st.button("修正してほしい", key="confirm_ng"):
                st.session_state.awaiting_feedback = True
                st.session_state.confirmation_required = True
                self._rerun()

        if st.session_state.awaiting_feedback:
            feedback = st.text_area("修正してほしい点を教えてください", key="ng_feedback")
            submit_disabled = not feedback.strip()
            if st.button("修正依頼を送信", disabled=submit_disabled):
                feedback_text = feedback.strip()
                st.session_state.awaiting_feedback = False
                st.session_state.confirmation_required = False
                st.session_state.ng_feedback = ""

                st.session_state.messages.append({"role": "user", "content": f"修正希望: {feedback_text}"})
                reply = self.call_api(feedback_text)
                reply_display = reply.replace("\\n", "\n")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": reply_display,
                        "meta": [
                            {"label": "いま伺えた内容", "value": f"{sum(st.session_state.info_status.values())}/{len(INFO_ITEMS)}"},
                            {"label": "本日の確認ポイント", "value": st.session_state.daily_mission["text"]},
                        ],
                        "summary": "いただいたご要望を反映しました。引き続き気になる点があればお知らせください。",
                    }
                )
                st.session_state.confirmation_required = True
                self._refresh_progress()
                self._rerun()

    def _render_conversation(self):
        for index, message in enumerate(st.session_state.messages):
            role = "user" if message["role"] == "user" else "assistant"
            with st.chat_message("user" if role == "user" else "ai"):
                if role == "assistant" and message.get("meta"):
                    meta = message["meta"]
                    cols = st.columns(len(meta))
                    for col, item in zip(cols, meta):
                        with col:
                            st.metric(item["label"], item["value"])
                    style_metric_cards(border_left_color="#f0ad4e")
                st.markdown(message["content"], help=message.get("hint"))
                if role == "assistant" and message.get("summary"):
                    st.caption(message["summary"])

    def run(self):
        st.set_page_config(page_title="国分寺市 窓口チャット", page_icon="🏢", layout="wide")
        ensure_login()
        self._init_session()
        self._render_sidebar()

        self._ensure_window_selection()

        st.title("国分寺市役所 行政窓口チャット")
        self._render_hint_bar()

        self._render_conversation()
        self._render_confirmation_prompt()

        if st.session_state.confirmation_required:
            st.info("直前の回答についての確認を優先しています。上部のボタンからご回答ください。")
            return

        prompt = st.chat_input("気になっていることや手続きのご相談内容をご自由に入力してください")

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            self._refresh_progress()
            with st.chat_message("user"):
                st.markdown(prompt)

            reply = self.call_api(prompt)
            reply_display = reply.replace("\\n", "\n")
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": reply_display,
                    "meta": [
                        {"label": "いま伺えた内容", "value": f"{sum(st.session_state.info_status.values())}/{len(INFO_ITEMS)}"},
                        {"label": "本日の確認ポイント", "value": st.session_state.daily_mission["text"]},
                    ],
                    "summary": "不安な点があれば続けてお知らせください。",
                }
            )
            st.session_state.confirmation_required = True
            with st.chat_message("ai"):
                st.markdown(reply_display)

            self._refresh_progress()
            self._rerun()


def main():
    ChatUI().run()


if __name__ == "__main__":
    main()
