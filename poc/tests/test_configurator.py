"""Unit tests for the pure configurator modules.

These need no site, no database and no Frappe bootstrap -- the modules under
test are deliberately free of framework imports so the rule math can be
exercised directly:

	bench --site demo run-tests --app poc
	python -m unittest poc.tests.test_configurator
"""

import unittest

from poc.configurator import geometry, ranges, rules
from poc.configurator import units as u


class TestUnits(unittest.TestCase):
	def test_fraction_round_trip(self):
		for text, value in (
			("24 3/16", 24.1875),
			("3/16", 0.1875),
			("24", 24.0),
			('12 1/2"', 12.5),
			("-2 1/4", -2.25),
		):
			self.assertAlmostEqual(u.from_fraction(text), value, msg=text)
			self.assertEqual(u.to_fraction(value), text.rstrip('"'), msg=text)

	def test_fraction_reduces(self):
		self.assertEqual(u.to_fraction(12.5), "12 1/2")  # 8/16 -> 1/2
		self.assertEqual(u.to_fraction(2.25), "2 1/4")  # 4/16 -> 1/4
		self.assertEqual(u.to_fraction(3.0), "3")  # no zero numerator

	def test_fraction_snaps_to_sixteenths(self):
		self.assertEqual(u.to_fraction(24.19), "24 3/16")

	def test_blank_and_bad_input(self):
		self.assertIsNone(u.from_fraction(""))
		self.assertIsNone(u.from_fraction(None))
		with self.assertRaises(ValueError):
			u.from_fraction("wide-ish")
		with self.assertRaises(ValueError):
			u.from_fraction("1/0")

	def test_metric_conversion(self):
		self.assertAlmostEqual(u.inch_to_mm(1), 25.4)
		self.assertAlmostEqual(u.mm_to_inch(25.4), 1.0)
		self.assertAlmostEqual(u.mm_to_inch(u.inch_to_mm(24.1875)), 24.1875)

	def test_sixteenth_boundary_survives_metric_round_trip(self):
		"""A 1/16" value must come back as the same fraction after mm rounding."""
		for sixteenths in range(1, 16):
			inches = 24 + sixteenths / 16
			mm = round(u.inch_to_mm(inches), 1)
			self.assertEqual(u.to_fraction(u.mm_to_inch(mm)), u.to_fraction(inches))


class TestRanges(unittest.TestCase):
	def test_snap_to_increment(self):
		self.assertAlmostEqual(ranges.FRAME_WIDTH_IMPERIAL.snap(2.03), 2.0)  # nearer 2
		self.assertAlmostEqual(ranges.FRAME_WIDTH_IMPERIAL.snap(2.05), 2.0625)  # nearer 2 1/16
		self.assertAlmostEqual(ranges.PANEL_IMPERIAL.snap(24.19), 24.1875)

	def test_clamp(self):
		self.assertEqual(ranges.DIVIDERS.clamp(9), 3)
		self.assertEqual(ranges.DIVIDERS.clamp(-2), 0)

	def test_contains(self):
		self.assertTrue(ranges.HINGE_QTY.contains(3))
		self.assertFalse(ranges.HINGE_QTY.contains(5))
		self.assertFalse(ranges.HINGE_QTY.contains(None))


class TestGeometry(unittest.TestCase):
	def test_panel_counts_for_every_divider_combination(self):
		for rails in range(4):
			for stiles in range(4):
				geo = geometry.build(
					24,
					30,
					2,
					2,
					2,
					2,
					rails=[
						geometry.Divider(i, c, 2)
						for i, c in enumerate(geometry.default_rail_centres(30, rails), 1)
					],
					stiles=[
						geometry.Divider(i, c, 2)
						for i, c in enumerate(geometry.default_stile_centres(24, stiles), 1)
					],
				)
				self.assertEqual(geo.vertical_panels, rails + 1)
				self.assertEqual(geo.horizontal_panels, stiles + 1)
				self.assertEqual(geo.total_panels, (rails + 1) * (stiles + 1))
				self.assertEqual(len(geo.panels), geo.total_panels)

	def test_max_grid_is_sixteen_panels(self):
		geo = geometry.build(
			24,
			30,
			2,
			2,
			2,
			2,
			rails=[geometry.Divider(i, c, 1) for i, c in enumerate(geometry.default_rail_centres(30, 3), 1)],
			stiles=[geometry.Divider(i, c, 1) for i, c in enumerate(geometry.default_stile_centres(24, 3), 1)],
		)
		self.assertEqual(geo.total_panels, 16)

	def test_panels_tile_the_opening(self):
		"""Panel areas plus divider bars must account for the whole opening."""
		geo = geometry.build(
			24, 30, 2, 2, 2, 2, rails=[geometry.Divider(1, 15, 2)], stiles=[geometry.Divider(1, 12, 2)]
		)
		panel_area = sum(p.width * p.height for p in geo.panels)
		opening = geo.inside_width * geo.inside_height
		bars = 2 * geo.inside_width + 2 * geo.inside_height - 2 * 2  # minus the crossing
		self.assertAlmostEqual(panel_area + bars, opening, places=6)

	def test_default_spacing_is_even(self):
		self.assertEqual(geometry.default_rail_centres(30, 2), [20.0, 10.0])
		self.assertEqual(geometry.default_stile_centres(24, 3), [6.0, 12.0, 18.0])
		self.assertEqual(geometry.default_rail_centres(30, 0), [])

	def test_panel_numbering_starts_top_left(self):
		geo = geometry.build(24, 30, 2, 2, 2, 2, rails=[geometry.Divider(1, 15, 2)])
		self.assertEqual(geo.panels[0].number, 1)
		self.assertGreater(geo.panels[0].bottom, geo.panels[1].bottom)


