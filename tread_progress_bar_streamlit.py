import streamlit as st
import threading
import time
import queue
import sys
import os
from dotenv import load_dotenv

# 환경 변수 로딩
# if getattr(sys, "frozen", False):
#     current_path = sys._MEIPASS
# else:
#     current_path = os.path.dirname(os.path.abspath(__file__))

# env_file_path = os.path.join(current_path, ".env")
env_file_path = os.path.join(sys._MEIPASS, ".env") if getattr(sys, "forzen", False) else ".env"
load_dotenv(env_file_path)
VERSION = os.getenv("VERSION", "1.0.0")
AUTHOR = os.getenv("AUTHOR", "Unknown")

# Worker thread class
class WorkerThread(threading.Thread):
    def __init__(self, progress_queue):
        super().__init__()
        self.progress_queue = progress_queue
        self._running = True

    def run(self):
        try:
            for second in range(1, 11):
                if not self._running:
                    self.progress_queue.put("작업이 취소되었습니다.")
                    return
                self.progress_queue.put(f"{second}초 동안 작업중.")
                time.sleep(1)
            self.progress_queue.put("총 작업 시간은: 10초 입니다.")
        except Exception as e:
            self.progress_queue.put(f"오류 발생: {str(e)}")

    def stop(self):
        self._running = False

# 진행 상태를 폴링하는 함수
def poll_progress():
    if st.session_state.worker is not None and st.session_state.worker.is_alive():
        try:
            # 큐에서 모든 메시지 처리
            while True:
                message = st.session_state.progress_queue.get_nowait()
                st.session_state.status = message
                if "초 동안 작업중" in message:
                    seconds = int(message.split("초")[0])
                    st.session_state.progress = seconds / 10.0
                elif "총 작업 시간은" in message:
                    st.session_state.progress = 1.0
                    st.session_state.start_disabled = False
                    st.session_state.cancel_disabled = True
                    st.session_state.worker = None
                    st.session_state.status = "작업 완료"
                elif "오류 발생" in message or "작업이 취소되었습니다" in message:
                    st.session_state.start_disabled = False
                    st.session_state.cancel_disabled = True
                    st.session_state.worker = None
                    st.session_state.status = message
                # UI 즉시 업데이트
                status_placeholder.write(st.session_state.status)
                progress_placeholder.progress(st.session_state.progress)
        except queue.Empty:
            pass
        # 스레드가 살아있으면 주기적으로 재실행
        if st.session_state.worker is not None and st.session_state.worker.is_alive():
            time.sleep(0.1)  # 짧은 대기 후 재실행
            st.rerun()
    else:
        # 스레드가 종료되었으면 상태 초기화
        if st.session_state.worker is not None:
            st.session_state.worker.join()
            st.session_state.worker = None
            st.session_state.start_disabled = False
            st.session_state.cancel_disabled = True
            status_placeholder.write(st.session_state.status)
            progress_placeholder.progress(st.session_state.progress)
            st.rerun()

# Streamlit app
def main():
    st.title("간단한 스레드 예제")

    # Initialize session state
    if "worker" not in st.session_state:
        st.session_state.worker = None
    if "status" not in st.session_state:
        st.session_state.status = "준비"
    if "progress" not in st.session_state:
        st.session_state.progress = 0
    if "start_disabled" not in st.session_state:
        st.session_state.start_disabled = False
    if "cancel_disabled" not in st.session_state:
        st.session_state.cancel_disabled = True
    if "progress_queue" not in st.session_state:
        st.session_state.progress_queue = queue.Queue()

    # Status display
    global status_placeholder, progress_placeholder
    status_placeholder = st.empty()
    status_placeholder.write(st.session_state.status)

    # Progress bar
    progress_placeholder = st.progress(st.session_state.progress)

    # Buttons
    col1, col2 = st.columns(2)
    with col1:
        start_button = st.button("작업 시작", disabled=st.session_state.start_disabled)
    with col2:
        cancel_button = st.button("작업 취소", disabled=st.session_state.cancel_disabled)

    # Start button logic
    if start_button and st.session_state.worker is None:
        st.session_state.status = "작업 중..."
        st.session_state.start_disabled = True
        st.session_state.cancel_disabled = False
        st.session_state.progress = 0
        st.session_state.progress_queue = queue.Queue()  # 새 큐로 초기화
        st.session_state.worker = WorkerThread(st.session_state.progress_queue)
        st.session_state.worker.start()
        status_placeholder.write(st.session_state.status)
        progress_placeholder.progress(st.session_state.progress)
        st.rerun()

    # Cancel button logic
    if cancel_button and st.session_state.worker is not None:
        st.session_state.worker.stop()
        st.session_state.worker.join()
        st.session_state.worker = None
        st.session_state.start_disabled = False
        st.session_state.cancel_disabled = True
        st.session_state.status = "작업이 취소되었습니다."
        st.session_state.progress = 0
        status_placeholder.write(st.session_state.status)
        progress_placeholder.progress(st.session_state.progress)
        st.rerun()

    # 진행 상태 폴링
    poll_progress()

    # Footer
    st.markdown("---")
    col3, col4 = st.columns(2)
    with col3:
        st.write(f"Ver. {VERSION}")
    with col4:
        st.markdown(f"<div style='text-align: right;'>Made by {AUTHOR}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()