#!/usr/bin/env python3
"""Shared rssCloud discovery and publisher endpoints."""

RSSCLOUD_DOMAIN = "rpc.rsscloud.io"
RSSCLOUD_PORT = "80"
RSSCLOUD_NOTIFY_PATH = "/pleaseNotify"
RSSCLOUD_PROTOCOL = "http-post"
RSSCLOUD_ORIGIN = f"https://{RSSCLOUD_DOMAIN}"
RSSCLOUD_NOTIFY_URL = f"{RSSCLOUD_ORIGIN}{RSSCLOUD_NOTIFY_PATH}"
RSSCLOUD_WEBSUB_HUB = f"{RSSCLOUD_ORIGIN}/websub"
RSSCLOUD_PING_URL = f"{RSSCLOUD_ORIGIN}/ping"
RSSCLOUD_SOURCE_NAMESPACE = "https://source.scripting.com/"
