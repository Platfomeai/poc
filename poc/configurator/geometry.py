"""Panel grid geometry.

Reproduces the ruleset's Row/Col loops (XML:4464, XML:4588) that populate the
``Panel["<field><n>"]`` string-keyed collection.  Frappe child-table ``idx``
plays the part of the ``[RailNumber]`` / ``[StileNumber]`` array index, so the
dynamic key concatenation collapses into ordinary indexing here.

All measurements are canonical inches.  Origin is the bottom-left of the door,
matching the ruleset's "Inches from Bottom to Centre of Divider" convention.
"""

from dataclasses import dataclass, field


@dataclass
class Panel:
	number: int
	row: int
	col: int
	left: float
	bottom: float
	width: float
	height: float

	@property
	def right(self) -> float:
		return self.left + self.width

	@property
	def top(self) -> float:
		return self.bottom + self.height


@dataclass
class Divider:
	"""A rail (horizontal) or stile (vertical) divider bar.

	``centre`` is the distance from the bottom edge (rails) or the left edge
	(stiles) to the centre line of the bar; ``width`` is the bar's thickness.
	"""

	index: int
	centre: float
	width: float

	@property
	def low(self) -> float:
		return self.centre - self.width / 2

	@property
	def high(self) -> float:
		return self.centre + self.width / 2


@dataclass
class DoorGeometry:
	width: float
	height: float
	frame_left: float
	frame_right: float
	frame_top: float
	frame_bottom: float
	rails: list[Divider] = field(default_factory=list)
	stiles: list[Divider] = field(default_factory=list)
	panels: list[Panel] = field(default_factory=list)

	@property
	def inside_width(self) -> float:
		return self.width - self.frame_left - self.frame_right

	@property
	def inside_height(self) -> float:
		return self.height - self.frame_top - self.frame_bottom

	@property
	def horizontal_panels(self) -> int:
		"""XML:4425 -- HorizontalPanels = TotalStiles + 1."""
		return len(self.stiles) + 1

	@property
	def vertical_panels(self) -> int:
		"""XML:4429 -- VerticalPanels = TotalRails + 1."""
		return len(self.rails) + 1

	@property
	def total_panels(self) -> int:
		return self.horizontal_panels * self.vertical_panels


def build(
	width: float,
	height: float,
	frame_left: float,
	frame_right: float,
	frame_top: float,
	frame_bottom: float,
	rails: list[Divider] | None = None,
	stiles: list[Divider] | None = None,
) -> DoorGeometry:
	"""Assemble the door and cut it into panels.

	Rails are sorted bottom-up and stiles left-to-right first, so that panel
	numbering is stable no matter what order the operator entered the rows in.
	"""
	geo = DoorGeometry(
		width=width,
		height=height,
		frame_left=frame_left,
		frame_right=frame_right,
		frame_top=frame_top,
		frame_bottom=frame_bottom,
		rails=sorted(rails or [], key=lambda d: d.centre),
		stiles=sorted(stiles or [], key=lambda d: d.centre),
	)
	geo.panels = _cut_panels(geo)
	return geo


def _spans(low: float, high: float, dividers: list[Divider]) -> list[tuple[float, float]]:
	"""Split the open span [low, high] at each divider bar, skipping the bars."""
	spans: list[tuple[float, float]] = []
	cursor = low

	for divider in dividers:
		spans.append((cursor, divider.low))
		cursor = divider.high

	spans.append((cursor, high))
	return spans


def _cut_panels(geo: DoorGeometry) -> list[Panel]:
	columns = _spans(geo.frame_left, geo.width - geo.frame_right, geo.stiles)
	rows = _spans(geo.frame_bottom, geo.height - geo.frame_top, geo.rails)

	panels: list[Panel] = []
	number = 1

	# Row-major from the top down, so P1 is the top-left panel -- the order a
	# reader scans a door drawing, and the order the spec sheet lists them.
	for row_index, (bottom, top) in enumerate(reversed(rows), start=1):
		for col_index, (left, right) in enumerate(columns, start=1):
			panels.append(
				Panel(
					number=number,
					row=row_index,
					col=col_index,
					left=round(left, 6),
					bottom=round(bottom, 6),
					width=round(right - left, 6),
					height=round(top - bottom, 6),
				)
			)
			number += 1

	return panels


def default_rail_centres(height: float, total: int) -> list[float]:
	"""Even spacing, transcribed from XML:4155 / XML:4171.

	    DefaultSpacing = Height / (TotalRails + 1)
	    centre[i]      = DefaultSpacing * Total - DefaultSpacing * (i - 1)

	Note this walks *down* from the top, so row 1 is the highest rail -- keep
	the ordering as-is; the spec sheet numbering depends on it.
	"""
	if total <= 0:
		return []
	spacing = height / (total + 1)
	return [round(spacing * total - spacing * (i - 1), 6) for i in range(1, total + 1)]


def default_stile_centres(width: float, total: int) -> list[float]:
	"""Even spacing across the width, mirroring default_rail_centres."""
	if total <= 0:
		return []
	spacing = width / (total + 1)
	return [round(spacing * i, 6) for i in range(1, total + 1)]
