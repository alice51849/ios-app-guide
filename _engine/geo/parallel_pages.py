#!/usr/bin/env python3
"""Order-preserving process fan-out for whole-tree page generators.

Daily GEO runs several generators that read tens of thousands of pages one by
one. The per-page work is independent, so it can fan out over processes as long
as the caller still consumes results in the original order and performs every
write itself, in that order. That keeps output bytes, statistics and the state
left on disk by a failure identical to a serial loop.

Policy (shared with gen_store_attribution): only Linux (the cloud runner) fans
out by default, via fork, so callers need no ``__main__`` guard. Elsewhere the
platform start method re-imports ``__main__``, so fan-out is opt-in through
``GEO_ATTRIBUTION_WORKERS``. Small inputs always stay in-process.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
import multiprocessing
import os
import sys
from typing import Callable, Iterable, Iterator, TypeVar


WORKERS_ENV = "GEO_ATTRIBUTION_WORKERS"
MIN_ITEMS = 512
CHUNK_ITEMS = 64
# Results for one batch are held by the executor until consumed; bounding the
# batch bounds the memory used by returned page bodies.
BATCH_ITEMS = 1024
# Hosted runners have 4 vCPUs; more processes only add memory pressure.
DEFAULT_MAX_WORKERS = 4

T = TypeVar("T")
R = TypeVar("R")

_FUNCTION: Callable | None = None


def workers() -> int:
    configured = os.environ.get(WORKERS_ENV, "").strip()
    if configured:
        if not configured.isdigit() or int(configured) < 1:
            raise ValueError(f"{WORKERS_ENV} must be a positive integer")
        return int(configured)
    if not sys.platform.startswith("linux"):
        return 1
    return max(1, min(DEFAULT_MAX_WORKERS, os.cpu_count() or 1))


def _context():
    if sys.platform.startswith("linux"):
        return multiprocessing.get_context("fork")
    return multiprocessing.get_context()


def _init(function: Callable) -> None:
    global _FUNCTION
    _FUNCTION = function


def _call(item):
    # Exceptions are not shipped back: they may not survive pickling, and the
    # parent replays the item in-process to raise the genuine exception.
    try:
        return True, _FUNCTION(item)
    except Exception:
        return False, None


def ordered_map(function: Callable[[T], R], items: Iterable[T]) -> Iterator[R]:
    """Yield ``function(item)`` for every item, in input order.

    ``function`` must be side-effect free (read files, compute, return); the
    caller applies any writes while consuming the iterator. When a worker
    fails, that item is recomputed in-process, so the caller sees the same
    exception at the same position as a serial loop. A broken pool degrades
    to in-process evaluation for the remaining items.
    """
    items = list(items)
    count = workers()
    if count <= 1 or len(items) < MIN_ITEMS:
        for item in items:
            yield function(item)
        return
    pool = ProcessPoolExecutor(
        max_workers=count,
        mp_context=_context(),
        initializer=_init,
        initargs=(function,),
    )
    position = 0
    try:
        for start in range(0, len(items), BATCH_ITEMS):
            batch = items[start:start + BATCH_ITEMS]
            try:
                results = pool.map(_call, batch, chunksize=CHUNK_ITEMS)
                for item, (ok, value) in zip(batch, results):
                    yield value if ok else function(item)
                    position += 1
            except BrokenProcessPool:
                break
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
    for item in items[position:]:
        yield function(item)
