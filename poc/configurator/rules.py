"""Ported rule logic for the SQUARE / MITRE five-piece door.

Each function below is a transcription of a named rule (or a contiguous run of
rules) from the ``Interactive`` RuleTree of
``Ruleset JS-CabinetDoor-A-Rev02.CONFIGURE``.  Function names echo the original
``Caption`` attributes so the two can be read side by side.

Two semantics from the source engine that are easy to lose in translation:

* **Sequential same-name assignment.**  Repeated ``<var name="Collapse">``
  blocks inside one ``<vars>`` are read-modify-write steps that run in document
  order.  Plain Python reassignment gives this for free -- but do not reorder
  the statements in ``apply_collapse``.
* **``.PreviousValue``.**  Several Message rules compare against the prior
  evaluation pass so a warning fires only on the *transition* into the invalid
  state.  ``evaluate`` accepts a ``previous`` snapshot for this.

``evaluate`` mutates the state it is given (the ruleset writes
``FrameWidth*.value`` directly) and returns the messages raised.
"""

from dataclasses import dataclass, field

from poc.configurator import geometry, ranges
from poc.configurator import units as u

#: MessageLevel values as used by the source ruleset.
LEVEL_ERROR = 1
LEVEL_ERROR_ALT = 2
LEVEL_WARNING = 4

BLOCKING_LEVELS = (LEVEL_ERROR, LEVEL_ERROR_ALT)


@dataclass
class Message:
	level: int
	title: str
	message: str

	@property
	def blocking(self) -> bool:
		return self.level in BLOCKING_LEVELS


@dataclass
class DividerInput:
	"""One row of the rail/stile child table."""

	index: int
	centre: float | None = None
	width: float | None = None


@dataclass
class State:
	"""The subset of the 95 component attributes this POC models.

	All lengths are canonical inches, matching the ruleset's practice of doing
	every calculation against the ``*Imperial`` attributes regardless of the
	operator's ``Units`` selection.
	"""

	product: str = "SQUARE"
	door_type: str = "Door"
	units: str = "I"

	frame_species: str | None = None
	panel_species: str | None = None
	corner_pegs: str | None = None

	#: Per-side profiles.  When the "all sides equal" flags are set the
	#: controller copies the primary into the other three, mirroring the
	#: ruleset's ``DefaultValue="=LeftInsideProfile"`` on each side.
	inside_profile: str | None = None
	right_inside_profile: str | None = None
	top_inside_profile: str | None = None
	bottom_inside_profile: str | None = None
	outside_profile: str | None = None
	right_outside_profile: str | None = None
	top_outside_profile: str | None = None
	bottom_outside_profile: str | None = None
	applied_moulding: str = "(None)"

	thickness: str | None = None
	thickness_uom: str = "Imperial"
	inverted_joints: bool = False

	catalogue: str = "CONFIGURE"
	line_number: int = 1
	quantity: float = 1.0

	width: float = 0.0
	height: float = 0.0
	frame_left: float = 0.0
	frame_right: float = 0.0
	frame_top: float = 0.0
	frame_bottom: float = 0.0
	custom_frame_widths: bool = False

	rails: list[DividerInput] = field(default_factory=list)
	stiles: list[DividerInput] = field(default_factory=list)

	hinge_qty: int = 2
	hinge_side: str = "Left"
	hinge_distance_from_edge: float = 5.0

	panel_type: str = "Raised"
	#: Per-panel overrides drive the uniqueness check behind the CUSTOM- part
	#: number.  Empty means every panel matches panel 1.
	panel_signatures: list[tuple] = field(default_factory=list)

	# -- derived (written by evaluate) ---------------------------------------
	inside_width: float = 0.0
	inside_height: float = 0.0
	horizontal_panels: int = 1
	vertical_panels: int = 1
	total_panels: int = 1
	collapse_applied: bool = False
	configured_part_number: str | None = None

	@property
	def minimum_panel_size(self) -> float:
		return ranges.MINIMUM_PANEL_SIZE


# ---------------------------------------------------------------------------
# Rules, in the order the Interactive tree runs them
# ---------------------------------------------------------------------------


def recalculate_inside_dimensions(state: State) -> None:
	"""XML: "InsideWidthImperial" / "InsideHeightImperial" variable rules."""
	state.inside_width = round(state.width - state.frame_left - state.frame_right, 6)
	state.inside_height = round(state.height - state.frame_top - state.frame_bottom, 6)


