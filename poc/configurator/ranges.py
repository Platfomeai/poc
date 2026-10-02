"""Per-unit min/max/increment tables, transcribed from the ruleset's <Range> nodes.

The source XML attaches 1..3 named ranges to each dimension attribute
(``PanelImperial``, ``FrameWidthImperial``, ``FrameWidthMetric``, ``Ethos``) and
picks between them at runtime via ``ScreenOption/@SelectedRanges``.  The POC
covers the SQUARE/MITRE slice, so only the non-Ethos ranges are active here;
``Ethos`` is carried for reference because no ScreenOption in the export ever
selects it -- that behaviour lives in the ``Arvin/Ethos`` sub-ruleset we were
not given.
"""

from dataclasses import dataclass

from poc.configurator import units as u


@dataclass(frozen=True)
class Range:
	name: str
	min: float
	max: float
	increment: float

	def clamp(self, value: float | None) -> float | None:
		if value is None:
			return None
		return min(self.max, max(self.min, float(value)))

	def snap(self, value: float | None) -> float | None:
		"""Clamp, then round to the nearest whole increment."""
		value = self.clamp(value)
		if value is None:
			return None
		steps = round((value - self.min) / self.increment)
		return round(self.min + steps * self.increment, 6)

	def contains(self, value: float | None) -> bool:
		if value is None:
			return False
		return self.min <= float(value) <= self.max


# -- Imperial (canonical) ----------------------------------------------------
PANEL_IMPERIAL = Range("PanelImperial", 3.0, 200.0, 0.0625)
FRAME_WIDTH_IMPERIAL = Range("FrameWidthImperial", 1.0, 6.0, 0.0625)
ETHOS_PANEL_IMPERIAL = Range("Ethos", 0.75, 5.0, 0.0625)
ETHOS_FRAME_IMPERIAL = Range("Ethos", 0.25, 5.0, 0.0625)

# -- Metric (mirror) ---------------------------------------------------------
FRAME_WIDTH_METRIC = Range("FrameWidthMetric", 25.0, 114.5, 0.1)
ETHOS_FRAME_METRIC = Range("Ethos", 5.0, 127.0, 0.1)

# -- Counts ------------------------------------------------------------------
DIVIDERS = Range("0-3", 0, 3, 1)
HINGE_QTY = Range("HingeQty", 2, 4, 1)
HINGE_DISTANCE = Range("Range", 5, 20, 1)


#: Minimum finished panel dimension.  Below this the ruleset collapses the frame
#: rather than rejecting the door outright -- see rules.apply_collapse.
MINIMUM_PANEL_SIZE = 3.0

#: XML:1696 -- "Due to the hinge, the width of the open frame cannot be less
#: than 1 3/4 inches."
MINIMUM_HINGE_FRAME_WIDTH = 1.75


def panel_range(product: str) -> Range:
	return ETHOS_PANEL_IMPERIAL if product == "Ethos" else PANEL_IMPERIAL


def frame_width_range(product: str) -> Range:
	return ETHOS_FRAME_IMPERIAL if product == "Ethos" else FRAME_WIDTH_IMPERIAL


def metric_equivalent(imperial: Range) -> Range:
	"""The metric range covering the same physical span, for display bounds."""
	return Range(
		name=imperial.name.replace("Imperial", "Metric"),
		min=round(u.inch_to_mm(imperial.min), 1),
		max=round(u.inch_to_mm(imperial.max), 1),
		increment=0.1,
	)
