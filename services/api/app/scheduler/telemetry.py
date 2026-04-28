"""
Scheduler telemetry — live state visible to the UI.

Every scheduler loop publishes:
  - LoopState (status, last_tick, next_tick, last_intervention, last_result_count, errors)
  - ActivityEvent (tick_start, connector_query, connector_done, evidence_persisted, tick_end, error)

The runner records into a process-global telemetry singleton; the API
routes (`/api/scheduler/state`, `/api/scheduler/activity`) read from it.

Activity uses a bounded ring buffer to keep memory predictable.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Deque, Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class LoopState:
    name: str
    status: str = "idle"        # idle | running | sleeping | error
    last_tick: Optional[datetime] = None
    next_tick: Optional[datetime] = None
    last_intervention: Optional[str] = None
    last_connector: Optional[str] = None
    last_result_count: int = 0
    last_error: Optional[str] = None
    total_ticks: int = 0
    total_evidence_persisted: int = 0

    def as_dict(self) -> dict:
        d = asdict(self)
        for k in ("last_tick", "next_tick"):
            v = d[k]
            d[k] = v.isoformat() if isinstance(v, datetime) else v
        return d


@dataclass
class ActivityEvent:
    ts: datetime
    kind: str                  # tick_start | tick_end | connector | persisted | error | scheduled
    loop: Optional[str] = None
    intervention: Optional[str] = None
    connector: Optional[str] = None
    message: str = ""
    count: Optional[int] = None

    def as_dict(self) -> dict:
        d = asdict(self)
        d["ts"] = self.ts.isoformat()
        return d


class Telemetry:
    """Process-global singleton, thread-safe (used from asyncio + sync code)."""

    _MAX = 500

    def __init__(self) -> None:
        self.loops: dict[str, LoopState] = {}
        self.activity: Deque[ActivityEvent] = deque(maxlen=self._MAX)
        self.queue: list[str] = []
        self._lock = threading.Lock()
        self._started_at = _now()

    def started_at(self) -> datetime:
        return self._started_at

    def ensure_loop(self, name: str) -> LoopState:
        with self._lock:
            ls = self.loops.get(name)
            if ls is None:
                ls = LoopState(name=name)
                self.loops[name] = ls
            return ls

    def update_loop(self, name: str, **kw) -> None:
        with self._lock:
            ls = self.loops.get(name) or LoopState(name=name)
            for k, v in kw.items():
                setattr(ls, k, v)
            self.loops[name] = ls

    def log(self, kind: str, *, loop: str | None = None,
            intervention: str | None = None, connector: str | None = None,
            message: str = "", count: int | None = None) -> None:
        ev = ActivityEvent(ts=_now(), kind=kind, loop=loop,
                            intervention=intervention, connector=connector,
                            message=message, count=count)
        with self._lock:
            self.activity.append(ev)

    def set_queue(self, q: list[str]) -> None:
        with self._lock:
            self.queue = list(q)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "started_at": self._started_at.isoformat(),
                "now": _now().isoformat(),
                "loops": [ls.as_dict() for ls in self.loops.values()],
                "queue": list(self.queue),
                "activity_count": len(self.activity),
            }

    def recent_activity(self, limit: int = 100) -> list[dict]:
        with self._lock:
            items = list(self.activity)[-limit:]
        items.reverse()
        return [a.as_dict() for a in items]


telemetry = Telemetry()
