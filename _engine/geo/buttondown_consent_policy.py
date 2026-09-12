#!/usr/bin/env python3
"""Read-only account-bound Buttondown policy snapshots; defaults are not evidence."""
from __future__ import annotations

import argparse
import ipaddress
import os
from pathlib import Path
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

import owned_email_contract as c
import owned_email_readback as readback
import owned_email_sender as legacy

SCHEMA = "lumi.buttondown-consent-policy/v1"
CONTRACT = c.HERE / "buttondown_consent_contract.json"
CHECKS = (
    "account_binding", "newsletter_binding", "double_opt_in", "scoped_confirmation",
    "unsubscribe_configuration", "tracking_disabled", "sender_identity",
)
ADDON_FILES = (
    "buttondown_consent_contract.json", "buttondown_consent_policy.py",
    "buttondown_consent_evaluator.py",
)
API = readback.API
REQUIRED_SENDER_FIELDS = (
    "email_address", "email_domain", "from_name", "reply_to_address", "sending_domain_status",
)


def settings():
    value = c.parse_json(CONTRACT.read_bytes())
    if (
        value.get("schema") != "lumi.buttondown-consent-contract/v1"
        or value.get("newsletter_username") != c.NEWSLETTER
        or value.get("public_form_url") != c.ENDPOINT
        or value.get("public_profile_url") != "https://buttondown.com/hourstag"
        or value.get("public_archive_url") != "https://buttondown.com/hourstag/archive/"
        or value.get("reply_to_address") != "hourstag.app@gmail.com"
        or type(value.get("ttl_seconds")) is not int or not 0 < value["ttl_seconds"] <= 300
        or type(value.get("domain_ttl_seconds")) is not int or not 0 < value["domain_ttl_seconds"] <= 86400
        or value.get("required_settings") != list(CHECKS)
        or value.get("confirmation_tokens") != [
            "confirmation_url", "subscriber.metadata.owned_app_id",
            "subscriber.metadata.owned_locale", "subscriber.metadata.owned_campaign",
        ]
        or value.get("sender_enabled") is not False
    ):
        raise c.ContractError("invalid or permissive consent policy contract")
    return value


def source_digest():
    return c.digest({
        "baseline": c.source_files(),
        "consent": {name: c.digest((c.HERE / name).read_bytes()) for name in ADDON_FILES},
    })


def local_config_digest():
    return c.digest({name: c.digest((c.HERE / name).read_bytes()) for name in (
        "buttondown_consent_contract.json", "tool_email_capture.json", "owned_email_copy.json",
        "owned_email_rollout.json",
    )})


def allowed_url(url):
    if not isinstance(url, str) or any(character.isspace() for character in url):
        raise c.ContractError("invalid GET URL")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment or parsed.port:
        raise c.ContractError("only exact credential-free HTTPS URLs are allowed")
    public = {settings()[key] for key in ("public_form_url", "public_profile_url", "public_archive_url")}
    if url in public:
        return False
    if parsed.netloc == "buttondown.com" and not parsed.query and readback.ARCHIVE.fullmatch(parsed.path):
        return False
    if parsed.netloc != "api.buttondown.com":
        raise c.ContractError("unapproved provider host")
    if parsed.path in {"/v1/accounts/me", "/v1/newsletters"} and not parsed.query:
        return True
    if parsed.path == "/v1/subscribers" and (
        not parsed.query or re.fullmatch(r"page=[1-9][0-9]{0,3}", parsed.query)
    ):
        return True
    parts = parsed.path.split("/")
    if (
        len(parts) in (4, 5) and parts[1] == "v1"
        and parts[2] in {"newsletters", "subscribers", "emails"}
        and readback.ID.fullmatch(parts[3]) and not parsed.query
        and (len(parts) == 4 or parts[2] == "newsletters" and parts[4] == "sending-domain")
    ):
        return True
    raise c.ContractError("only safe GET routes are allowed; force re-verification is forbidden")


