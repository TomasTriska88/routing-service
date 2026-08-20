#!/usr/bin/env python3
"""Read-only Zoho Mail bridge for Markvarec/Lineum.

Credentials stay in ~/.config/zoho-mail/credentials.json (0600).
No token or client secret is ever printed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

CREDENTIALS = os.path.expanduser("~/.config/zoho-mail/credentials.json")
DEFAULT_MAX_CONTENT = 12000


class BridgeError(RuntimeError):
    pass


def load_credentials() -> dict[str, Any]:
    with open(CREDENTIALS, encoding="utf-8") as f:
        data = json.load(f)
    needed = ("client_id", "client_secret", "refresh_token", "target_email", "accounts_base", "mail_base")
    missing = [k for k in needed if not data.get(k)]
    if missing:
        raise BridgeError("credentials_missing:" + ",".join(missing))
    return data


def access_token(c: dict[str, Any]) -> str:
    payload = urllib.parse.urlencode(
        {
            "refresh_token": c["refresh_token"],
            "client_id": c["client_id"],
            "client_secret": c["client_secret"],
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request(c["accounts_base"] + "/oauth/v2/token", data=payload)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        raise BridgeError(f"token_http_{e.code}") from None
    token = body.get("access_token")
    if not token:
        raise BridgeError("token_refresh_failed:" + str(body.get("error") or "unknown"))
    return str(token)


def api_get(c: dict[str, Any], token: str, path: str) -> dict[str, Any]:
    req = urllib.request.Request(
        c["mail_base"] + path,
        headers={"Authorization": "Zoho-oauthtoken " + token},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        code = f"http_{e.code}"
        try:
            err = json.loads(e.read().decode("utf-8", "replace"))
            if isinstance(err, dict):
                status = err.get("status")
                if isinstance(status, dict):
                    code = str(status.get("description") or status.get("code") or code)
        except Exception:
            pass
        raise BridgeError("api_" + code[:120]) from None
    if not isinstance(body, dict):
        raise BridgeError("api_non_object")
    return body


def find_context(c: dict[str, Any], token: str) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    accounts = api_get(c, token, "/api/accounts").get("data")
    if not isinstance(accounts, list):
        raise BridgeError("accounts_invalid")
    target = c["target_email"].lower()
    account = next(
        (x for x in accounts if isinstance(x, dict) and target in json.dumps(x, ensure_ascii=False).lower()),
        None,
    )
    if not account:
        raise BridgeError("target_account_not_found")
    account_id = str(account.get("accountId") or account.get("accountID") or "")
    if not account_id:
        raise BridgeError("account_id_missing")
    folders = api_get(c, token, f"/api/accounts/{urllib.parse.quote(account_id, safe='')}/folders").get("data")
    if not isinstance(folders, list):
        raise BridgeError("folders_invalid")
    inbox = next(
        (
            x
            for x in folders
            if isinstance(x, dict)
            and str(x.get("folderName") or x.get("folder_name") or "").casefold() == "inbox"
        ),
        None,
    )
    if not inbox:
        raise BridgeError("inbox_not_found")
    return account_id, folders, inbox


def folder_id(folder: dict[str, Any]) -> str:
    value = folder.get("folderId") or folder.get("folderID")
    if not value:
        raise BridgeError("folder_id_missing")
    return str(value)


def normalize_message(item: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "messageId",
        "folderId",
        "subject",
        "fromAddress",
        "sender",
        "sentDateInGMT",
        "receivedTime",
        "summary",
        "status2",
        "priority",
        "hasAttachment",
    )
    return {k: item.get(k) for k in keep if k in item}


def cmd_health(c: dict[str, Any], token: str) -> None:
    account_id, folders, inbox = find_context(c, token)
    fid = folder_id(inbox)
    path = (
        f"/api/accounts/{urllib.parse.quote(account_id, safe='')}/messages/view?"
        + urllib.parse.urlencode({"folderId": fid, "limit": 1})
    )
    data = api_get(c, token, path).get("data")
    if not isinstance(data, list):
        raise BridgeError("message_list_invalid")
    print(
        json.dumps(
            {
                "ok": True,
                "target_email": c["target_email"],
                "folder_count": len(folders),
                "inbox": True,
                "message_list": True,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


def cmd_list(c: dict[str, Any], token: str, limit: int, status: str) -> None:
    account_id, _, inbox = find_context(c, token)
    fid = folder_id(inbox)
    params: dict[str, Any] = {"folderId": fid, "limit": max(1, min(limit, 100))}
    if status != "all":
        params["status"] = status
    path = (
        f"/api/accounts/{urllib.parse.quote(account_id, safe='')}/messages/view?"
        + urllib.parse.urlencode(params)
    )
    data = api_get(c, token, path).get("data")
    if not isinstance(data, list):
        raise BridgeError("message_list_invalid")
    out = {
        "ok": True,
        "target_email": c["target_email"],
        "folderId": fid,
        "status_filter": status,
        "messages": [normalize_message(x) for x in data if isinstance(x, dict)],
    }
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))


def cmd_content(
    c: dict[str, Any],
    token: str,
    folder: str,
    message: str,
    max_chars: int,
) -> None:
    account_id, _, _ = find_context(c, token)
    path = (
        f"/api/accounts/{urllib.parse.quote(account_id, safe='')}"
        f"/folders/{urllib.parse.quote(folder, safe='')}"
        f"/messages/{urllib.parse.quote(message, safe='')}/content"
    )
    body = api_get(c, token, path)
    data = body.get("data")
    content: Any = data
    if isinstance(data, dict) and "content" in data:
        content = data.get("content")
    if content is None:
        content = ""
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    cap = max(256, min(max_chars, 30000))
    truncated = len(content) > cap
    out = {
        "ok": True,
        "messageId": message,
        "folderId": folder,
        "content": content[:cap],
        "truncated": truncated,
    }
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("health")

    lp = sub.add_parser("list")
    lp.add_argument("--limit", type=int, default=25)
    lp.add_argument("--status", choices=("unread", "all"), default="unread")

    cp = sub.add_parser("content")
    cp.add_argument("folder_id")
    cp.add_argument("message_id")
    cp.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CONTENT)

    args = p.parse_args()
    try:
        c = load_credentials()
        token = access_token(c)
        if args.command == "health":
            cmd_health(c, token)
        elif args.command == "list":
            cmd_list(c, token, args.limit, args.status)
        else:
            cmd_content(c, token, args.folder_id, args.message_id, args.max_chars)
        return 0
    except (BridgeError, OSError, json.JSONDecodeError) as e:
        print(
            json.dumps(
                {"ok": False, "error": str(e)[:180]},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
