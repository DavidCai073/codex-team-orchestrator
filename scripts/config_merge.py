"""Conservative, formatting-preserving edits with a TOML semantic postcondition."""
from __future__ import annotations

import copy
import json
import math
import re
import tomllib


class ConfigMergeError(ValueError):
    """The proposed edit cannot be proven to preserve unmanaged configuration."""


def same_semantics(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same_semantics(value, right[key]) for key, value in left.items())
    if isinstance(left, list):
        return len(left) == len(right) and all(same_semantics(a, b) for a, b in zip(left, right))
    if isinstance(left, float) and math.isnan(left):
        return math.isnan(right)
    return left == right


def statements(lines: list[str]) -> list[tuple[int, int]]:
    """Locate complete statements; never interpret string contents as TOML keys."""
    result: list[tuple[int, int]] = []
    quote = ""
    depth = 0
    start: int | None = None
    for line_number, line in enumerate(lines):
        if start is None and line.strip() and not line.lstrip().startswith("#"):
            start = line_number
        index = 0
        while index < len(line):
            char = line[index]
            if quote:
                if quote[0] == '"' and char == "\\":
                    index += 2
                    continue
                if line.startswith(quote, index):
                    index += len(quote)
                    if len(quote) == 3:
                        # TOML permits four/five quotes at a multiline closing delimiter.
                        while index < len(line) and line[index] == quote[0]:
                            index += 1
                    quote = ""
                    continue
            elif char == "#":
                break
            elif char in "\"'":
                quote = char * 3 if line.startswith(char * 3, index) else char
                index += len(quote)
                continue
            elif char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1
            index += 1
        if start is not None and not quote and depth == 0:
            result.append((start, line_number + 1))
            start = None
    if quote or depth or start is not None:
        raise ConfigMergeError("Unsupported TOML statement layout; merge the selected keys manually.")
    return result


def literal(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    raise ConfigMergeError("Preset values must be strings, integers, or booleans.")


def merge_values(existing: str, selected: dict[str, object]) -> str:
    """Edit only root scalars and [agents] scalars, or fail before any write."""
    try:
        original = tomllib.loads(existing)
        expected = copy.deepcopy(original)
        lines = existing.splitlines()
        for section, values in (("", {k: v for k, v in selected.items() if k != "agents"}),
                                ("agents", selected.get("agents", {}))):
            if not isinstance(values, dict):
                raise ConfigMergeError("Selected [agents] settings must be a table.")
            if not values:
                continue
            destination = expected if not section else expected.setdefault(section, {})
            if not isinstance(destination, dict):
                raise ConfigMergeError("Existing agents value is not an editable table.")
            destination.update(values)
            spans = statements(lines)
            headers = [(a, b, lines[a].strip()) for a, b in spans
                       if lines[a].lstrip().startswith("[")]
            if not section:
                begin, end = 0, headers[0][0] if headers else len(lines)
            else:
                matching = [(i, a, b) for i, (a, b, header) in enumerate(headers)
                            if re.fullmatch(r"\[agents\]\s*(?:#.*)?", header)]
                if matching:
                    index, _, begin = matching[0]
                    end = headers[index + 1][0] if index + 1 < len(headers) else len(lines)
                else:
                    lines.extend(["", "[agents]"])
                    begin = end = len(lines)
            missing: list[str] = []
            for key, value in values.items():
                if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
                    raise ConfigMergeError("Preset contains an unsupported key.")
                matches = [(a, b) for a, b in spans if begin <= a < end
                           and re.match(rf"^\s*{re.escape(key)}\s*=", lines[a])]
                replacement = f"{key} = {literal(value)}"
                if matches:
                    first, last = matches[0]
                    if last != first + 1:
                        raise ConfigMergeError(f"Managed key {key} uses a multiline value; merge manually.")
                    lines[first] = replacement
                else:
                    missing.append(replacement)
            lines[end:end] = missing
        candidate = "\n".join(lines).rstrip() + "\n"
        if not same_semantics(tomllib.loads(candidate), expected):
            raise ConfigMergeError("Semantic preservation failed; no configuration was written.")
        return candidate
    except tomllib.TOMLDecodeError as error:
        # Do not echo configuration contents, which may contain credentials.
        raise ConfigMergeError("Unsupported or invalid TOML layout; review and merge selected keys manually.") from error