class ReadOnlyClient:
    def __init__(self, api_key=None):
        if api_key is not None and (
            not isinstance(api_key, str) or not api_key or any(character.isspace() for character in api_key)
        ):
            raise c.ContractError("invalid API credential")
        self._key = api_key

    def request(self, method, url):
        if method != "GET":
            raise c.ContractError("subscription, sending and settings mutations are forbidden")
        api = allowed_url(url)
        host = urllib.parse.urlsplit(url).hostname
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise c.ContractError("non-public provider address")
        headers = {"User-Agent": "OwnedEmail-Consent-ReadOnly/1", "Cache-Control": "no-cache"}
        if api and self._key:
            headers["Authorization"] = f"Token {self._key}"
        request = urllib.request.Request(url, method="GET", headers=headers)
        try:
            response = urllib.request.build_opener(readback._NoRedirect()).open(request, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read(readback.MAX_BODY + 1)
            if len(body) > readback.MAX_BODY:
                raise c.ContractError("provider readback exceeds size limit")
            return {
                "method": "GET", "url": url, "final_url": response.geturl(),
                "http_status": response.code, "authenticated": bool(api and self._key),
                "location": response.headers.get("Location"), "body": body,
                "observed_at": c.utcnow().isoformat(),
            }

    def get(self, url):
        return self.request("GET", url)


def observe(url, get, now, *, require_authenticated=False):
    allowed_url(url)
    result = get(url)
    if (
        not isinstance(result, dict) or result.get("method") != "GET"
        or result.get("url") != url or result.get("final_url") != url
        or type(result.get("http_status")) is not int
        or not isinstance(result.get("body"), bytes) or len(result["body"]) > readback.MAX_BODY
        or type(result.get("authenticated")) is not bool
    ):
        raise c.ContractError("invalid exact provider GET evidence")
    c.fresh(result.get("observed_at"), now() if callable(now) else now, 300)
    evidence = {
        key: result[key] for key in ("method", "url", "final_url", "http_status", "authenticated", "observed_at")
    }
    evidence["body_sha256"] = c.digest(result["body"])
    evidence["location"] = result.get("location")
    payload = None
    if result["http_status"] == 200 and (not require_authenticated or result["authenticated"]):
        try:
            payload = c.parse_json(result["body"])
        except c.ContractError:
            pass
    return payload, evidence, result["body"]


def template_summary(value):
    if not isinstance(value, str):
        return {"present": False, "sha256": None, "visible_tokens": [], "link_tokens": [], "unsafe_logic": False}
    dom = readback.Body(value)
    tokens = lambda text: sorted(set(re.findall(r"{{\s*([A-Za-z0-9_.]+)\s*}}", text)))
    links = [*dom.links, *re.findall(r"\]\((.*?)\)", value, re.S)]
    return {
        "present": bool(value.strip()), "sha256": c.digest(value.encode()),
        "visible_tokens": tokens(dom.visible()), "link_tokens": tokens(" ".join(links)),
        "unsafe_logic": "{%" in value or "<script" in value.lower(),
    }


def project_account(value):
    if not isinstance(value, dict) or not isinstance(value.get("username"), str) or not value["username"].strip():
        return None
    try:
        fingerprint = legacy.email_hash(value.get("email_address"))
    except c.ContractError:
        return None
    return {"username": value["username"], "email_sha256": fingerprint}


def project_newsletter(value):
    if (
        not isinstance(value, dict) or not isinstance(value.get("id"), str)
        or not readback.ID.fullmatch(value["id"]) or value.get("username") != c.NEWSLETTER
    ):
        return None
    sender = {"fields_present": all(key in value for key in REQUIRED_SENDER_FIELDS)}
    try:
        sender.update(
            email_sha256=legacy.email_hash(value.get("email_address")),
            email_domain=value["email_address"].rsplit("@", 1)[1].lower(),
            configured_domain=value.get("email_domain"), status=value.get("sending_domain_status"),
            from_name_present=isinstance(value.get("from_name"), str) and bool(value["from_name"].strip()),
            reply_to_matches=value.get("reply_to_address") == settings()["reply_to_address"],
        )
    except c.ContractError:
        sender["fields_present"] = False
    features = value.get("enabled_features")
    return {
        "id": value["id"], "username": value["username"],
        "double_opt_in": value.get("should_require_double_optin") if type(value.get("should_require_double_optin")) is bool else None,
        "double_opt_in_exposed": "should_require_double_optin" in value,
        "confirmation": template_summary(value.get("custom_subscription_confirmation_email_text")),
        "confirmation_template_default": "custom_subscription_confirmation_email_template" in value
        and value["custom_subscription_confirmation_email_template"] in (None, ""),
        "footer": template_summary(value.get("footer")),
        "email_template_default": "custom_email_template" in value and value["custom_email_template"] in (None, ""),
        "features": features if isinstance(features, list) and all(isinstance(item, str) for item in features) else None,
        "unknown_tracking_fields": sorted(key for key in value if "track" in key.lower()),
        "sender": sender, "test_mode": value.get("test_mode") if type(value.get("test_mode")) is bool else None,
    }


def project_domain(value):
    if not isinstance(value, dict):
        return None
    requirements = value.get("requirements")
    return {
        "domain": value.get("domain"), "status": value.get("status"),
        "checked_date": value.get("checked_date"), "is_checking": value.get("is_checking"),
        "requirements_verified": isinstance(requirements, list) and bool(requirements)
        and all(isinstance(item, dict) and item.get("is_valid") is True for item in requirements),
        "warnings_empty": value.get("warnings") == [],
    }


def configuration_digest(value):
    # DNS observation freshness is evidence, not a change to the user's consent scope.
    domain = value.get("domain")
    domain = {key: item for key, item in domain.items() if key != "checked_date"} if domain else None
    return c.digest({"newsletter": value.get("newsletter"), "domain": domain})


def decisions(account, newsletter, domain, now):
    checks = {name: "UNKNOWN" for name in CHECKS}
    if account:
        checks["account_binding"] = "VERIFIED"
    if not newsletter:
        return checks
    checks["newsletter_binding"] = "VERIFIED" if account else "UNKNOWN"
    if newsletter["double_opt_in"] is True:
        checks["double_opt_in"] = "VERIFIED"
    elif newsletter["double_opt_in"] is False:
        checks["double_opt_in"] = "BLOCKED"
    confirmation = newsletter["confirmation"]
    required = set(settings()["confirmation_tokens"]) - {"confirmation_url"}
    if (
        confirmation["present"] and not confirmation["unsafe_logic"]
        and newsletter["confirmation_template_default"]
        and required <= set(confirmation["visible_tokens"])
        and "confirmation_url" in confirmation["link_tokens"]
    ):
        checks["scoped_confirmation"] = "VERIFIED"
    footer = newsletter["footer"]
    if (
        footer["present"] and not footer["unsafe_logic"] and newsletter["email_template_default"]
        and "unsubscribe_url" in footer["link_tokens"]
    ):
        checks["unsubscribe_configuration"] = "VERIFIED"
    if newsletter["features"] is not None and not newsletter["unknown_tracking_fields"]:
        checks["tracking_disabled"] = "VERIFIED" if "tracking" not in newsletter["features"] else "UNKNOWN"
    sender = newsletter["sender"]
    if (
        sender["fields_present"] and sender.get("from_name_present") is True
        and sender.get("reply_to_matches") is True and newsletter["test_mode"] is False
        and domain and sender.get("status") == "valid" and domain.get("status") == "valid"
        and sender.get("email_domain") == sender.get("configured_domain") == domain.get("domain")
        and domain.get("requirements_verified") is True and domain.get("warnings_empty") is True
        and domain.get("is_checking") is False
    ):
        try:
            c.fresh(domain.get("checked_date"), now, settings()["domain_ttl_seconds"])
            checks["sender_identity"] = "VERIFIED"
        except c.ContractError:
            pass
    return checks


def collect(get, *, now=None):
    clock = c.utcnow if now is None else lambda: now
    config = settings()
    observations, public = {}, {}
    for name in ("public_form_url", "public_profile_url", "public_archive_url"):
        _, evidence, _ = observe(config[name], get, clock)
        public[name] = evidence
    raw_account, observations["account"], _ = observe(
        f"{API}/accounts/me", get, clock, require_authenticated=True,
    )
    account, newsletter, domain = project_account(raw_account), None, None
    if account:
        listing, observations["newsletters"], _ = observe(f"{API}/newsletters", get, clock, require_authenticated=True)
        entries = listing.get("results") if isinstance(listing, dict) else None
        selected = [row for row in entries or [] if isinstance(row, dict) and row.get("username") == config["newsletter_username"]]
        if len(selected) == 1 and isinstance(selected[0].get("id"), str) and readback.ID.fullmatch(selected[0]["id"]):
            identity = selected[0]["id"]
            value, observations["newsletter"], _ = observe(
                f"{API}/newsletters/{identity}", get, clock, require_authenticated=True,
            )
            newsletter = project_newsletter(value)
            if newsletter and newsletter["id"] == identity:
                value, observations["domain"], _ = observe(
                    f"{API}/newsletters/{identity}/sending-domain", get, clock, require_authenticated=True,
                )
                domain = project_domain(value)
            else:
                newsletter = None
    current = clock()
    binding = {
        "account": account, "newsletter_id": newsletter["id"] if newsletter else None,
        "newsletter_username": config["newsletter_username"],
        "public_form_url": config["public_form_url"],
    }
    configuration = {"newsletter": newsletter, "domain": domain}
    checks = decisions(account, newsletter, domain, current)
    result = {
        "schema": SCHEMA, "observed_at": current.isoformat(), "ttl_seconds": config["ttl_seconds"],
        "source_digest": source_digest(), "local_config_digest": local_config_digest(),
        "binding": binding, "binding_digest": c.digest(binding),
        "configuration": configuration, "configuration_digest": configuration_digest(configuration),
        "public_gets": public, "api_gets": observations, "checks": checks,
        "status": "VERIFIED_CONFIGURATION" if all(value == "VERIFIED" for value in checks.values()) else "BLOCKED",
        "blockers": [name for name, value in checks.items() if value != "VERIFIED"],
        "subscriber_count": "UNKNOWN", "verified_audience_count": 0, "native_count": 0,
        "unsubscribe_runtime": "UNKNOWN_NOT_EXERCISED", "send_allowed": False,
        "official_sources": config["official_sources"],
    }
    result["digest"] = c.digest(result)
    return result


def validate(snapshot, *, now=None, require_verified=True):
    now = now or c.utcnow()
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        raise c.ContractError("consent policy snapshot is missing")
    if snapshot.get("digest") != c.digest({k: v for k, v in snapshot.items() if k != "digest"}):
        raise c.ContractError("consent policy snapshot digest mismatch")
    if (
        snapshot.get("source_digest") != source_digest()
        or snapshot.get("local_config_digest") != local_config_digest()
        or type(snapshot.get("ttl_seconds")) is not int
        or not 0 < snapshot["ttl_seconds"] <= settings()["ttl_seconds"]
        or snapshot.get("send_allowed") is not False
        or snapshot.get("subscriber_count") != "UNKNOWN" or snapshot.get("native_count") != 0
    ):
        raise c.ContractError("policy source/configuration/count boundary changed")
    c.fresh(snapshot.get("observed_at"), now, snapshot["ttl_seconds"])
    binding, configuration = snapshot.get("binding"), snapshot.get("configuration")
    if (
        not isinstance(binding, dict) or not isinstance(configuration, dict)
        or binding.get("public_form_url") != c.ENDPOINT
        or binding.get("newsletter_username") != c.NEWSLETTER
        or c.digest(binding) != snapshot.get("binding_digest")
        or configuration_digest(configuration) != snapshot.get("configuration_digest")
    ):
        raise c.ContractError("account/public-form/config binding mismatch")
    newsletter = configuration.get("newsletter")
    if newsletter and (
        newsletter.get("id") != binding.get("newsletter_id")
        or newsletter.get("username") != binding["newsletter_username"]
    ):
        raise c.ContractError("newsletter identity differs from the account binding")
    checks = decisions(binding.get("account"), configuration.get("newsletter"), configuration.get("domain"), now)
    if snapshot.get("checks") != checks:
        raise c.ContractError("policy booleans cannot override GET-derived settings")
    expected_status = "VERIFIED_CONFIGURATION" if all(value == "VERIFIED" for value in checks.values()) else "BLOCKED"
    if snapshot.get("status") != expected_status or snapshot.get("blockers") != [
        name for name, value in checks.items() if value != "VERIFIED"
    ]:
        raise c.ContractError("policy readiness claims do not match provider evidence")
    for name, url in (
        ("public_form_url", c.ENDPOINT), ("public_profile_url", "https://buttondown.com/hourstag"),
        ("public_archive_url", "https://buttondown.com/hourstag/archive/"),
    ):
        entry = snapshot.get("public_gets", {}).get(name, {})
        if (
            entry.get("method") != "GET" or entry.get("url") != url or entry.get("final_url") != url
            or type(entry.get("http_status")) is not int
            or not isinstance(entry.get("body_sha256"), str) or not c.HEX.fullmatch(entry["body_sha256"])
        ):
            raise c.ContractError("public form health is not exact GET evidence")
        c.fresh(entry.get("observed_at"), now, snapshot["ttl_seconds"])
    observations = snapshot.get("api_gets")
    if not isinstance(observations, dict) or "account" not in observations:
        raise c.ContractError("missing named account GET evidence")
    identity = binding.get("newsletter_id")
    urls = {
        "account": f"{API}/accounts/me", "newsletters": f"{API}/newsletters",
        "newsletter": f"{API}/newsletters/{identity}", "domain": f"{API}/newsletters/{identity}/sending-domain",
    }
    for name, entry in observations.items():
        if (
            name not in urls or entry.get("method") != "GET" or entry.get("url") != urls[name]
            or entry.get("final_url") != entry.get("url") or type(entry.get("http_status")) is not int
            or type(entry.get("authenticated")) is not bool
            or not isinstance(entry.get("body_sha256"), str) or not c.HEX.fullmatch(entry["body_sha256"])
        ):
            raise c.ContractError("invalid account GET evidence")
        allowed_url(entry.get("url"))
        c.fresh(entry.get("observed_at"), now, snapshot["ttl_seconds"])
    if require_verified and (
        snapshot.get("status") != "VERIFIED_CONFIGURATION"
        or any(value != "VERIFIED" for value in checks.values())
        or not binding.get("account") or not binding.get("newsletter_id")
        or any(snapshot["api_gets"].get(name, {}).get("authenticated") is not True
               or snapshot["api_gets"][name].get("http_status") != 200
               for name in ("account", "newsletters", "newsletter", "domain"))
    ):
        raise c.ContractError("account DOI/confirmation/unsubscribe/privacy/sender configuration is UNKNOWN/BLOCKED")
    return snapshot


def refresh_match(snapshot, get, *, now=None, require_verified=True):
    validate(snapshot, now=now, require_verified=require_verified)
    fresh = collect(get, now=now)
    validate(fresh, now=now, require_verified=require_verified)
    if (
        fresh["binding_digest"] != snapshot["binding_digest"]
        or fresh["configuration_digest"] != snapshot["configuration_digest"]
    ):
        raise c.ContractError("account or provider configuration changed")
    return fresh


def write_private(path, value):
    path = Path(path)
    if path.is_symlink():
        raise c.ContractError("snapshot output cannot be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(c.json_bytes(value) + b"\n")
    path.chmod(0o600)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args(argv)
    key = os.environ.get("BUTTONDOWN_API_KEY") or os.environ.get("BUTTONDOWN_API_TOKEN")
    result = collect(ReadOnlyClient(key).get)
    write_private(args.snapshot, result)
    print(c.json_bytes({
        "status": result["status"], "checks": result["checks"],
        "subscriber_count": "UNKNOWN", "verified_audience_count": 0, "native_count": 0,
        "api_statuses": {key: item["http_status"] for key, item in result["api_gets"].items()},
        "public_statuses": {key: item["http_status"] for key, item in result["public_gets"].items()},
        "snapshot_digest": result["digest"], "send_allowed": False,
    }).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
