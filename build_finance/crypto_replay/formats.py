"""Pure semantic format predicates for replay contracts."""

from __future__ import annotations

import re

_CANONICAL_DECIMAL = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")


def _validate_integer_bounds(minimum: int | None, maximum: int | None) -> None:
    if minimum is not None and (isinstance(minimum, bool) or not isinstance(minimum, int)):
        raise TypeError("minimum must be an integer or None")
    if maximum is not None and (isinstance(maximum, bool) or not isinstance(maximum, int)):
        raise TypeError("maximum must be an integer or None")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("minimum must not exceed maximum")


def parse_bounded_decimal_string(
    value: object,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Parse one canonical decimal integer string within optional bounds."""
    _validate_integer_bounds(minimum, maximum)
    if not isinstance(value, str) or _CANONICAL_DECIMAL.fullmatch(value) is None:
        raise ValueError("value is not a canonical decimal integer string")
    parsed = int(value, 10)
    if minimum is not None and parsed < minimum:
        raise ValueError("decimal integer is below the minimum")
    if maximum is not None and parsed > maximum:
        raise ValueError("decimal integer is above the maximum")
    return parsed


def is_bounded_decimal_string(
    value: object,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> bool:
    """Return whether a value is a canonical decimal string in range."""
    _validate_integer_bounds(minimum, maximum)
    try:
        parse_bounded_decimal_string(value, minimum=minimum, maximum=maximum)
    except ValueError:
        return False
    return True


def has_utf8_length_at_most(value: object, maximum_bytes: int) -> bool:
    """Apply a semantic UTF-8 byte maximum (not JSON Schema maxLength)."""
    if isinstance(maximum_bytes, bool) or not isinstance(maximum_bytes, int):
        raise TypeError("maximum_bytes must be an integer")
    if maximum_bytes < 0:
        raise ValueError("maximum_bytes must be non-negative")
    if not isinstance(value, str):
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= maximum_bytes
    except UnicodeEncodeError:
        return False
