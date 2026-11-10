"""Pull the exact model calls of a conversation: the prompt, the tools offered and the response.

The running server keeps every model call of a conversation in memory, and sends them on the
Inspector's socket.io channel when a client asks for the session. This script asks for them.

    # print one call as text (default: the last call)
    python -m eval.export_model_calls <conversation_id> [--call N]

    # export every call of the conversations named in files (for example run_N.txt of a suite run)
    # as JSON lines: one line per model call, with the messages and the response
    python -m eval.export_model_calls --ids-from eval/results/<stamp>/*/run_*.txt --jsonl calls.jsonl

The server must run with the Inspector (`rasa run --inspect`), and the conversations must still be
in its tracker store: a restart of the default in-memory store empties it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

import socketio

DEFAULT_URL = "http://localhost:5005"
# Conversation ids that the scenario runner (`sim-<uuid>`) and eval/probe.py (`<prefix>-<hex8>`) make.
_CONVERSATION_ID = re.compile(r"\b(sim-[0-9a-f-]{36}|[a-z]+-[0-9a-f]{8})\b")


async def pull_calls(conversation_id: str, url: str = DEFAULT_URL, timeout: float = 30) -> list[dict[str, Any]]:
    """Every model call of one conversation, oldest first."""
    received = asyncio.Event()
    payload: dict[str, Any] = {}
    client = socketio.AsyncClient()

    @client.on("tracker")
    async def _on_session(data: dict[str, Any]) -> None:
        payload.update(data)
        received.set()

    await client.connect(url, socketio_path="inspector.io", transports=["websocket"])
    try:
        await client.emit("session_request", {"session_id": conversation_id})
        await asyncio.wait_for(received.wait(), timeout)
    finally:
        await client.disconnect()
    return (payload.get("skill_state") or {}).get("llm_calls") or []


def _content_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):
        content = " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content or "")


def format_output(call: dict[str, Any]) -> str:
    lines = [
        f"tools offered: {', '.join(call.get('tool_names') or [])}",
        f"tools called:  {', '.join(call.get('response_tool_names') or []) or '(none, text reply)'}",
        "",
    ]
    for message in call.get("prompt_messages") or []:
        lines += [f"===== {message.get('role')} =====", _content_text(message), ""]
    lines += ["===== response =====", json.dumps(call.get("response") or call.get("response_text"), indent=1, default=str)]
    return "\n".join(lines)


def _ids_from(files: list[str]) -> list[str]:
    ids: list[str] = []
    for name in files:
        for found in _CONVERSATION_ID.findall(Path(name).read_text(errors="replace")):
            if found not in ids:
                ids.append(found)
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("conversation_id", nargs="?", help="one conversation to print")
    parser.add_argument("--call", type=int, default=-1, help="the call to print; negative counts from the end")
    parser.add_argument("--ids-from", nargs="+", default=[], help="files to take conversation ids from")
    parser.add_argument("--jsonl", default="", help="write every call of every conversation to this file")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()

    ids = ([args.conversation_id] if args.conversation_id else []) + _ids_from(args.ids_from)
    if not ids:
        parser.error("give a conversation id or --ids-from")

    if args.jsonl:
        count = 0
        with open(args.jsonl, "w") as out:
            for conversation_id in ids:
                for index, call in enumerate(asyncio.run(pull_calls(conversation_id, args.url))):
                    out.write(json.dumps({"conversation_id": conversation_id, "call_index": index, **call}, default=str) + "\n")
                    count += 1
        print(f"{count} model calls of {len(ids)} conversations written to {args.jsonl}")
        return 0

    calls = asyncio.run(pull_calls(ids[0], args.url))
    if not calls:
        print(f"no model calls for {ids[0]}", file=sys.stderr)
        return 1
    print(f"{len(calls)} model calls; showing call {args.call}\n")
    print(format_output(calls[args.call]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
