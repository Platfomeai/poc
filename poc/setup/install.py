"""Seed the masters the configurator demo needs.

Idempotent -- safe to re-run.  Wired to ``after_install``; also runnable with
``bench --site demo execute poc.setup.install.execute``.

The species and profiles here stand in for the ruleset's external option lists.
Profile ``collapse`` / ``reveal`` values are chosen so the collapse rule
actually fires during the demo walkthrough rather than staying theoretical.
"""

import frappe

SPECIES = [
	# (name, group, rate per sq.ft. -- placeholder pricing)
	("Maple", "Frame", 42.00),
	("Red Oak", "Frame", 38.00),
	("White Oak", "Frame", 52.00),
	("Cherry", "Frame", 61.00),
	("Walnut", "Frame", 78.00),
	("Paint Grade Poplar", "Frame", 29.00),
	("MDF", "MDF", 22.00),
	("None", "CornerPegs", 0.00),
	("Hard Maple Pegs", "CornerPegs", 0.00),
]

PROFILES = [
	# Inside (panel) profiles -- names taken from the client's picker screens.
	# (name, type, product, shape, collapse, reveal, width, plateau, frame_width)
	("Shaker", "Inside", None, "shaker", 1.75, 0.25, 2.25, 0.00, 2.25),
	("22 Degree", "Inside", None, "22degree", 1.875, 0.3125, 2.375, 0.0625, 2.375),
	("Bead", "Inside", None, "bead", 1.875, 0.3125, 2.375, 0.0625, 2.375),
	("Cascade", "Inside", None, "cascade", 2.125, 0.375, 2.625, 0.125, 2.625),
	("Chamfer", "Inside", None, "chamfer", 2.00, 0.25, 2.50, 0.0625, 2.50),
	("Cove", "Inside", None, "cove", 2.125, 0.25, 2.625, 0.125, 2.625),
	("Half Shoulder", "Inside", None, "half_shoulder", 1.875, 0.25, 2.375, 0.0625, 2.375),
	("Ogee", "Inside", None, "ogee", 2.00, 0.375, 2.50, 0.125, 2.50),
	("Parklane Small Bevel 316", "Inside", None, "parklane", 2.0625, 0.1875, 2.5625, 0.0625, 2.5625),
	("Regency", "Inside", None, "regency", 2.25, 0.375, 2.75, 0.1875, 2.75),
	("Provincial", "Inside", "MITRE", "cascade", 2.50, 0.50, 3.00, 0.25, 3.00),
	("Mitre Classic", "Inside", "MITRE", "ogee", 2.25, 0.375, 2.75, 0.1875, 2.75),

	# Outside (edge) profiles.
	("None", "Outside", None, "square", 0.00, 0.00, 0.00, 0.00, 0.00),
	("22 Degree Edge", "Outside", None, "22degree", 0.00, 0.00, 0.1875, 0.00, 0.00),
	("Cambridge", "Outside", None, "cambridge", 0.00, 0.00, 0.25, 0.00, 0.00),
	("Chamfer Edge", "Outside", None, "chamfer", 0.00, 0.00, 0.1875, 0.00, 0.00),
	("Crown", "Outside", None, "crown", 0.00, 0.00, 0.375, 0.00, 0.00),
	("Curve", "Outside", None, "curve", 0.00, 0.00, 0.25, 0.00, 0.00),
	("Double Shoulder", "Outside", None, "double_shoulder", 0.00, 0.00, 0.3125, 0.00, 0.00),
	("Ellipse", "Outside", None, "ellipse", 0.00, 0.00, 0.3125, 0.00, 0.00),
	("Roundover", "Outside", None, "roundover", 0.00, 0.00, 0.125, 0.00, 0.00),
	("Bevel", "Outside", None, "bevel", 0.00, 0.00, 0.25, 0.00, 0.00),
]

#: Stand-in rows for the external X-IPNResolution matrix.  Anything not matched
#: here falls through to "CUSTOM-<Product>", exactly as the real ruleset does.
PART_NUMBERS = [
	("SQUARE", "Raised|Shaker", "JS-SQ-SHK-RSD"),
	("SQUARE", "Recessed|Shaker", "JS-SQ-SHK-REC"),
	("MITRE", "Raised|Mitre Classic", "JS-MI-CLS-RSD"),
]

PRESETS = [
	{
		"configuration_name": "104 Shaker",
		"product": "SQUARE",
		"door_type": "Door",
		"units": "Imperial",
		"panel_type": "Recessed",
		"frame_species": "Maple",
		"panel_species": "Maple",
		"outside_profile": "None",
		"inside_profile": "Shaker",
		"width_imperial": "24",
		"height_imperial": "30",
		"frame_width_imperial": "2 1/4",
		"hinge_qty": 2,
		"corner_pegs": "None",
		"hinge_side": "Left",
		"hinge_distance_from_edge": 5,
		"is_preset": 1,
	},
	{
		"configuration_name": "212 Two Rail Pantry",
		"product": "SQUARE",
		"door_type": "Door",
		"units": "Imperial",
		"panel_type": "Raised",
		"frame_species": "Cherry",
		"panel_species": "Cherry",
		"outside_profile": "Roundover",
		"inside_profile": "Ogee",
		"width_imperial": "18",
		"height_imperial": "42",
		"frame_width_imperial": "2 1/2",
		"rail_dividers": 2,
		"hinge_qty": 3,
		"corner_pegs": "None",
		"hinge_side": "Left",
		"hinge_distance_from_edge": 6,
		"is_preset": 1,
	},
	{
		"configuration_name": "330 Mitre Drawer Front",
		"product": "MITRE",
		"door_type": "Drawer Front",
		"units": "Imperial",
		"panel_type": "Raised",
		"frame_species": "Walnut",
		"panel_species": "Walnut",
		"outside_profile": "Chamfer Edge",
		"inside_profile": "Mitre Classic",
		"width_imperial": "30",
		"height_imperial": "6",
		"frame_width_imperial": "1 3/4",
		"hinge_qty": 2,
		"corner_pegs": "None",
		"hinge_side": "Left",
		"hinge_distance_from_edge": 5,
		"is_preset": 1,
	},
]


def after_install():
	execute()


def execute():
	seed_species()
	seed_profiles()
	seed_part_numbers()
	seed_presets()
	frappe.db.commit()


def seed_species():
	for name, group, rate in SPECIES:
		if frappe.db.exists("Door Species", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Door Species",
				"species_name": name,
				"species_group": group,
				"rate_per_sqft": rate,
			}
		).insert(ignore_permissions=True)


def seed_profiles():
	for name, ptype, product, shape, collapse, reveal, width, plateau, frame_width in PROFILES:
		if frappe.db.exists("Door Profile", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Door Profile",
				"profile_name": name,
				"profile_type": ptype,
				"product": product,
				"shape": shape,
				"collapse": collapse,
				"reveal": reveal,
				"width": width,
				"plateau": plateau,
				"frame_width": frame_width,
			}
		).insert(ignore_permissions=True)


def seed_part_numbers():
	for product, signature, part_number in PART_NUMBERS:
		if frappe.db.exists("Door Part Number Matrix", {"product": product, "panel_signature": signature}):
			continue
		frappe.get_doc(
			{
				"doctype": "Door Part Number Matrix",
				"product": product,
				"panel_signature": signature,
				"part_number": part_number,
			}
		).insert(ignore_permissions=True)


def seed_presets():
	for preset in PRESETS:
		if frappe.db.exists("Door Configuration", preset["configuration_name"]):
			continue
		doc = frappe.get_doc(dict(doctype="Door Configuration", **preset))
		doc.insert(ignore_permissions=True)