def _state(**kw):
	base = dict(
		width=24, height=30, frame_left=2, frame_right=2, frame_top=2, frame_bottom=2
	)
	base.update(kw)
	return rules.State(**base)


class TestCollapse(unittest.TestCase):
	"""The accumulator at XML:1960 -- each +0.25 trigger, independently."""

	def test_no_collapse_when_panel_is_big_enough(self):
		state = _state()
		self.assertEqual(rules.apply_collapse(state), [])
		self.assertFalse(state.collapse_applied)
		self.assertEqual(state.frame_left, 2)

	def test_exactly_minimum_panel_size_does_not_collapse(self):
		"""The test is ``< MinimumPanelSize``, so 3.0" exactly is still valid."""
		state = _state(height=8, frame_top=2.5, frame_bottom=2.5)
		self.assertEqual(state.height - 5, 3.0)
		self.assertEqual(rules.apply_collapse(state), [])
		self.assertFalse(state.collapse_applied)

	def test_door_base_is_1_75(self):
		state = _state(height=7, door_type="Door", frame_top=2.5, frame_bottom=2.5)
		rules.apply_collapse(state)
		self.assertTrue(state.collapse_applied)
		self.assertEqual(state.frame_left, 1.75)

	def test_drawer_front_base_is_1_50(self):
		state = _state(height=7, door_type="DrawerFront", frame_top=2.5, frame_bottom=2.5)
		rules.apply_collapse(state)
		self.assertEqual(state.frame_left, 1.5)

	def test_drawer_front_wide_left_frame_adds_quarter(self):
		state = _state(height=7, door_type="DrawerFront", frame_left=3.0, frame_top=2.5, frame_bottom=2.5)
		rules.apply_collapse(state)
		self.assertEqual(state.frame_left, 1.75)

	def test_top_frame_over_3_75_adds_quarter(self):
		state = _state(height=10, door_type="Door", frame_top=4.0, frame_bottom=4.0)
		rules.apply_collapse(state)
		self.assertEqual(state.frame_top, 2.0)

	def test_top_frame_over_4_75_adds_both_quarters(self):
		state = _state(height=12, door_type="Door", frame_top=5.0, frame_bottom=5.0)
		rules.apply_collapse(state)
		self.assertEqual(state.frame_top, 2.25)

	def test_warning_only_on_transition(self):
		"""``.PreviousValue`` gate: a re-save of an already-collapsed door is quiet."""
		state = _state(height=7, frame_top=2.5, frame_bottom=2.5)
		self.assertEqual(len(rules.apply_collapse(state)), 1)

		previous = _state(height=7, frame_top=2.5, frame_bottom=2.5)
		previous.collapse_applied = True
		again = _state(height=7, frame_top=2.5, frame_bottom=2.5)
		self.assertEqual(rules.apply_collapse(again, previous=previous), [])


