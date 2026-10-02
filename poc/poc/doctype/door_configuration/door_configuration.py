"""Door Configuration controller.

Translates the Desk document into a ``rules.State``, runs the ported ruleset,
and writes the results back: derived fields, the metric/imperial mirror, the
OrderDetails child table, and the SVG preview.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from poc.configurator import details as details_mod
from poc.configurator import preview as preview_mod
from poc.configurator import rules as rules_mod
from poc.configurator import units as u

#: Imperial dimension fields stored as Data so the operator can type "24 3/16",
#: paired with the metric field that mirrors them.
LENGTH_PAIRS = (
	("width_imperial", "width_metric"),
	("frame_width_imperial", "frame_width_metric"),
	("height_imperial", "height_metric"),
	("frame_width_left_imperial", "frame_width_left_metric"),
	("frame_width_right_imperial", "frame_width_right_metric"),
	("frame_width_top_imperial", "frame_width_top_metric"),
	("frame_width_bottom_imperial", "frame_width_bottom_metric"),
)


#: The form shows friendly labels; the rule engine speaks the ruleset's own
#: vocabulary ("I"/"M", "DrawerFront").  Normalise at this boundary only.
UNIT_CODE = {"Imperial": "I", "Metric": "M"}
DOOR_TYPE_CODE = {"Door": "Door", "Drawer Front": "DrawerFront"}


class DoorConfiguration(Document):
	def validate(self):
		self.sync_units()
		# Local, not a document flag: flags persist on the in-memory document
		# across successive saves, which would silently re-space dividers the
		# operator had just positioned by hand.
		reset_dividers = self.sync_divider_rows()

		state = self.to_state()
		previous = _state_from_doc(self.get_doc_before_save())

		messages, geo = rules_mod.evaluate(
			state,
			previous=previous,
			reset_dividers=reset_dividers,
			matrix_lookup=lookup_part_number,
		)

		self.apply_state(state, geo)
		self.build_details(state, geo)
		self.report(messages)

	# -- unit handling -------------------------------------------------------

	def sync_units(self):
		"""Keep the imperial/metric pairs in step.

		Imperial is canonical.  When the operator is working in metric we
		convert their entry down into the imperial field first, then mirror
		back out so both halves always agree -- this is what the ruleset's
		``Usr.Convert`` round-trip does, just without the Mode variable.
		"""
		for imperial_field, metric_field in LENGTH_PAIRS:
			if self.units == "Metric":
				metric = self.get(metric_field)
				inches = u.mm_to_inch(metric) if metric else None
				self.set(imperial_field, u.to_fraction(inches) if inches is not None else None)
			else:
				inches = self._parse(imperial_field)
				self.set(metric_field, round(u.inch_to_mm(inches), 1) if inches is not None else 0)

		# Uniform frame widths unless the operator asked for per-side control.
		# The master "Frame Width" field is what they see in that case; the four
		# members only appear once Custom Frame Widths is ticked.
		if not self.custom_frame_widths:
			for side in ("left", "right", "top", "bottom"):
				self.set(f"frame_width_{side}_imperial", self.frame_width_imperial)
				self.set(f"frame_width_{side}_metric", self.frame_width_metric)

		self.propagate_profiles()

	def propagate_profiles(self):
		"""Copy the primary profile to the other three sides when they match.

		Mirrors the ruleset's per-side ScreenOptions, which default to
		``=LeftInsideProfile`` and hide themselves while AllSidesEqual is set.
		"""
		if self.all_sides_equal_inside:
			for side in ("right", "top", "bottom"):
				self.set(f"{side}_inside_profile", self.inside_profile)
		if self.all_sides_equal_outside:
			for side in ("right", "top", "bottom"):
				self.set(f"{side}_outside_profile", self.outside_profile)

	def _parse(self, fieldname: str) -> float | None:
		"""Read a fraction-formatted Data field, raising a field-level error."""
		try:
			return u.from_fraction(self.get(fieldname))
		except ValueError as exc:
			frappe.throw(str(exc), title=_(self.meta.get_label(fieldname)))

	# -- divider rows --------------------------------------------------------

	def sync_divider_rows(self) -> bool:
		"""Resize the child tables to match the divider counts.

		Returns True when a table actually changed size, which reproduces the
		ruleset's ``RailResetFlag``: every row is then re-spaced evenly rather
		than leaving a stale position behind.  Saves that do not change the
		count leave the operator's positions alone.
		"""
		self.rail_dividers = max(0, min(3, int(self.rail_dividers or 0)))
		self.stile_dividers = max(0, min(3, int(self.stile_dividers or 0)))

		rails_changed = _resize(self, "rails", self.rail_dividers)
		stiles_changed = _resize(self, "stiles", self.stile_dividers)
		return rails_changed or stiles_changed

	# -- state bridge --------------------------------------------------------

	def to_state(self) -> rules_mod.State:
		return rules_mod.State(
			product=self.product,
			door_type=DOOR_TYPE_CODE.get(self.door_type, self.door_type),
			units=UNIT_CODE.get(self.units, self.units),
			frame_species=self.frame_species,
			panel_species=self.panel_species,
			corner_pegs=self.corner_pegs,
			inside_profile=self.inside_profile,
			right_inside_profile=self.right_inside_profile,
			top_inside_profile=self.top_inside_profile,
			bottom_inside_profile=self.bottom_inside_profile,
			outside_profile=self.outside_profile,
			right_outside_profile=self.right_outside_profile,
			top_outside_profile=self.top_outside_profile,
			bottom_outside_profile=self.bottom_outside_profile,
			applied_moulding=self.applied_moulding,
			thickness=self.thickness if self.thickness_uom == "Imperial" else self.thickness_metric,
			thickness_uom=self.thickness_uom,
			inverted_joints=bool(self.inverted_joints),
			catalogue=self.catalogue,
			line_number=int(self.line_number or 1),
			quantity=float(self.quantity or 1),
			width=self._parse("width_imperial") or 0.0,
			height=self._parse("height_imperial") or 0.0,
			frame_left=self._parse("frame_width_left_imperial") or 0.0,
			frame_right=self._parse("frame_width_right_imperial") or 0.0,
			frame_top=self._parse("frame_width_top_imperial") or 0.0,
			frame_bottom=self._parse("frame_width_bottom_imperial") or 0.0,
			custom_frame_widths=bool(self.custom_frame_widths),
			rails=[
				rules_mod.DividerInput(
					index=row.idx,
					centre=u.from_fraction(row.height_imperial),
					width=u.from_fraction(row.width_imperial),
				)
				for row in self.rails
			],
			stiles=[
				rules_mod.DividerInput(
					index=row.idx,
					centre=u.from_fraction(row.distance_imperial),
					width=u.from_fraction(row.width_imperial),
				)
				for row in self.stiles
			],
			hinge_qty=int(self.hinge_qty or 0),
			hinge_side=self.hinge_side,
			hinge_distance_from_edge=self.hinge_distance_from_edge or 0.0,
			panel_type=self.panel_type,
		)

	def apply_state(self, state: rules_mod.State, geo) -> None:
		"""Write derived values and any frame widths the collapse rule rewrote."""
		self.width_imperial = u.to_fraction(state.width)
		self.height_imperial = u.to_fraction(state.height)
		for side in ("left", "right", "top", "bottom"):
			inches = getattr(state, f"frame_{side}")
			self.set(f"frame_width_{side}_imperial", u.to_fraction(inches))
			self.set(f"frame_width_{side}_metric", round(u.inch_to_mm(inches), 1))

		# The collapse rule may have rewritten the members; reflect that in the
		# master field too, so the two never disagree on screen.
		if not self.custom_frame_widths:
			self.frame_width_imperial = u.to_fraction(state.frame_left)
			self.frame_width_metric = round(u.inch_to_mm(state.frame_left), 1)

		units = UNIT_CODE.get(self.units, self.units)
		self.inside_width_display = u.format_length(state.inside_width, units)
		self.inside_height_display = u.format_length(state.inside_height, units)
		self.horizontal_panels = geo.horizontal_panels
		self.vertical_panels = geo.vertical_panels
		self.total_panels = geo.total_panels
		self.configured_part_number = state.configured_part_number

		# Push the defaulted divider positions back into the visible rows.
		for row, divider in zip(self.rails, state.rails, strict=False):
			row.height_imperial = u.to_fraction(divider.centre)
			row.width_imperial = u.to_fraction(divider.width)
			row.height_metric = round(u.inch_to_mm(divider.centre or 0), 1)
			row.width_metric = round(u.inch_to_mm(divider.width or 0), 1)

		for row, divider in zip(self.stiles, state.stiles, strict=False):
			row.distance_imperial = u.to_fraction(divider.centre)
			row.width_imperial = u.to_fraction(divider.width)
			row.distance_metric = round(u.inch_to_mm(divider.centre or 0), 1)
			row.width_metric = round(u.inch_to_mm(divider.width or 0), 1)

	def build_details(self, state: rules_mod.State, geo) -> None:
		self.set("details", [])
		for line in details_mod.build(state, geo):
			self.append(
				"details",
				{
					"print_sequence": line.print_sequence,
					"description": line.description,
					"value": line.value,
					"visible": int(line.visible),
				},
			)

	def report(self, messages: list[rules_mod.Message]) -> None:
		"""Surface rule messages, honouring the ruleset's level split.

		Levels 1 and 2 block the save; level 4 is advisory -- notably the
		collapse warning, which fires *after* the frame widths have already
		been rewritten.
		"""
		self.messages = "\n".join(f"[{m.title}] {m.message}" for m in messages)

		blocking = [m for m in messages if m.blocking]
		for message in messages:
			if not message.blocking:
				frappe.msgprint(message.message, title=_(message.title), indicator="orange")

		if blocking:
			frappe.throw(
				"<br>".join(f"<b>{m.title}</b>: {m.message}" for m in blocking),
				title=_("Configuration Not Valid"),
			)


def _resize(doc, table: str, target: int) -> bool:
	"""Grow or shrink a divider table to ``target`` rows. Returns True if changed."""
	rows = doc.get(table) or []
	if len(rows) == target:
		return False

	while len(doc.get(table)) > target:
		doc.get(table).pop()
	while len(doc.get(table)) < target:
		doc.append(table, {})

	for idx, row in enumerate(doc.get(table), start=1):
		row.idx = idx
	return True


def _state_from_doc(doc) -> rules_mod.State | None:
	"""Snapshot of the previous save, for the ruleset's .PreviousValue checks."""
	if not doc:
		return None
	try:
		return doc.to_state()
	except Exception:
		# A previous revision that no longer parses must not block this save.
		return None


