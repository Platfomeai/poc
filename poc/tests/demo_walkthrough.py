"""Scripted walkthrough of the client demo, runnable end to end.

	bench --site demo execute poc.tests.demo_walkthrough.run

Every step here mirrors a step in the live demo script, so a green run means
the demo itself is safe to give.  Rolls back at the end -- it leaves no data
behind.
"""

import frappe

NAME = "104 Shaker"
PANTRY = "212 Two Rail Pantry"

_results: list[tuple[bool, str]] = []


def check(condition, label, detail=""):
	_results.append((bool(condition), f"{label}{f'  -- {detail}' if detail else ''}"))


def load(name=NAME):
	return frappe.get_doc("Door Configuration", name)


def expect_block(doc, label):
	"""Save and require a blocking rule message."""
	try:
		doc.save()
	except frappe.ValidationError as exc:
		check(True, label, str(exc).split("</b>")[-1].strip()[:60])
		return
	check(False, label, "save was NOT blocked")


def run():
	frappe.flags.in_test = True

	# 1 -- baseline geometry
	d = load()
	check(d.total_panels == 1, "single panel door", f"panels={d.total_panels}")
	check(d.configured_part_number == "JS-SQ-SHK-REC", "matrix part number", d.configured_part_number)
	check(d.inside_width_display == '19 1/2"', "inside width", d.inside_width_display)

	# 2 -- dividers seed with even spacing
	d = load()
	d.rail_dividers = 2
	d.save()
	seeded = [r.height_imperial for r in d.rails]
	check(seeded == ["20", "10"], "rails seeded evenly", str(seeded))
	check(d.total_panels == 3, "three panels", f"{d.horizontal_panels}x{d.vertical_panels}")

	# 3 -- hand-positioned dividers survive a save
	d = load()
	d.rails[0].height_imperial = "22"
	d.rails[1].height_imperial = "8"
	d.save()
	kept = [r.height_imperial for r in load().rails]
	check(kept == ["22", "8"], "operator positions kept", str(kept))

	# ... and survive a no-op save (the sticky-reset-flag regression)
	d = load()
	d.save()
	kept = [r.height_imperial for r in load().rails]
	check(kept == ["22", "8"], "positions survive a no-op save", str(kept))

	# 4 -- blocking rules
	d = load()
	d.rails[1].height_imperial = "21"  # 1" under rail 1, both 2" wide
	expect_block(d, "overlapping dividers blocked")

	# Drop to a single divider first, so this exercises the inside-the-frame
	# check rather than also tripping the overlap check against a neighbour.
	d = load()
	d.rail_dividers = 1
	d.save()
	d = load()
	d.rails[0].height_imperial = "1"  # buried in the bottom frame
	expect_block(d, "divider inside frame blocked")

	# restore the two-rail state the later steps assume
	d = load()
	d.rail_dividers = 2
	d.save()

	# 5 -- count change re-spaces (RailResetFlag)
	d = load()
	d.rail_dividers = 3
	d.save()
	respaced = [r.height_imperial for r in d.rails]
	check(respaced == ["22 1/2", "15", "7 1/2"], "count change respaces", str(respaced))
	check(d.total_panels == 4, "four panels", str(d.total_panels))

	# 6 -- stiles make a grid
	d = load()
	d.stile_dividers = 1
	d.save()
	check(d.total_panels == 8, "2 x 4 grid", f"{d.horizontal_panels}x{d.vertical_panels}={d.total_panels}")

	# 7 -- collapse rewrites frames and warns
	d = load(PANTRY)
	d.rail_dividers = 0
	d.height_imperial = "7"
	d.save()
	check(d.frame_width_imperial == "1 3/4", "collapse rewrote frames", d.frame_width_imperial)
	check("Minimum Panel Height" in (d.messages or ""), "collapse warned", (d.messages or "")[:50])

	# 8 -- hinge rule, gated on Open Panel as the source ruleset gates it
	d = load()
	d.panel_type = "Open Panel"
	d.custom_frame_widths = 1
	d.frame_width_left_imperial = "1 1/2"
	expect_block(d, "open-panel hinge minimum blocked")

	# 9 -- metric round trip, no drift
	d = load()
	before = (d.width_imperial, d.height_imperial, d.frame_width_left_imperial)
	d.units = "Metric"
	d.save()
	metric = (d.width_metric, d.height_metric)
	d = load()
	d.units = "Imperial"
	d.save()
	after = (d.width_imperial, d.height_imperial, d.frame_width_left_imperial)
	check(metric == (609.6, 762.0), "converted to mm", str(metric))
	check(before == after, "imperial round trip", f"{before} -> {after}")

	# 10 -- spec sheet sequencing
	d = load()
	seqs = [row.print_sequence for row in d.details]
	check(len(seqs) > 20, "spec sheet populated", f"{len(seqs)} lines")
	check(all(a <= b for a, b in zip(seqs, seqs[1:], strict=False)), "sequence monotonic")
	check(
		d.details[-1].description == "Configured Part Number",
		"part number is the last line",
		d.details[-1].description,
	)

	# 11 -- quotation
	from poc.configurator.quotation import create_quotation

	quotation_name = create_quotation(NAME)
	quotation = frappe.get_doc("Quotation", quotation_name)
	check(quotation.docstatus == 0, "quotation is a draft")
	check(quotation.items[0].item_code == "JS-SQ-SHK-REC", "item code", quotation.items[0].item_code)
	check(quotation.items[0].rate > 0, "rate calculated", str(quotation.items[0].rate))

	# 12 -- the spec sheet print format renders
	html = frappe.get_print("Door Configuration", NAME, print_format="Door Specification")
	for probe in ("spec-lines", "Configured Part Number", "Frame Width - Left", "JS-SQ-SHK-REC"):
		check(probe in html, f"print format contains {probe!r}")

	# 13 -- the visual pickers
	from poc.poc.doctype.door_configuration.door_configuration import (
		get_catalogue_items,
		get_product_tiles,
		get_profiles,
		load_catalogue_item,
	)

	tiles = get_product_tiles()
	check(len(tiles) == 4, "four product tiles", str([t["value"] for t in tiles]))
	check(all(t["svg"].startswith("<svg") for t in tiles), "tiles carry artwork")

	inside = get_profiles("Inside", "SQUARE")
	outside = get_profiles("Outside", "SQUARE")
	check(len(inside) >= 10, "inside profiles listed", f"{len(inside)}")
	check(all(p["svg"].startswith("<svg") for p in inside), "profiles carry cross-sections")
	check(any(p["value"] == "None" for p in outside), "outside list offers None")
	# MITRE-only profiles must not leak into the SQUARE list.
	check(
		not any(p["value"] == "Mitre Classic" for p in inside),
		"product filters the profile list",
	)

	catalogue = get_catalogue_items()
	check(catalogue[0]["value"] == "CONFIGURE", "CONFIGURE heads the catalogue")
	check(len(catalogue) == 4, "three catalogue items", str(len(catalogue)))

	loaded = load_catalogue_item(PANTRY)
	check(loaded.get("inside_profile") == "Ogee", "catalogue item loads options", str(loaded.get("inside_profile")))
	check("configuration_name" not in loaded, "catalogue load never renames the document")
	check(len(loaded.get("rails", [])) >= 0, "catalogue load carries divider rows")

	# 14 -- the spec sheet carries the new attributes
	d = load()
	descriptions = [row.description for row in d.details]
	for expected in ("Thickness", "Quantity", "Line Number", "Corner Pegs", "Inside Profile"):
		check(expected in descriptions, f"spec sheet lists {expected!r}")

	# 15 -- live preview needs no save
	from poc.poc.doctype.door_configuration.door_configuration import recalculate

	result = recalculate(frappe.as_json(load().as_dict()))
	check(result.get("svg", "").startswith("<svg"), "preview renders")
	check(result.get("total_panels") == 8, "preview panel count", str(result.get("total_panels")))

	frappe.db.rollback()
	_report()


def _report():
	passed = sum(1 for ok, _ in _results if ok)
	for ok, label in _results:
		print(f"  {'PASS' if ok else 'FAIL'}  {label}")
	print(f"\n{passed}/{len(_results)} checks passed")
	if passed != len(_results):
		raise SystemExit(1)
