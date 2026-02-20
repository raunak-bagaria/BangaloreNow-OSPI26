"""Cross-source event deduplication using geo+time blocking.

Given a list of new event rows (ready for DB upsert) and the current contents
of the events table in Supabase, this module identifies duplicates across
different scraped sources even when URLs differ.

Strategy  — "hybrid geohash+date blocking":
1.  Fetch a lightweight index from the DB:
        SELECT id, url, lat, long, "startDate", name FROM events
2.  Build an in-memory spatial+temporal index using grid cells (~500 m) and
    date strings.  Only events in the *same or adjacent* grid cell on the
    *same calendar date* are compared.
3.  Within each bucket, score pairs on:
        - haversine distance  (<= 500 m)
        - time proximity      (<= 1 h)
        - Jaccard similarity on word tokens (>=30%)
4.  For each duplicate pair, prefer the existing DB row (it's already stored)
    and drop the new row from the upsert list.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Constants / thresholds
# ---------------------------------------------------------------------------

# Grid cell size in degrees.  At Bangalore's latitude (~13 °N):
#   0.005° lat  ≈ 555 m
#   0.005° long ≈ 540 m
_GRID_STEP = 0.005

# Maximum haversine distance (metres) to consider two events co-located.
MAX_DISTANCE_M = 500

# Maximum time difference (seconds) to consider two events concurrent.
MAX_TIME_DIFF_S = 1 * 3600  # 1 hour

# Minimum Jaccard similarity (0-1) on name tokens to consider a name match.
# 0.3 is lenient enough for cross-source name variations
# (e.g. "Live Music at Hard Rock" vs "Hard Rock Cafe - Live Music Night").
MIN_NAME_SIMILARITY = 0.3

# Earth radius in metres (mean).
_R = 6_371_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _grid_key(lat: float, lng: float) -> tuple[int, int]:
    """Return an integer grid cell for the given coordinate."""
    return (int(math.floor(lat / _GRID_STEP)),
            int(math.floor(lng / _GRID_STEP)))


def _neighbor_keys(gk: tuple[int, int]) -> list[tuple[int, int]]:
    """Return *gk* plus its 8 neighbours (handles cell-boundary duplicates)."""
    r, c = gk
    return [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two points."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
    return _R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_iso(ts: str | None) -> datetime | None:
    """Best-effort parse of ISO-8601 timestamps (with or without TZ)."""
    if not ts:
        return None
    # Strip trailing 'Z' or timezone offset for naive comparison.
    clean = ts.replace("Z", "").replace("+00:00", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(clean, fmt)
        except ValueError:
            continue
    return None


def _date_str(ts: str | None) -> str | None:
    """Extract 'YYYY-MM-DD' from an ISO timestamp string."""
    dt = _parse_iso(ts)
    return dt.strftime("%Y-%m-%d") if dt else None


def _time_diff_s(ts1: str | None, ts2: str | None) -> float | None:
    """Absolute difference in seconds between two ISO timestamps."""
    d1, d2 = _parse_iso(ts1), _parse_iso(ts2)
    if d1 is None or d2 is None:
        return None
    return abs((d1 - d2).total_seconds())


# ---- Name similarity ----

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Common filler words that add noise to similarity comparison.
_STOPWORDS = frozenset({
    "a", "an", "the", "at", "in", "on", "of", "for", "and", "to", "with",
    "by", "is", "it", "this", "that", "from", "or", "as",
})


def _name_tokens(name: str) -> set[str]:
    """Lowercase a name, strip punctuation, remove stopwords, return token set."""
    tokens = set(_TOKEN_RE.findall(name.lower()))
    return tokens - _STOPWORDS


def _name_similarity(name1: str, name2: str) -> float:
    """Jaccard similarity between the token sets of two event names.

    Returns a float in [0, 1].  1 = identical token sets, 0 = no overlap.
    """
    t1 = _name_tokens(name1)
    t2 = _name_tokens(name2)
    if not t1 or not t2:
        # If either name is empty / all stopwords, be conservative: treat as
        # matching so we still fall through to geo+time (avoids false negatives
        # when scrapers produce blank names).
        return 1.0
    intersection = t1 & t2
    union = t1 | t2
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

class _EventRef:
    """Lightweight reference to an event (DB row or new row)."""

    __slots__ = ("url", "lat", "lng", "start", "name", "from_db", "idx")

    def __init__(
        self,
        url: str,
        lat: float,
        lng: float,
        start: str | None,
        name: str,
        from_db: bool,
        idx: int,
    ):
        self.url = url
        self.lat = lat
        self.lng = lng
        self.start = start      # ISO string
        self.name = name
        self.from_db = from_db
        self.idx = idx           # position in the source list (new rows only)


def _build_index(refs: list[_EventRef]) -> dict[tuple[tuple[int, int], str | None], list[_EventRef]]:
    """Build a dict mapping (grid_key, date_str) → [EventRef …]."""
    idx: dict[tuple[tuple[int, int], str | None], list[_EventRef]] = defaultdict(list)
    for ref in refs:
        gk = _grid_key(ref.lat, ref.lng)
        ds = _date_str(ref.start)
        idx[(gk, ds)].append(ref)
    return dict(idx)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def deduplicate(
    new_rows: list[dict[str, Any]],
    db_rows: list[dict[str, Any]],
    *,
    max_distance_m: float = MAX_DISTANCE_M,
    max_time_diff_s: float = MAX_TIME_DIFF_S,
    min_name_similarity: float = MIN_NAME_SIMILARITY,
) -> tuple[list[dict[str, Any]], int]:
    """Remove cross-source duplicates from *new_rows* that match *db_rows*.

    Parameters
    ----------
    new_rows:
        Rows ready for upsert (must have ``url``, ``lat``, ``long``,
        ``startDate``, ``name``).
    db_rows:
        Lightweight rows fetched from ``events`` table (same keys).
    max_distance_m:
        Spatial proximity threshold.
    max_time_diff_s:
        Temporal proximity threshold.
    min_name_similarity:
        Minimum Jaccard token-overlap to consider names matching (0-1).

    Returns
    -------
    (kept_rows, duplicates_removed)
        *kept_rows* is a filtered copy of *new_rows* with cross-source
        duplicates removed.  *duplicates_removed* is the count dropped.
    """

    # Build refs for DB rows (they always "win" — already stored).
    db_refs: list[_EventRef] = []
    for i, r in enumerate(db_rows):
        lat = r.get("lat")
        lng = r.get("long")
        if lat is None or lng is None:
            continue
        db_refs.append(_EventRef(
            url=r.get("url", ""),
            lat=float(lat),
            lng=float(lng),
            start=r.get("startDate"),
            name=r.get("name", ""),
            from_db=True,
            idx=i,
        ))

    # Build refs for new rows.
    new_refs: list[_EventRef] = []
    for i, r in enumerate(new_rows):
        lat = r.get("lat")
        lng = r.get("long")
        if lat is None or lng is None:
            continue
        new_refs.append(_EventRef(
            url=r.get("url", ""),
            lat=float(lat),
            lng=float(lng),
            start=r.get("startDate"),
            name=r.get("name", ""),
            from_db=False,
            idx=i,
        ))

    # Build spatial+temporal index from DB rows.
    db_index = _build_index(db_refs)

    # Also index new rows against each other (cross-source dupes within batch).
    # We process new rows in order; earlier row wins.
    new_index: dict[tuple[tuple[int, int], str | None], list[_EventRef]] = defaultdict(list)

    duplicate_indices: set[int] = set()

    for nref in new_refs:
        if nref.idx in duplicate_indices:
            continue

        gk = _grid_key(nref.lat, nref.lng)
        ds = _date_str(nref.start)
        is_dup = False

        # Check against DB rows in same + neighbouring cells.
        for neighbor in _neighbor_keys(gk):
            bucket_key = (neighbor, ds)
            for dref in db_index.get(bucket_key, []):
                # Same URL → already handled by upsert ON CONFLICT; skip.
                if nref.url and dref.url and nref.url == dref.url:
                    continue
                dist = _haversine(nref.lat, nref.lng, dref.lat, dref.lng)
                if dist > max_distance_m:
                    continue
                tdiff = _time_diff_s(nref.start, dref.start)
                if tdiff is not None and tdiff > max_time_diff_s:
                    continue
                sim = _name_similarity(nref.name, dref.name)
                if sim < min_name_similarity:
                    continue
                # Close in space + time + similar name → duplicate.
                is_dup = True
                break
            if is_dup:
                break

        # Check against already-accepted new rows (cross-source within batch).
        if not is_dup:
            for neighbor in _neighbor_keys(gk):
                bucket_key = (neighbor, ds)
                for prev in new_index.get(bucket_key, []):
                    if nref.url and prev.url and nref.url == prev.url:
                        continue
                    dist = _haversine(nref.lat, nref.lng, prev.lat, prev.lng)
                    if dist > max_distance_m:
                        continue
                    tdiff = _time_diff_s(nref.start, prev.start)
                    if tdiff is not None and tdiff > max_time_diff_s:
                        continue
                    sim = _name_similarity(nref.name, prev.name)
                    if sim < min_name_similarity:
                        continue
                    is_dup = True
                    break
                if is_dup:
                    break

        if is_dup:
            duplicate_indices.add(nref.idx)
        else:
            # Accept this row; register it for future within-batch checks.
            new_index[(gk, ds)].append(nref)

    kept = [r for i, r in enumerate(new_rows) if i not in duplicate_indices]
    return kept, len(duplicate_indices)


def fetch_db_index(client: Any) -> list[dict[str, Any]]:
    """Fetch the lightweight dedup index from Supabase.

    Returns a list of dicts with keys: ``url``, ``lat``, ``long``,
    ``startDate``, ``name``.
    """
    resp = (
        client
        .table("events")
        .select("url, lat, long, startDate, name")
        .execute()
    )
    return resp.data or []