def lookup_part_number(state: rules_mod.State) -> str | None:
	"""Resolve against the stand-in X-IPNResolution matrix."""
	signature = f"{state.panel_type}|{state.inside_profile or ''}"
	return frappe.db.get_value(
		"Door Part Number Matrix",
		{"product": state.product, "panel_signature": signature, "disabled": 0},
		"part_number",
	)


@frappe.whitelist()
def recalculate(doc: str) -> dict:
	"""Live recalculation for the client script -- evaluates without saving.

	Returns the SVG, the messages and the derived values so the form can repaint
	as the operator types, which is what makes this read as a configurator.
	"""
	document = frappe.get_doc(frappe.parse_json(doc))
	document.flags.ignore_permissions = True

	try:
		document.sync_units()
		state = document.to_state()
		messages, geo = rules_mod.evaluate(state, matrix_lookup=lookup_part_number)
	except Exception as exc:
		return {"error": str(exc), "svg": "", "messages": []}

	return {
		"svg": preview_mod.render(state, geo),
		"messages": [
			{"level": m.level, "title": m.title, "message": m.message, "blocking": m.blocking}
			for m in messages
		],
		"part_number": state.configured_part_number,
		"inside_width": u.format_length(state.inside_width, state.units),
		"inside_height": u.format_length(state.inside_height, state.units),
		"total_panels": geo.total_panels,
		"horizontal_panels": geo.horizontal_panels,
		"vertical_panels": geo.vertical_panels,
		"rails": [
			{"centre": u.to_fraction(r.centre), "width": u.to_fraction(r.width)} for r in state.rails
		],
		"stiles": [
			{"centre": u.to_fraction(s.centre), "width": u.to_fraction(s.width)} for s in state.stiles
		],
	}