class TestHinges(unittest.TestCase):
	def test_open_panel_below_minimum_is_blocking(self):
		state = _state(panel_type="Open Panel", frame_left=1.5, hinge_side="Left")
		messages = rules.validate_hinges(state)
		self.assertTrue(any(m.blocking for m in messages))

	def test_solid_panel_is_exempt(self):
		"""The source gates the hinge rule on PanelType = "Open Panel"."""
		state = _state(panel_type="Raised", frame_left=1.5)
		self.assertEqual(rules.validate_hinges(state), [])

	def test_rule_follows_the_hinge_side(self):
		state = _state(panel_type="Open Panel", frame_left=1.5, frame_right=3, hinge_side="Right")
		self.assertEqual(rules.validate_hinges(state), [])

	def test_hinge_qty_range(self):
		self.assertTrue(rules.validate_hinges(_state(hinge_qty=9)))


class TestDividerValidation(unittest.TestCase):
	def _rails(self, *pairs):
		return [rules.DividerInput(index=i, centre=c, width=w) for i, (c, w) in enumerate(pairs, 1)]

	def test_clear_dividers_pass(self):
		state = _state(rails=self._rails((20, 2), (10, 2)))
		self.assertEqual(rules.validate_dividers(state), [])

	def test_divider_buried_in_bottom_frame(self):
		state = _state(rails=self._rails((2.5, 2)))  # low edge at 1.5, frame at 2
		self.assertTrue(rules.validate_dividers(state))

	def test_divider_touching_the_frame_is_allowed(self):
		state = _state(rails=self._rails((3.0, 2)))  # low edge exactly at the frame
		self.assertEqual(rules.validate_dividers(state), [])

	def test_overlapping_dividers(self):
		state = _state(rails=self._rails((20, 2), (19, 2)))
		self.assertTrue(any("overlap" in m.message.lower() for m in rules.validate_dividers(state)))

	def test_adjacent_dividers_just_touching_are_allowed(self):
		state = _state(rails=self._rails((20, 2), (18, 2)))
		self.assertEqual(rules.validate_dividers(state), [])

	def test_incomplete_rows_are_skipped(self):
		state = _state(rails=[rules.DividerInput(index=1)])
		self.assertEqual(rules.validate_dividers(state), [])


class TestPartNumber(unittest.TestCase):
	def test_falls_back_to_custom(self):
		state = _state(product="MITRE")
		rules.resolve_part_number(state)
		self.assertEqual(state.configured_part_number, "CUSTOM-MITRE")

	def test_uses_matrix_when_it_resolves(self):
		state = _state(product="SQUARE")
		rules.resolve_part_number(state, matrix_lookup=lambda s: "JS-SQ-SHK-RSD")
		self.assertEqual(state.configured_part_number, "JS-SQ-SHK-RSD")

	def test_mismatched_panels_force_custom(self):
		"""The Exception check: any panel differing from panel 1 forces CUSTOM-."""
		state = _state(product="SQUARE", panel_signatures=[("Raised", "A"), ("Recessed", "A")])
		rules.resolve_part_number(state, matrix_lookup=lambda s: "JS-SQ-SHK-RSD")
		self.assertEqual(state.configured_part_number, "CUSTOM-SQUARE")

	def test_uniform_panels_still_resolve(self):
		state = _state(product="SQUARE", panel_signatures=[("Raised", "A"), ("Raised", "A")])
		rules.resolve_part_number(state, matrix_lookup=lambda s: "JS-SQ-SHK-RSD")
		self.assertEqual(state.configured_part_number, "JS-SQ-SHK-RSD")


class TestDetails(unittest.TestCase):
	def test_sequence_is_monotonic_and_ends_with_part_number(self):
		from poc.configurator import details

		state = _state(rails=[rules.DividerInput(1, 15, 2)])
		messages, geo = rules.evaluate(state)
		lines = details.build(state, geo)

		seqs = [line.print_sequence for line in lines]
		self.assertEqual(seqs, sorted(seqs))
		self.assertEqual(lines[-1].description, "Configured Part Number")

	def test_blank_values_are_dropped(self):
		from poc.configurator import details

		state = _state()
		messages, geo = rules.evaluate(state)
		lines = details.build(state, geo)
		# frame_species is unset, so no such line should be emitted
		self.assertNotIn("Frame Species", [line.description for line in lines])


class TestPreview(unittest.TestCase):
	def test_renders_svg(self):
		from poc.configurator import preview

		state = _state(rails=[rules.DividerInput(1, 15, 2)])
		messages, geo = rules.evaluate(state)
		svg = preview.render(state, geo)
		self.assertTrue(svg.startswith("<svg"))
		self.assertIn("door-panel", svg)

	def test_empty_door_is_handled(self):
		from poc.configurator import preview

		state = rules.State()
		messages, geo = rules.evaluate(state)
		self.assertNotIn("<svg", preview.render(state, geo))


if __name__ == "__main__":
	unittest.main()
