"""Inline SVG rendering of the configured door.

No libraries and no external assets -- the markup goes straight into the
``preview`` HTML field on Door Configuration and is repainted on every
debounced change, which is what makes the form read as a configurator rather
than a data-entry screen.

Colours come from Frappe's CSS custom properties so the drawing follows the
desk theme in both light and dark mode.
"""

from xml.sax.saxutils import escape

from poc.configurator import geometry as geo_mod
from poc.configurator import rules as rules_mod
from poc.configurator import units as u

CANVAS = 420.0
MARGIN = 46.0


def render(state: "rules_mod.State", geo: "geo_mod.DoorGeometry") -> str:
	if not geo.width or not geo.height:
		return _empty("Enter a width and height to see the door.")

	scale = min((CANVAS - 2 * MARGIN) / geo.width, (CANVAS - 2 * MARGIN) / geo.height)
	draw_w = geo.width * scale
	draw_h = geo.height * scale
	origin_x = (CANVAS - draw_w) / 2
	origin_y = (CANVAS - draw_h) / 2

	def x(inches: float) -> float:
		return origin_x + inches * scale

	def y(inches: float) -> float:
		"""Flip the Y axis: the model measures up from the bottom, SVG measures down."""
		return origin_y + draw_h - inches * scale

	parts: list[str] = [
		f'<svg viewBox="0 0 {CANVAS:.0f} {CANVAS:.0f}" width="100%" '
		'style="max-width:460px;font-family:var(--font-stack,sans-serif)" '
		'xmlns="http://www.w3.org/2000/svg">',
		"<style>"
		".door-frame{fill:var(--bg-color,#fff);stroke:var(--text-color,#1f272e);stroke-width:1.5}"
		".door-panel{fill:var(--control-bg,#f4f5f6);stroke:var(--border-color,#d1d8dd);stroke-width:1}"
		".door-divider{fill:var(--bg-light-gray,#e2e6e9);stroke:var(--text-color,#1f272e);stroke-width:1}"
		".door-label{fill:var(--text-muted,#8d99a6);font-size:10px;text-anchor:middle;"
		"dominant-baseline:middle}"
		".door-dim{fill:var(--text-muted,#8d99a6);font-size:11px;text-anchor:middle}"
		".door-hinge{fill:var(--text-color,#1f272e)}"
		"</style>",
	]

	# Outer frame.
	parts.append(
		f'<rect class="door-frame" x="{x(0):.2f}" y="{y(geo.height):.2f}" '
		f'width="{draw_w:.2f}" height="{draw_h:.2f}" rx="2"/>'
	)

	# Panel cells.
	for panel in geo.panels:
		parts.append(
			f'<rect class="door-panel" x="{x(panel.left):.2f}" y="{y(panel.top):.2f}" '
			f'width="{panel.width * scale:.2f}" height="{panel.height * scale:.2f}"/>'
		)
		if panel.width * scale > 24 and panel.height * scale > 16:
			parts.append(
				f'<text class="door-label" x="{x(panel.left + panel.width / 2):.2f}" '
				f'y="{y(panel.bottom + panel.height / 2):.2f}">P{panel.number}</text>'
			)

	# Divider bars.
	for rail in geo.rails:
		parts.append(
			f'<rect class="door-divider" x="{x(geo.frame_left):.2f}" y="{y(rail.high):.2f}" '
			f'width="{geo.inside_width * scale:.2f}" height="{rail.width * scale:.2f}"/>'
		)
	for stile in geo.stiles:
		parts.append(
			f'<rect class="door-divider" x="{x(stile.low):.2f}" '
			f'y="{y(geo.height - geo.frame_top):.2f}" '
			f'width="{stile.width * scale:.2f}" height="{geo.inside_height * scale:.2f}"/>'
		)

	parts.extend(_hinges(state, geo, x, y, scale))

	# Dimension callouts.
	parts.append(
		f'<text class="door-dim" x="{CANVAS / 2:.2f}" y="{y(geo.height) - 14:.2f}">'
		f"{escape(u.format_length(geo.width, state.units))}</text>"
	)
	parts.append(
		f'<text class="door-dim" x="{x(0) - 22:.2f}" y="{CANVAS / 2:.2f}" '
		f'transform="rotate(-90 {x(0) - 22:.2f} {CANVAS / 2:.2f})">'
		f"{escape(u.format_length(geo.height, state.units))}</text>"
	)

	parts.append("</svg>")
	return "".join(parts)


def _hinges(state, geo, x, y, scale) -> list[str]:
	"""Hinge markers on the selected side, inset by hinge_distance_from_edge."""
	qty = int(state.hinge_qty or 0)
	if qty <= 0:
		return []

	inset = state.hinge_distance_from_edge or 0
	usable = geo.height - 2 * inset
	if usable <= 0:
		return []

	on_left = state.hinge_side == "Left"
	centre_x = x(geo.frame_left / 2) if on_left else x(geo.width - geo.frame_right / 2)

	markers = []
	for i in range(qty):
		# Evenly distribute between the two inset limits.
		fraction = 0.5 if qty == 1 else i / (qty - 1)
		cy = y(inset + usable * fraction)
		markers.append(
			f'<rect class="door-hinge" x="{centre_x - 3:.2f}" y="{cy - 7:.2f}" '
			f'width="6" height="14" rx="1.5"/>'
		)
	return markers


def _empty(message: str) -> str:
	return (
		'<div style="padding:2rem;text-align:center;color:var(--text-muted,#8d99a6);'
		f'font-size:12px">{escape(message)}</div>'
	)
