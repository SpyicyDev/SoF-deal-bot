"""DST gate: only proceed if it's currently 7am US/Eastern.

GitHub Actions cron is UTC-only. We register two crons (11:00 UTC and
12:00 UTC); only one will match 7am ET on any given day, depending on
whether DST is in effect. This script is run from the gate job and
exits 0 when current ET hour == 7, exits 1 otherwise so the dependent
digest job is skipped.

Allows up to ~15 minutes of cron drift (i.e. 7:00–7:15 ET still passes).
Manual dispatch bypasses this script entirely (handled in the workflow).
"""

from __future__ import annotations

import datetime as dt
import sys
from zoneinfo import ZoneInfo


TARGET_HOUR = 7
DRIFT_TOLERANCE_MINUTES = 15


def main() -> int:
    now_et = dt.datetime.now(ZoneInfo("America/New_York"))
    if now_et.hour == TARGET_HOUR:
        print(f"DST gate: pass — {now_et.isoformat()} (hour {now_et.hour})")
        return 0
    # Allow brief overflow into the next hour from cron drift, but only just past.
    if now_et.hour == TARGET_HOUR + 1 and now_et.minute < DRIFT_TOLERANCE_MINUTES:
        print(
            f"DST gate: pass (drift) — {now_et.isoformat()} "
            f"(hour {now_et.hour}, minute {now_et.minute})"
        )
        return 0
    print(
        f"DST gate: skip — {now_et.isoformat()} (hour {now_et.hour}, expected {TARGET_HOUR})",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