@frappe.whitelist()
def get_product_tiles() -> list[dict]:
	"""Artwork for the Product picker -- the row of large door tiles."""
	from poc.configurator import artwork

	return [
		{"value": "SQUARE", "label": "Square (90° Frame)", "svg": artwork.product_tile("SQUARE")},
		{"value": "MITRE", "label": "Mitre (45° Frame)", "svg": artwork.product_tile("MITRE")},
		{"value": "MDF", "label": "MDF", "svg": artwork.product_tile("MDF")},
		{"value": "SLAB", "label": "Slab", "svg": artwork.product_tile("SLAB")},
	]


@frappe.whitelist()
def get_profiles(profile_type: str, product: str | None = None) -> list[dict]:
	"""Options for the profile picker dialog, each with its drawn section.

	``product`` narrows the list the way the ruleset's ``OptionListGroup``
	expressions do -- MITRE and SQUARE do not share a moulding set.
	"""
	from poc.configurator import artwork

	filters = {"profile_type": profile_type, "disabled": 0}
	rows = frappe.get_all(
		"Door Profile",
		filters=filters,
		fields=["name", "shape", "product", "collapse", "reveal", "width"],
		order_by="name",
	)

	if product:
		rows = [r for r in rows if not r.product or r.product == product]

	kind = "outside" if profile_type == "Outside" else "inside"
	return [
		{
			"value": row.name,
			"label": row.name,
			"svg": artwork.profile_swatch(row.shape, kind),
			"detail": f"reveal {row.reveal}\"  ·  width {row.width}\"" if row.width else "",
		}
		for row in rows
	]


