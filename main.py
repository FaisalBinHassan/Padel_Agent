#!/usr/bin/env python3
"""
Padel Court Availability Notifier
==================================
Polls Hyde Park and Regent's Park for available padel slots on Friday 2026-04-10
at 11:00–12:00 or 12:00–13:00, then sends a push notification.

Usage:
    python main.py                   # poll every 5 minutes until a slot is found
    python main.py --once            # check once and exit
    python main.py --interval 120    # poll every 2 minutes
    python main.py --keep-going      # keep polling even after finding slots
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

from checker import check_all_courts, TARGET_DATE, TARGET_TIMES
from notifier import notify, notify_status

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run(interval_seconds: int, once: bool, keep_going: bool) -> None:
    times_str = " or ".join(f"{t}–{int(t.split(':')[0])+1:02d}:00" for t in sorted(TARGET_TIMES))
    logger.info(f"Checking for padel courts on {TARGET_DATE} at {times_str}")
    logger.info("Locations: Hyde Park + Regent's Park")

    if not once:
        logger.info(f"Polling every {interval_seconds}s  (Ctrl-C to stop)")

    already_notified: set[str] = set()
    check_count = 0

    while True:
        check_count += 1
        now = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[Check #{check_count} at {now}] Scanning courts...")

        try:
            available, statuses = check_all_courts()
        except Exception as exc:
            logger.error(f"Check failed: {exc}")
            available, statuses = [], []

        # Always send a status notification so you can confirm it's running
        run_num = os.getenv("GITHUB_RUN_NUMBER", str(check_count))
        notify_status(run_num, statuses)

        # Only alert about newly opened slots
        new_slots = [s for s in available if str(s) not in already_notified]

        if new_slots:
            notify(new_slots)
            for s in new_slots:
                already_notified.add(str(s))

            # Stop after finding slots (unless --keep-going)
            if not keep_going and not once:
                logger.info("Slots found and notified. Use --keep-going to continue polling.")
                break
        else:
            logger.info("No available slots found.")

        if once:
            break

        logger.info(f"Next check in {interval_seconds}s...")
        time.sleep(interval_seconds)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Padel court availability notifier")
    p.add_argument("--once", action="store_true", help="Check once and exit")
    p.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("CHECK_INTERVAL", "300")),
        metavar="SECONDS",
        help="Seconds between checks (default: 300 = 5 min)",
    )
    p.add_argument(
        "--keep-going",
        action="store_true",
        help="Keep polling even after finding available slots",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.interval, args.once, args.keep_going)
    except KeyboardInterrupt:
        logger.info("Stopped.")
        sys.exit(0)
