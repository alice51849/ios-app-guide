#!/usr/bin/env python3
"""Reviewed buyer personas staged for apps that are not yet live.

When an app here goes READY_FOR_SALE, move its entry back into
answer_personas.PERSONAS (the strict live==personas contract requires it).
"""
from typing import Any

PRELAUNCH_PERSONAS: dict[str, list[dict[str, Any]]] = {}