def apply_collapse(state: State, previous: State | None = None) -> list[Message]:
	"""Rule: "Initialize and Default Collapse Values ... for hinge consideration A - R01".

	When the finished panel would fall below ``MinimumPanelSize`` the ruleset
	does *not* reject the door -- it silently rewrites all four frame widths to
	a computed ``Collapse`` value and raises a level-4 advisory.  That
	rewrite-then-warn behaviour is deliberate and is reproduced as-is.

	The accumulator below is four sequential assignments to ``Collapse`` in the
	source; order matters because each step reads the previous result.
	"""
	recalculate_inside_dimensions(state)

	too_small = (
		state.inside_height < state.minimum_panel_size
		or state.inside_width < state.minimum_panel_size
	)
	if not too_small:
		state.collapse_applied = False
		return []

	# --- sequential read-modify-write, do not reorder ---
	collapse = 1.75 if state.door_type == "Door" else 1.5
	if state.frame_left > 2.75 and state.door_type == "DrawerFront":
		collapse = collapse + 0.25
	if state.frame_top > 3.75:
		collapse = collapse + 0.25
	if state.frame_top > 4.75:
		collapse = collapse + 0.25
	# --- end accumulator ---

	state.frame_left = collapse
	state.frame_right = collapse
	state.frame_top = collapse
	state.frame_bottom = collapse
	state.collapse_applied = True

	recalculate_inside_dimensions(state)

	# ``.PreviousValue`` gate: only announce the adjustment on the pass where
	# the door first became too small, so re-saving a collapsed door is quiet.
	if previous is not None and previous.collapse_applied:
		return []

	return [
		Message(
			level=LEVEL_WARNING,
			title="Panel Height Warning",
			message=(
				"Minimum Panel Height was not met, frame sizes are being adjusted "
				f"to {u.to_fraction(collapse)}\". Please review dimensions and Frame Widths."
			),
		)
	]


def validate_hinges(state: State) -> list[Message]:
	"""Rule: "limitation for the open frame with" (XML:1693).

	Level 2 in the source -- blocking.  The original also force-writes
	``FrameWidthImperial.uservalue = 1.75``; we surface the error instead of
	silently correcting, because on a Desk form the operator can see and fix the
	field directly.

	Note the source gates this on ``PanelType = "Open Panel"`` -- an open frame
	has no panel bracing the hinge side, so the frame itself has to carry the
	screw.  Solid panels are exempt, which is what lets a collapsed drawer front
	sit below 1 3/4".
	"""
	messages: list[Message] = []
	hinge_frame = state.frame_left if state.hinge_side == "Left" else state.frame_right

	if state.panel_type == "Open Panel" and hinge_frame < ranges.MINIMUM_HINGE_FRAME_WIDTH:
		messages.append(
			Message(
				level=LEVEL_ERROR_ALT,
				title="Frame width profile",
				message=(
					"Due to the hinge, the width of the open frame cannot be less "
					"than 1 3/4 inches."
				),
			)
		)

	if not ranges.HINGE_QTY.contains(state.hinge_qty):
		messages.append(
			Message(
				level=LEVEL_ERROR,
				title="Hinge Quantity",
				message=f"Hinge quantity must be between {int(ranges.HINGE_QTY.min)} and "
				f"{int(ranges.HINGE_QTY.max)}.",
			)
		)

	if not ranges.HINGE_DISTANCE.contains(state.hinge_distance_from_edge):
		messages.append(
			Message(
				level=LEVEL_ERROR,
				title="Hinge Placement",
				message=f"Hinge distance from edge must be between "
				f"{int(ranges.HINGE_DISTANCE.min)}\" and {int(ranges.HINGE_DISTANCE.max)}\".",
			)
		)

	return messages


def validate_dimensions(state: State) -> list[Message]:
	"""Range checks from the <Range> nodes on Width/Height/FrameWidth*."""
	messages: list[Message] = []
	panel = ranges.panel_range(state.product)
	frame = ranges.frame_width_range(state.product)

	for label, value in (("Width", state.width), ("Height", state.height)):
		if not panel.contains(value):
			messages.append(
				Message(
					level=LEVEL_ERROR,
					title=f"{label} Out of Range",
					message=f"{label} must be between {u.to_fraction(panel.min)}\" and "
					f"{u.to_fraction(panel.max)}\".",
				)
			)

	sides = (
		("Left", state.frame_left),
		("Right", state.frame_right),
		("Top", state.frame_top),
		("Bottom", state.frame_bottom),
	)
	for label, value in sides:
		if not frame.contains(value):
			messages.append(
				Message(
					level=LEVEL_ERROR,
					title="Frame Width Out of Range",
					message=f"{label} frame width must be between {u.to_fraction(frame.min)}\" "
					f"and {u.to_fraction(frame.max)}\".",
				)
			)

	return messages


def default_divider_spacing(state: State, reset: bool = False) -> None:
	"""Rule: "If RailReset Flag, force default width and spacing" (XML:4171).

	Fills any row with no centre yet; ``reset=True`` reproduces the
	``RailResetFlag`` behaviour of re-spacing every row, which the source fires
	whenever the divider count changes.
	"""
	default_width = 2.0

	rail_centres = geometry.default_rail_centres(state.height, len(state.rails))
	for row, centre in zip(state.rails, rail_centres, strict=False):
		if reset or row.centre is None:
			row.centre = centre
		if reset or row.width is None:
			row.width = default_width

	stile_centres = geometry.default_stile_centres(state.width, len(state.stiles))
	for row, centre in zip(state.stiles, stile_centres, strict=False):
		if reset or row.centre is None:
			row.centre = centre
		if reset or row.width is None:
			row.width = default_width


