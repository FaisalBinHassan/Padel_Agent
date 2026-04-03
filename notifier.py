"""
Notification methods for padel court availability alerts.

Supported channels:
  - ntfy.sh  — free push notifications to phone/desktop (no account needed)
  - Desktop  — system notification via notify-send (Linux) or osascript (macOS)
  - Console  — always prints to stdout
"""

import logging
import os
import platform
import subprocess
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from checker import AvailableSlot

logger = logging.getLogger(__name__)

# ── ntfy.sh config ─────────────────────────────────────────────────────────────
# Subscribe to your topic at https://ntfy.sh/<TOPIC> or in the ntfy mobile app.
# Set NTFY_TOPIC in .env (e.g. "padel-courts-abc123").  If unset, ntfy is skipped.
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh")


def notify(slots: "list[AvailableSlot]") -> None:
    """Send notifications for all available slots via every configured channel."""
    if not slots:
        return

    message = _build_message(slots)
    title = f"🎾 Padel available! ({len(slots)} slot{'s' if len(slots) > 1 else ''})"

    _console(title, message, slots)
    _ntfy(title, message, slots)
    _desktop(title, message)


def _build_message(slots: "list[AvailableSlot]") -> str:
    lines = []
    for s in slots:
        end_hour = int(s.time.split(":")[0]) + 1
        end_time = f"{end_hour:02d}:00"
        court_info = f" ({s.court})" if s.court else ""
        lines.append(f"• {s.location}{court_info}: {s.time}–{end_time}")
    lines.append(f"\nBook now: {slots[0].url}")
    return "\n".join(lines)


def _console(title: str, message: str, slots: "list[AvailableSlot]") -> None:
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"  {title}")
    print(separator)
    print(message)
    print(separator + "\n")


def _ntfy(title: str, message: str, slots: "list[AvailableSlot]") -> None:
    if not NTFY_TOPIC:
        return

    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
    try:
        resp = requests.post(
            url,
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": "high",
                "Tags": "tennis,calendar",
                "Click": slots[0].url,
            },
            timeout=10,
        )
        if resp.ok:
            logger.info(f"ntfy notification sent to {url}")
        else:
            logger.warning(f"ntfy returned {resp.status_code}: {resp.text}")
    except Exception as exc:
        logger.warning(f"Failed to send ntfy notification: {exc}")


def _desktop(title: str, message: str) -> None:
    system = platform.system()
    try:
        if system == "Linux":
            subprocess.run(
                ["notify-send", "-u", "critical", title, message],
                check=False,
                timeout=5,
            )
        elif system == "Darwin":
            script = (
                f'display notification "{message}" '
                f'with title "{title}" sound name "Glass"'
            )
            subprocess.run(["osascript", "-e", script], check=False, timeout=5)
    except FileNotFoundError:
        pass  # notify-send / osascript not available — silently skip
    except Exception as exc:
        logger.debug(f"Desktop notification failed: {exc}")
