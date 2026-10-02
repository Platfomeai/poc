"""Unit conversion and fractional display.

Stands in for the ruleset's ``Usr.Convert`` user function, which the source XML
calls with ``Mode = "mm2inch" | "inch2mm"``.  As in the original ruleset,
**imperial is the canonical internal unit** -- every rule in ``rules.py`` reads
the ``*_imperial`` values regardless of what the operator selected for ``Units``.
"""

import math
import re

MM_PER_INCH = 25.4

#: The ruleset declares DisplayFormat="Fraction" DisplayPrecision="1/16" on every
#: imperial dimension, so 1/16" is both the display precision and the snap grid.
DEFAULT_DENOMINATOR = 16

_FRACTION_RE = re.compile(
	r"""^\s*
	(?P<sign>-)?\s*
	(?:(?P<whole>\d+(?:\.\d+)?)\s*)?
	(?:(?P<num>\d+)\s*/\s*(?P<den>\d+))?
	\s*(?:"|''|in|inch|inches)?\s*$""",
	re.VERBOSE | re.IGNORECASE,
)


def mm_to_inch(mm: float | None) -> float | None:
	if mm is None:
		return None
	return float(mm) / MM_PER_INCH


def inch_to_mm(inch: float | None) -> float | None:
	if inch is None:
		return None
	return float(inch) * MM_PER_INCH


def snap(value: float | None, denominator: int = DEFAULT_DENOMINATOR) -> float | None:
	"""Round to the nearest 1/``denominator`` of an inch."""
	if value is None:
		return None
	return round(float(value) * denominator) / denominator


def to_fraction(value: float | None, denominator: int = DEFAULT_DENOMINATOR) -> str:
	"""Render inches the way the configurator screens do: ``24 3/16``.

	Reduces the fraction (``8/16`` -> ``1/2``) and drops a zero numerator.
	"""
	if value is None:
		return ""

	value = float(value)
	sign = "-" if value < 0 else ""
	value = abs(value)

	ticks = round(value * denominator)
	whole, remainder = divmod(ticks, denominator)

	if remainder == 0:
		return f"{sign}{whole}"

	divisor = math.gcd(remainder, denominator)
	numerator = remainder // divisor
	reduced_denominator = denominator // divisor

	if whole == 0:
		return f"{sign}{numerator}/{reduced_denominator}"
	return f"{sign}{whole} {numerator}/{reduced_denominator}"


def from_fraction(text: str | float | None) -> float | None:
	"""Parse ``24 3/16``, ``3/16``, ``24``, ``24.1875`` (and a trailing ``"``).

	Returns ``None`` for blank input; raises ``ValueError`` on anything it cannot
	read, so the caller can surface a field-level message.
	"""
	if text is None:
		return None
	if isinstance(text, int | float):
		return float(text)

	text = str(text).strip()
	if not text:
		return None

	match = _FRACTION_RE.match(text)
	if not match or not (match.group("whole") or match.group("num")):
		raise ValueError(f"Cannot read {text!r} as inches. Try a value like 24 3/16.")

	total = float(match.group("whole") or 0)

	if match.group("num"):
		denominator = int(match.group("den"))
		if denominator == 0:
			raise ValueError(f"Cannot read {text!r} as inches: division by zero.")
		total += int(match.group("num")) / denominator

	return -total if match.group("sign") else total


def format_length(inches: float | None, units: str, metric_precision: int = 1) -> str:
	"""Format a canonical imperial value for display in the operator's units."""
	if inches is None:
		return ""
	if units == "M":
		return f"{round(inch_to_mm(inches), metric_precision)} mm"
	return f'{to_fraction(inches)}"'