def validate_dividers(state: State) -> list[Message]:
	"""Rules at XML:4223 and XML:4227, applied per index.

	Two checks, exactly as written in the source ConditionExpressions:

	1. the bar must sit clear of the frame at both ends;
	2. it must not overlap the previous bar (``[RailNumber-1]``).

	The previous-bar test walks the rows in the order the operator sees them,
	which for rails is top-down -- so "previous" is the bar *above*.
	"""
	messages: list[Message] = []

	messages += _validate_divider_axis(
		rows=state.rails,
		label="Divider",
		span=state.height,
		frame_low=state.frame_bottom,
		frame_high=state.frame_top,
		descending=True,
	)
	messages += _validate_divider_axis(
		rows=state.stiles,
		label="Stile",
		span=state.width,
		frame_low=state.frame_left,
		frame_high=state.frame_right,
		descending=False,
	)

	return messages


def _validate_divider_axis(
	rows: list[DividerInput],
	label: str,
	span: float,
	frame_low: float,
	frame_high: float,
	descending: bool,
) -> list[Message]:
	messages: list[Message] = []

	for position, row in enumerate(rows, start=1):
		if row.centre is None or row.width is None:
			continue

		half = row.width / 2

		if row.centre - half < frame_low or row.centre + half > span - frame_high:
			messages.append(
				Message(
					level=LEVEL_ERROR,
					title=f"{label} Position",
					message=f"Please ensure {label} #{position} is positioned inside the frame.",
				)
			)

		if position > 1:
			previous = rows[position - 2]
			if previous.centre is None or previous.width is None:
				continue
			previous_half = previous.width / 2

			overlaps = (
				row.centre + half > previous.centre - previous_half
				if descending
				else row.centre - half < previous.centre + previous_half
			)
			if overlaps:
				messages.append(
					Message(
						level=LEVEL_ERROR,
						title=f"{label} Overlap",
						message=f"{label} #{position} overlaps {label} #{position - 1}.",
					)
				)

	return messages


def build_geometry(state: State) -> geometry.DoorGeometry:
	"""Rules "Loop through each Panel" / Row + Col loops (XML:4464, XML:4588)."""
	geo = geometry.build(
		width=state.width,
		height=state.height,
		frame_left=state.frame_left,
		frame_right=state.frame_right,
		frame_top=state.frame_top,
		frame_bottom=state.frame_bottom,
		rails=[
			geometry.Divider(index=r.index, centre=r.centre, width=r.width)
			for r in state.rails
			if r.centre is not None and r.width is not None
		],
		stiles=[
			geometry.Divider(index=s.index, centre=s.centre, width=s.width)
			for s in state.stiles
			if s.centre is not None and s.width is not None
		],
	)

	state.horizontal_panels = geo.horizontal_panels
	state.vertical_panels = geo.vertical_panels
	state.total_panels = geo.total_panels

	return geo


def resolve_part_number(state: State, matrix_lookup=None) -> list[Message]:
	"""Rule: "Set Part Number from Matrix if match found, or to Configured Part".

	The source resolves against ``X-IPNResolution`` -- an external part-number
	matrix that was **not** included in the ruleset export.  ``matrix_lookup``
	is the seam for it; when it returns nothing (or the panel-uniqueness
	``Exception`` trips) we fall through to ``"CUSTOM-" + Product``, which is
	exactly what the real ruleset does.
	"""
	exception = _panels_differ(state)

	resolved = None
	if matrix_lookup is not None and not exception:
		resolved = matrix_lookup(state)

	if resolved:
		state.configured_part_number = resolved
	elif state.product == "PART":
		state.configured_part_number = "CUSTOM-PART"
	else:
		state.configured_part_number = f"CUSTOM-{state.product}"

	return []


def _panels_differ(state: State) -> bool:
	"""Rule: "Check for Exceptions - Some Panel elements must match".

	The source compares each panel's type, profile and beading against panel 1
	and sets ``Exception = True`` on any mismatch, which forces a custom part
	number.
	"""
	if not state.panel_signatures:
		return False
	first = state.panel_signatures[0]
	return any(signature != first for signature in state.panel_signatures[1:])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def evaluate(
	state: State,
	previous: State | None = None,
	reset_dividers: bool = False,
	matrix_lookup=None,
) -> tuple[list[Message], geometry.DoorGeometry]:
	"""Run the ported rules in the ruleset's document order.

	Mutates ``state`` in place (the source engine likewise writes back to the
	component attributes) and returns the messages raised plus the resulting
	geometry.
	"""
	messages: list[Message] = []

	recalculate_inside_dimensions(state)
	messages += validate_dimensions(state)
	messages += apply_collapse(state, previous=previous)

	default_divider_spacing(state, reset=reset_dividers)
	messages += validate_dividers(state)
	messages += validate_hinges(state)

	geo = build_geometry(state)
	messages += resolve_part_number(state, matrix_lookup=matrix_lookup)

	return messages, geo
