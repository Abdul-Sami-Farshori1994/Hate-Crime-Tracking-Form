"""Batch analytics: few DB round-trips instead of per-question queries."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from answer_normalize import options_list
from models import Question, QuestionType, Response, ResponseSession
from schemas import AnalyticsBar
from soft_delete import active_response_session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def fetch_answer_rows(db: AsyncSession) -> list[tuple[int, str, object]]:
    """All answers for non-deleted sessions: (question_id, answer_value, submitted_at)."""
    result = await db.execute(
        select(Response.question_id, Response.answer_value, Response.submitted_at)
        .join(ResponseSession, Response.session_id == ResponseSession.session_id)
        .where(active_response_session()),
    )
    return [(int(qid), str(val), submitted_at) for qid, val, submitted_at in result.all()]


async def fetch_total_sessions(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(ResponseSession).where(active_response_session()),
    )
    return int(result.scalar_one() or 0)


def _ordered_breakdown(counter: Counter[str], options: list[str] | None) -> list[AnalyticsBar]:
    if options:
        bars = [AnalyticsBar(label=opt, count=int(counter.get(opt, 0))) for opt in options]
        extras = sorted(
            (label for label in counter if label not in options),
            key=lambda label: (-counter[label], label),
        )
        bars.extend(AnalyticsBar(label=label, count=int(counter[label])) for label in extras)
        return bars
    return [
        AnalyticsBar(label=label, count=int(counter[label]))
        for label in sorted(counter.keys(), key=lambda label: (-counter[label], label))
    ]


def _choice_counter(rows: list[str], question_type: QuestionType) -> Counter[str]:
    counter: Counter[str] = Counter()
    if question_type == QuestionType.checkbox:
        for raw in rows:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    for item in parsed:
                        counter[str(item)] += 1
                    continue
            except json.JSONDecodeError:
                pass
            if raw.strip():
                counter[raw.strip()] += 1
    else:
        for raw in rows:
            label = raw.strip()
            if label:
                counter[label] += 1
    return counter


def _latest_samples(
    rows_with_time: list[tuple[str, object]],
    *,
    limit: int = 8,
) -> list[str]:
    ordered = sorted(rows_with_time, key=lambda pair: pair[1], reverse=True)
    samples: list[str] = []
    for raw, _ in ordered:
        text = str(raw).strip()
        if text and text not in samples:
            samples.append(text)
        if len(samples) >= limit:
            break
    return samples


def build_question_analytics(
    questions: list[Question],
    answer_rows: list[tuple[int, str, object]],
) -> dict[int, tuple[list[AnalyticsBar], int, list[str]]]:
    """
    Per question_id: (breakdown bars, total count, latest text samples).
    """
    by_qid_values: dict[int, list[str]] = defaultdict(list)
    by_qid_timed: dict[int, list[tuple[str, object]]] = defaultdict(list)
    for qid, val, submitted_at in answer_rows:
        by_qid_values[qid].append(val)
        by_qid_timed[qid].append((val, submitted_at))

    out: dict[int, tuple[list[AnalyticsBar], int, list[str]]] = {}
    for q in questions:
        rows = by_qid_values.get(q.id, [])
        total = len(rows)
        qt = q.question_type
        if qt in (QuestionType.radio, QuestionType.select, QuestionType.checkbox, QuestionType.rating):
            counter = _choice_counter(rows, qt)
            breakdown = _ordered_breakdown(counter, options_list(q))
            if qt == QuestionType.rating and not breakdown:
                breakdown = [AnalyticsBar(label=str(n), count=0) for n in range(1, 6)]
            out[q.id] = (breakdown, total, [])
        else:
            latest = _latest_samples(by_qid_timed.get(q.id, []))
            out[q.id] = ([], total, latest)
    return out
