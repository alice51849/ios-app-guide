#!/usr/bin/env python3
"""Shared configuration for the independent WebSub publishing hubs."""
from __future__ import annotations

import os
import urllib.parse

DEFAULT_WEBSUB_HUBS = (
    "https://pubsubhubbub.appspot.com/",
    "https://pubsubhubbub.superfeedr.com/",
)


def configured_hubs(value=None):
    raw = os.environ.get("WEBSUB_HUBS") if value is None else value
    hubs = (
        DEFAULT_WEBSUB_HUBS
        if raw is None
        else tuple(item.strip() for item in raw.split(",") if item.strip())
    )
    if not hubs:
        raise ValueError("at least one WebSub hub is required")
    if len(hubs) != len(set(hubs)):
        raise ValueError("WebSub hubs must be unique")
    for hub in hubs:
        parsed = urllib.parse.urlsplit(hub)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(f"invalid WebSub hub URL: {hub}")
    return hubs


WEBSUB_HUBS = configured_hubs()
