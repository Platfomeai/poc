"""OrderDetails assembly -- the spec-sheet print layer.

Reproduces the ruleset's ``DetailSeq`` protocol (XML:272, XML:4436, XML:5599):
``DetailSeq`` starts at 0; each Detail rule emits its lines at ``seq``,
``seq + 10``, ``seq + 20`` ...; a child "Increment DetailSeq" Variable rule then
advances the cursor by the block's full span.  Keeping the stride is what holds
the printed order stable when Detail rules sit inside per-rail / per-panel
loops.

Detail rows whose ``Visible`` expression is false self-suppress, same as the
source.

Note: the live ruleset also emits debug rows into this customer-facing category
(``sys.ImagePath``, ``sys.ImageLink``, ``TESTMatrixPartNumber``).  Those are
deliberately not reproduced here.
"""

from dataclasses import dataclass

from poc.configurator import geometry as geo_mod
from poc.configurator import rules as rules_mod
from poc.configurator import units as u

STRIDE = 10


@dataclass
class DetailLine:
	print_sequence: int
	description: str
	value: str
	visible: bool = True


class DetailBuilder:
	"""Accumulates lines and advances DetailSeq by each block's span."""

	def __init__(self):
		self.seq = 0
		self.lines: list[DetailLine] = []

	def block(self, entries: list[tuple[str, object]]) -> None:
		"""Emit one Detail rule's worth of lines, then advance the cursor."""
		offset = 0
		for description, value in entries:
			if value is None or value == "":
				continue
			self.lines.append(
				DetailLine(
					print_sequence=self.seq + offset,
					description=description,
					value=str(value),
				)
			)
			offset += STRIDE

		# Advance by the block's span, as the "Increment DetailSeq" child rules do.
		self.seq += offset if offset else STRIDE

	def spacer(self) -> None:
		self.lines.append(DetailLine(print_sequence=self.seq, description="", value=""))
		self.seq += STRIDE


def _sides(state: "rules_mod.State", kind: str) -> list[tuple[str, object]]:
	"""Only emit the per-side rows when a side actually differs from the primary."""
	primary = getattr(state, f"{kind}_profile")
	labels = {"right": "Right", "top": "Top", "bottom": "Bottom"}
	return [
		(f"{labels[side]} {kind.title()} Profile", value)
		for side in ("right", "top", "bottom")
		if (value := getattr(state, f"{side}_{kind}_profile")) and value != primary
	]


def build(state: "rules_mod.State", geo: "geo_mod.DoorGeometry") -> list[DetailLine]:
	"""Assemble the full OrderDetails list for a configuration."""
	b = DetailBuilder()

	def length(value: float | None) -> str:
		return u.format_length(value, state.units)

	b.block(
		[
			("Catalogue Item", state.catalogue),
			("Line Number", state.line_number),
			("Quantity", state.quantity),
		]
	)

	b.block(
		[
			("Product", state.product),
			("Door Type", "Drawer Front" if state.door_type == "DrawerFront" else state.door_type),
			("Units", "Imperial" if state.units == "I" else "Metric"),
			("Thickness", state.thickness),
		]
	)

	b.block(
		[
			("Frame Species", state.frame_species),
			("Panel Species", state.panel_species),
			("Panel Type", state.panel_type),
			("Corner Pegs", state.corner_pegs),
		]
	)

	# Per-side profiles are listed individually only when they differ -- the
	# same restraint the ruleset shows by hiding those screen options.
	b.block([("Inside Profile", state.inside_profile)] + _sides(state, "inside"))
	b.block([("Outside Profile", state.outside_profile)] + _sides(state, "outside"))

	b.block(
		[
			("Applied Moulding", None if state.applied_moulding == "(None)" else state.applied_moulding),
			("Inverted Joints", "Yes" if state.inverted_joints else None),
		]
	)

	b.block(
		[
			("Overall Width", length(state.width)),
			("Overall Height", length(state.height)),
		]
	)

	b.block(
		[
			("Frame Width - Left", length(state.frame_left)),
			("Frame Width - Right", length(state.frame_right)),
			("Frame Width - Top", length(state.frame_top)),
			("Frame Width - Bottom", length(state.frame_bottom)),
		]
	)

	b.block(
		[
			("Inside Width", length(state.inside_width)),
			("Inside Height", length(state.inside_height)),
		]
	)

	# Per-divider blocks -- the source emits these from inside the rail/stile
	# loops, one numbered block per divider.
	for position, rail in enumerate(state.rails, start=1):
		b.block(
			[
				(f"Rail #{position} - Centre from Bottom", length(rail.centre)),
				(f"Rail #{position} - Width", length(rail.width)),
			]
		)

	for position, stile in enumerate(state.stiles, start=1):
		b.block(
			[
				(f"Stile #{position} - Centre from Left", length(stile.centre)),
				(f"Stile #{position} - Width", length(stile.width)),
			]
		)

	b.block(
		[
			("Horizontal Panels", geo.horizontal_panels),
			("Vertical Panels", geo.vertical_panels),
			("Total Panels", geo.total_panels),
		]
	)

	for panel in geo.panels:
		b.block(
			[
				(
					f"Panel P{panel.number} (R{panel.row}C{panel.col})",
					f"{length(panel.width)} x {length(panel.height)}",
				)
			]
		)

	if state.door_type != "DrawerFront":
		b.block(
			[
				("Hinge Quantity", state.hinge_qty),
				("Hinge Side", state.hinge_side),
				("Hinge Distance from Edge", length(state.hinge_distance_from_edge)),
			]
		)

	# Final block, mirroring XML:5597-5610.
	b.spacer()
	b.block([("Configured Part Number", state.configured_part_number)])

	return b.lines
