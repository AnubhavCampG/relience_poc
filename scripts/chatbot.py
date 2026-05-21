#!/usr/bin/env python
"""Interactive CLI for the Reliance AI Copilot."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.agent.graph import run_agent_turn  # noqa: E402


def chat() -> None:
    print("Welcome to the Reliance AI Copilot! (Type 'exit' to quit)")
    print("Tip: pdf:path/to/file.pdf Summarize this  |  add --ocr for scanned PDFs")
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        pdf_path = None
        use_ocr = False
        message = user_input

        if user_input.lower().startswith("pdf:"):
            parts = user_input[4:].strip().split(maxsplit=1)
            if parts:
                pdf_path = parts[0]
                message = parts[1] if len(parts) > 1 else "Summarize this PDF document."
            if "--ocr" in message:
                use_ocr = True
                message = message.replace("--ocr", "").strip()

        try:
            result = run_agent_turn(message, pdf_path=pdf_path, use_ocr=use_ocr)
            answer = result.get("final_answer", "I could not process your request.")
            print(f"\nAI: {answer}")
            if result.get("generated_sql"):
                print(f"\n[SQL] {result['generated_sql']}")
            if result.get("pdf_result", {}).get("file"):
                print(f"\n[PDF] {result['pdf_result']['file']}")
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    chat()
