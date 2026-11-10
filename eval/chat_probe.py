"""Talk to the running assistant with fixed messages, and read back what happened.

The scenario suite answers "did this conversation pass". A probe answers "how often does the
assistant do X": it sends fixed member messages over the REST channel, with no simulated user and
no judge, and reads the tracker.

    python -m eval.chat_probe --member m1001 "Am I covered for an ambulance?" "And non-emergency?"

From code:

    from eval.chat_probe import Conversation
    chat = Conversation(member="m1001", hours_profile="always_open")
    replies = chat.send("I want to talk to someone")
    events = chat.events()
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import uuid
from typing import Any

DEFAULT_URL = "http://localhost:5005"
FIRST_MESSAGE = "/session_start"


def _post(url: str, payload: Any, timeout: int = 120) -> Any:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode() or "null")


def _get(url: str, timeout: int = 60) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode())


class Conversation:
    """One conversation with the assistant. The session-start metadata is what a trusted channel
    client sends: `member_id` for a signed-in member, `client_surface`, and the test-only `hours_profile`."""

    def __init__(
        self,
        member: str | None = None,
        surface: str = "web",
        hours_profile: str | None = None,
        url: str = DEFAULT_URL,
        prefix: str = "probe",
    ) -> None:
        self.url = url.rstrip("/")
        self.sender = f"{prefix}-{uuid.uuid4().hex[:8]}"
        metadata: dict[str, Any] = {"client_surface": surface}
        if member:
            metadata["member_id"] = member
        if hours_profile:
            metadata["hours_profile"] = hours_profile
        self.greeting = self._send(FIRST_MESSAGE, metadata)

    def _send(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = {"sender": self.sender, "message": text, "metadata": metadata or {}}
        return _post(f"{self.url}/webhooks/rest/webhook", payload) or []

    def send(self, text: str) -> list[dict[str, Any]]:
        """Send one member message. Returns the replies: each has `text`, and maybe `buttons`."""
        return self._send(text)

    def events(self) -> list[dict[str, Any]]:
        return _get(f"{self.url}/conversations/{self.sender}/tracker?include_events=ALL")["events"]

    def written_memory(self) -> dict[str, Any]:
        """The latest value of every memory key that was written, from the `memory_set` events."""
        values: dict[str, Any] = {}
        for event in self.events():
            if event.get("event") == "memory_set":
                values[event.get("key")] = event.get("value")
        return values

    def tools_called(self) -> list[str]:
        return [e.get("tool_name") for e in self.events() if e.get("event") == "tool_executed"]

    def responses_sent(self) -> list[str]:
        """The names of the authored responses that the assistant sent, in order."""
        return [
            (e.get("metadata") or {}).get("utter_action")
            for e in self.events()
            if e.get("event") == "bot" and (e.get("metadata") or {}).get("utter_action")
        ]


def format_output(replies: list[dict[str, Any]]) -> str:
    lines = []
    for reply in replies:
        if reply.get("text"):
            lines.append(f"  bot: {reply['text']}")
        for button in reply.get("buttons") or []:
            lines.append(f"       [{button.get('title')}] -> {button.get('payload')}")
    return "\n".join(lines) or "  bot: (no text)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("messages", nargs="+", help="member messages, in order")
    parser.add_argument("--member", default=None, help="member id, for example m1001; omit for a visitor")
    parser.add_argument("--surface", default="web", choices=["web", "app"])
    parser.add_argument("--hours", default=None, choices=["always_open", "never_open"])
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()

    chat = Conversation(args.member, args.surface, args.hours, args.url)
    print(f"conversation {chat.sender}")
    print(format_output(chat.greeting))
    for message in args.messages:
        print(f"member: {message}")
        print(format_output(chat.send(message)))
    print(f"tools: {', '.join(chat.tools_called())}")
    print(f"inspector: {args.url}/webhooks/inspector/inspect.html?sender={chat.sender}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
