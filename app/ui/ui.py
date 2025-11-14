import logging
import os
import requests
import streamlit as st

from line_login import ensure_login

logger = logging.getLogger(__name__)

API_URL = os.environ.get("API_URL", "http://api:8000/api/v1/user-message")


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

    def run(self):
        ensure_login()
        st.set_page_config(page_title="AI チャットアプリ", page_icon="🤖")

        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "こんにちは！何かお困りのことはありますか？"}
            ]

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

        prompt = st.chat_input("メッセージを入力...")

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            reply = self.call_api(prompt)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            with st.chat_message("ai"):
                st.markdown(reply)


def main():
    ChatUI().run()


if __name__ == "__main__":
    main()
