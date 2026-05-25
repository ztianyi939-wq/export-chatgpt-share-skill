#!/usr/bin/env python
"""Export a ChatGPT shared conversation to Obsidian-friendly Markdown."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


VISIBLE_ROLES = {"user", "assistant"}
VISIBLE_CONTENT_TYPE = "text"
DEFAULT_OUT_DIR = "notes"
MATH_DELIMITERS = ("preserve", "dollar")


class ExportError(RuntimeError):
    """Raised for expected export failures with user-facing messages."""


def validate_share_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in {"chatgpt.com", "www.chatgpt.com"}:
        raise ExportError("URL must be a chatgpt.com share link.")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "share":
        raise ExportError("URL path must look like /share/<share_id>.")

    return parts[1]


def fetch_html(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; chatgpt-share-exporter/1.0; "
                "+https://chatgpt.com/share)"
            )
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except urllib.error.URLError as exc:
        raise ExportError(f"Failed to fetch share page: {exc}") from exc


def extract_react_router_table(html: str) -> list[Any]:
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", html, flags=re.DOTALL | re.IGNORECASE)
    for script in scripts:
        if "serverResponse" not in script or "streamController.enqueue" not in script:
            continue

        match = re.search(r"enqueue\((.*)\)\s*;?\s*$", script, flags=re.DOTALL)
        if not match:
            continue

        try:
            encoded_payload = json.loads(match.group(1))
            table = json.loads(encoded_payload)
        except json.JSONDecodeError as exc:
            raise ExportError(f"Failed to decode embedded conversation JSON: {exc}") from exc

        if not isinstance(table, list):
            raise ExportError("Embedded conversation data did not decode to a list.")
        return table

    raise ExportError("Could not find embedded ChatGPT conversation data in the page.")


def decode_reference_table(table: list[Any]) -> Any:
    memo: dict[int, Any] = {}

    def is_ref(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def decode_value(value: Any) -> Any:
        if is_ref(value):
            if value < 0:
                return None
            return decode_at(value)
        return value

    def decode_key(key: str) -> str:
        if re.fullmatch(r"_\d+", key):
            decoded = decode_at(int(key[1:]))
            return str(decoded)
        return key

    def decode_at(index: int) -> Any:
        if index in memo:
            return memo[index]
        if index >= len(table):
            raise ExportError(f"Embedded data references missing index {index}.")

        raw = table[index]
        if isinstance(raw, list):
            decoded_list: list[Any] = []
            memo[index] = decoded_list
            decoded_list.extend(decode_value(item) for item in raw)
            return decoded_list

        if isinstance(raw, dict):
            decoded_dict: OrderedDict[str, Any] = OrderedDict()
            memo[index] = decoded_dict
            for key, value in raw.items():
                decoded_dict[decode_key(key)] = decode_value(value)
            return decoded_dict

        memo[index] = raw
        return raw

    return decode_at(0)


def get_conversation_data(decoded: Any) -> dict[str, Any]:
    try:
        data = decoded["loaderData"]["routes/share.$shareId.($action)"]["serverResponse"]["data"]
    except (KeyError, TypeError) as exc:
        raise ExportError("Embedded data did not contain the expected ChatGPT share payload.") from exc

    if not isinstance(data, dict):
        raise ExportError("ChatGPT share payload had an unexpected shape.")
    return data


def mainline_messages(data: dict[str, Any]) -> list[dict[str, Any]]:
    mapping = data.get("mapping")
    current_node = data.get("current_node")
    if not isinstance(mapping, dict) or not current_node:
        raise ExportError("Conversation payload is missing mapping/current_node data.")

    node_ids: list[str] = []
    seen: set[str] = set()
    node_id = current_node
    while node_id:
        if node_id in seen:
            raise ExportError("Conversation parent chain contains a cycle.")
        seen.add(node_id)
        node = mapping.get(node_id)
        if not isinstance(node, dict):
            raise ExportError(f"Conversation mapping is missing node {node_id}.")
        node_ids.insert(0, node_id)
        node_id = node.get("parent")

    messages: list[dict[str, Any]] = []
    for node_id in node_ids:
        node = mapping.get(node_id)
        message = node.get("message") if isinstance(node, dict) else None
        if isinstance(message, dict):
            messages.append(message)
    return messages


def visible_messages(data: dict[str, Any]) -> list[tuple[str, str]]:
    visible: list[tuple[str, str]] = []
    for message in mainline_messages(data):
        role = message.get("author", {}).get("role")
        content = message.get("content")
        if role not in VISIBLE_ROLES or not isinstance(content, dict):
            continue
        if content.get("content_type") != VISIBLE_CONTENT_TYPE:
            continue

        parts = content.get("parts")
        if not isinstance(parts, list) or not parts:
            continue

        text_parts = [part for part in parts if isinstance(part, str) and part.strip()]
        if text_parts:
            visible.append((role, "\n\n".join(text_parts).strip()))

    if not visible:
        raise ExportError("No visible user/assistant text messages found.")
    return visible


def timestamp_to_iso(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return ""
    return datetime.fromtimestamp(value, UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def yaml_quote(value: Any) -> str:
    text = "" if value is None else str(value)
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def slugify_title(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", title).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.rstrip(". ")
    return cleaned or "chatgpt-share"


def normalize_math_delimiters(markdown: str) -> str:
    """Convert LaTeX \( \) and \[ \] delimiters to Obsidian-friendly dollars."""

    chunks: list[tuple[bool, str]] = []
    current: list[str] = []
    in_fence = False

    for line in markdown.splitlines(keepends=True):
        stripped = line.lstrip()
        is_fence = stripped.startswith("```") or stripped.startswith("~~~")
        if is_fence:
            if current:
                chunks.append((in_fence, "".join(current)))
                current = []
            chunks.append((in_fence, line))
            in_fence = not in_fence
            continue
        current.append(line)

    if current:
        chunks.append((in_fence, "".join(current)))

    def normalize_chunk(chunk: str) -> str:
        chunk = re.sub(r"\\\s+\\mathrm", r"\\,\\mathrm", chunk)
        chunk = re.sub(r"\\\[(.*?)\\\]", lambda m: f"$$\n{m.group(1).strip()}\n$$", chunk, flags=re.DOTALL)
        return re.sub(r"\\\((.*?)\\\)", lambda m: f"${m.group(1).strip()}$", chunk, flags=re.DOTALL)

    return "".join(chunk if fenced else normalize_chunk(chunk) for fenced, chunk in chunks)


def render_markdown(
    data: dict[str, Any],
    messages: list[tuple[str, str]],
    source_url: str,
    share_id: str,
    math_delimiters: str = "preserve",
) -> str:
    title = str(data.get("title") or "ChatGPT Share")
    frontmatter = OrderedDict(
        [
            ("title", title),
            ("source", source_url),
            ("share_id", share_id),
            ("created", timestamp_to_iso(data.get("create_time"))),
            ("updated", timestamp_to_iso(data.get("update_time"))),
            ("model", data.get("default_model_slug") or ""),
            ("exported_at", datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")),
        ]
    )

    lines = ["---"]
    lines.extend(f"{key}: {yaml_quote(value)}" for key, value in frontmatter.items())
    lines.extend(["---", "", f"# {title}", ""])

    for role, text in messages:
        heading = "User" if role == "user" else "Assistant"
        lines.extend([f"## {heading}", "", text, ""])

    markdown = "\n".join(lines).rstrip() + "\n"
    if math_delimiters == "dollar":
        markdown = normalize_math_delimiters(markdown)
    return markdown


def export_share(url: str, out_dir: Path, filename: str | None = None, math_delimiters: str = "preserve") -> Path:
    share_id = validate_share_url(url)
    html = fetch_html(url)
    table = extract_react_router_table(html)
    decoded = decode_reference_table(table)
    data = get_conversation_data(decoded)
    messages = visible_messages(data)

    title = str(data.get("title") or "ChatGPT Share")
    output_name = filename or f"{slugify_title(title)}.md"
    output_path = out_dir / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(data, messages, url, share_id, math_delimiters), encoding="utf-8")
    return output_path.resolve()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("share_url", help="ChatGPT share URL, for example https://chatgpt.com/share/<id>")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help=f"Output directory (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("--filename", help="Optional Markdown filename, for example conversation.md")
    parser.add_argument(
        "--math-delimiters",
        choices=MATH_DELIMITERS,
        default="preserve",
        help="Use 'dollar' to convert \\(...\\) and \\[...\\] to Obsidian $/$$ math delimiters.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        output_path = export_share(args.share_url, Path(args.out), args.filename, args.math_delimiters)
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
