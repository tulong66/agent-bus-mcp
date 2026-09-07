#!/usr/bin/env python3
"""
Antigravity Universal Doorbell Watcher Daemon
Watches for doorbell bell file updates and exits 0 to trigger platform reactive wakeup.
"""
import sys
import time
from pathlib import Path

agent_id = sys.argv[1] if len(sys.argv) > 1 else "antigravity-lead"
timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 600.0

bell_file = Path.home() / ".agent-bus" / "doorbells" / f"{agent_id}.bell"
inbox_file = Path.home() / ".agent-bus" / "inbox" / f"{agent_id}.msg"
legacy_sc = Path.home() / ".superconductor" / "inbox" / "antigravity.msg"

watch_targets = [bell_file, inbox_file, legacy_sc]
baseline = {}
for p in watch_targets:
    try:
        if p.exists():
            baseline[str(p)] = p.stat().st_mtime
    except OSError:
        pass

start_t = time.time()
while time.time() - start_t < timeout:
    for p in watch_targets:
        try:
            if p.exists():
                st = p.stat()
                if st.st_size > 0:
                    old_m = baseline.get(str(p), 0.0)
                    if st.st_mtime > old_m or str(p) not in baseline:
                        sys.exit(0)
        except OSError:
            pass
    time.sleep(0.15)

sys.exit(1)