@frappe.whitelist()
def get_catalogue_items() -> list[dict]:
	"""Saved catalogue items for the "Select a Catalogue Item or CONFIGURE" field."""
	rows = frappe.get_all(
		"Door Configuration",
		filters={"is_preset": 1},
		fields=["name", "product", "configured_part_number"],
		order_by="name",
	)
	return [{"value": "CONFIGURE", "description": "Start a new configuration"}] + [
		{"value": r.name, "description": f"{r.product} · {r.configured_part_number or ''}"} for r in rows
	]


@frappe.whitelist()
def load_catalogue_item(catalogue: str) -> dict:
	"""Field values for a chosen catalogue item, for the client to apply.

	Returns the configuration only -- never the identity fields, so loading a
	catalogue item never renames or overwrites the document being edited.
	"""
	if not catalogue or catalogue == "CONFIGURE":
		return {}

	source = frappe.get_doc("Door Configuration", catalogue)
	skip = {
		"name",
		"configuration_name",
		"is_preset",
		"quotation",
		"details",
		"catalogue",
		"line_number",
		"quantity",
	}

	values = {
		key: value
		for key, value in source.as_dict().items()
		if key not in skip and not key.startswith("_") and not isinstance(value, list)
	}
	for std in ("owner", "creation", "modified", "modified_by", "docstatus", "idx", "doctype"):
		values.pop(std, None)

	values["rails"] = [
		{k: row.get(k) for k in ("height_imperial", "width_imperial", "height_metric", "width_metric")}
		for row in source.rails
	]
	values["stiles"] = [
		{k: row.get(k) for k in ("distance_imperial", "width_imperial", "distance_metric", "width_metric")}
		for row in source.stiles
	]
	return values
