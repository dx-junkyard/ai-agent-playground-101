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

API_URL = os.environ.get("API_URL", "http://localhost:8080/api/v1/user-message")

# 福岡市版：カテゴリと情報項目
INFO_ITEMS = [
    {
        "key": "ward",
        "label": "区",
        "patterns": [r"東区", r"博多区", r"中央区", r"南区", r"城南区", r"早良区", r"西区"],
        "hint": "福岡市のどの区の内容ですか？",
    },
    {
        "key": "location",
        "label": "場所",
        "patterns": [r"駅", r"通り", r"丁目", r"番地", r"交差点", r"公園", r"川", r"住所"],
        "hint": "場所はどこですか？（住所／近くの施設名／交差点名など）",
    },
    {
        "key": "road_damage",
        "label": "道路損傷",
        "patterns": [r"道路", r"傷み", r"破損", r"穴"],
        "hint": "道路の損傷について詳しく教えてください",
    },
    {
        "key": "streetlight",
        "label": "街路灯",
        "patterns": [r"街灯", r"街路灯", r"照明"],
        "hint": "街路灯の故障について詳しく教えてください",
    },
    {
        "key": "garbage",
        "label": "ごみ散乱",
        "patterns": [r"ごみ", r"散乱", r"落ちてる"],
        "hint": "ごみの散乱について詳しく教えてください",
    },
    {
        "key": "illegal_dumping",
        "label": "不法投棄",
        "patterns": [r"不法投棄", r"捨ててる"],
        "hint": "不法投棄について詳しく教えてください",
    },
    {
        "key": "wildlife",
        "label": "獣害",
        "patterns": [r"イノシシ", r"野生", r"動物", r"害獣"],
        "hint": "野生鳥獣による被害について詳しく教えてください",
    },
    {
        "key": "time",
        "label": "発見時期",
        "patterns": [r"今日", r"昨日", r"先週", r"朝", r"昼", r"夜", r"最近"],
        "hint": "いつ頃（いつから）気づきましたか？",
    },
    {
        "key": "details",
        "label": "詳細",
        "patterns": [r"状況", r"状態", r"詳しく"],
        "hint": "状況をもう少し詳しく教えてください",
    },
]

BADGES = [
    (3, "情報収集の達人"),
    (5, "福岡市サポーター"),
    (7, "窓口案内マスター"),
]

DAILY_MISSIONS = [
    {"key": "ward", "text": "区を確認しよう"},
    {"key": "location", "text": "場所を把握しよう"},
    {"key": "road_damage", "text": "道路損傷の情報を集めよう"},
    {"key": "streetlight", "text": "街路灯の情報を集めよう"},
    {"key": "garbage", "text": "ごみ散乱の情報を集めよう"},
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
                    "content": "こんにちは。福岡市役所オンライン相談窓口です。道路・街路灯・ごみ・不法投棄・獣害などのお困りごとについて、適切な担当課をご案内いたします。お気軽にご相談ください。",
                    "summary": "初回案内: 福岡市の相談窓口案内",
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
        st.sidebar.title("🏢 福岡市 相談窓口ナビ")

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

        st.header("まずはお困りごとの種類をお選びください")
        options = [
            "道路の損傷・陥没", "街路灯の故障", "公園の損傷", "河川・排水の問題",
            "ごみの散乱", "不法投棄", "野生鳥獣による被害", "その他",
        ]
        choice = st.radio("以下から最も近いものをお選びいただくと、適切な担当課をご案内できます。", options, index=0)
        if st.button("この内容で相談を進める", type="primary"):
            st.session_state.window_selected = choice
            st.session_state.messages.append({"role": "user", "content": f"相談内容: {choice}"})
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
        st.set_page_config(page_title="福岡市 相談窓口チャット", page_icon="🏢", layout="wide")
        ensure_login()
        self._init_session()
        self._render_sidebar()

        self._ensure_window_selection()

        st.title("福岡市役所 相談窓口チャット")
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
