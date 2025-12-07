import logging
import os
import requests
import json
import streamlit as st

from line_login import ensure_login

logger = logging.getLogger(__name__)


class ChatUI:
    """Main chat UI handling text and voice input."""
    
    API_URL = os.environ.get("API_URL", "http://api:8000/api/v1/user-message-stream")

    @staticmethod
    def call_api_stream(text: str):
        payload = {"message": text}
        if "user_id" in st.session_state:
            payload["user_id"] = st.session_state["user_id"]
        
        try:
            with requests.post(ChatUI.API_URL, json=payload, stream=True) as resp:
                resp.raise_for_status()
                yield from resp.iter_lines()
        except Exception as e:
            st.error(f"送信エラー: {e}")
            yield None

    def _format_message(self, text: str) -> str:
        """
        Streamlitのmarkdown表示用にテキストを整形する。
        改行コードを末尾スペース2つ+改行に変換して、強制的に改行させる。
        """
        if not text:
            return ""
        return text.replace("\n", "  \n")

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
                
                # Handling streaming manually inside audio branch if needed. 
                # For simplicity, assuming audio flow needs updating too or we just focus on text input loop below.
                # Since user requested "ChatUI" mainly. Let's update main loop logic.
                # Audio path using old call_api logic might break if we change API_URL globally or remove call_api.
                # Let's keep call_api for compatibility or refactor audio path too.
                # But to follow instructions strictly, I'll update the main prompt text flow primarily.
                # Ideally audio path should also use stream. 
                
                # Refactoring audio bit:
                reply_text = ""
                with st.chat_message("user"):
                    st.markdown(self._format_message(text))
                
                with st.chat_message("ai"):
                    status_placeholder = st.status("処理を開始します...", expanded=True)
                    try:
                        for line in self.call_api_stream(text):
                            if not line: continue
                            data = json.loads(line)
                            if data["type"] == "progress":
                                status_placeholder.write(data["message"])
                                status_placeholder.update(label=data["message"])
                            elif data["type"] == "result":
                                reply_text = data["message"]
                                status_placeholder.update(label="完了しました！", state="complete", expanded=False)
                    except Exception as e:
                        import traceback
                        logger.error(f"Stream error: {e}")
                        logger.error(traceback.format_exc())
                        reply_text = f"エラーが発生しました: {e}"
                    
                    st.markdown(self._format_message(reply_text))
                
                st.session_state.messages.append({"role": "assistant", "content": reply_text})
                self._rerun()

            elif not text:
                st.session_state.voice_processed = False

        for m in st.session_state.messages:
            with st.chat_message("user" if m["role"] == "user" else "ai"):
                st.markdown(self._format_message(m["content"]))

        prompt = st.chat_input("メッセージを入力...")

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(self._format_message(prompt))

            with st.chat_message("ai"):
                status_placeholder = st.status("処理を開始します...", expanded=True)
                reply_text = ""
                try:
                    for line in self.call_api_stream(prompt):
                        if not line: continue
                        data = json.loads(line)
                        if data["type"] == "progress":
                            status_placeholder.write(data["message"])
                            status_placeholder.update(label=data["message"])
                        elif data["type"] == "result":
                            reply_text = data["message"]
                            status_placeholder.update(label="完了しました！", state="complete", expanded=False)
                except Exception as e:
                    import traceback
                    logger.error(f"Stream error: {e}")
                    logger.error(traceback.format_exc())
                    reply_text = f"エラーが発生しました: {e}"
                
                st.markdown(self._format_message(reply_text))

            st.session_state.messages.append({"role": "assistant", "content": reply_text})


def main():
    ChatUI().run()


if __name__ == "__main__":
    main()
