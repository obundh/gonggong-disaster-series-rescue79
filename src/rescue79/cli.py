"""Command-line launcher bound to this computer only."""

from __future__ import annotations

import argparse
import threading
import webbrowser

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Rescue79 local still-image reviewer")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print("\nRescue79 정적 7·9 모델 검토기를 시작합니다.")
    print("이 프로그램은 자동 신고하거나 출동시키지 않습니다.")
    print(f"브라우저가 열리지 않으면 주소창에 입력하세요: {url}")
    print("종료하려면 이 창에서 Ctrl+C를 누르세요.\n")
    uvicorn.run("rescue79.app:app", host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
