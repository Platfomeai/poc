"""Procedurally drawn SVG artwork for the configurator's visual pickers.

The client's Design Studio screens lean heavily on imagery: the Product step is
a row of large door tiles, and every profile field opens a grid of machined
cross-sections.  We were not given those assets, so everything here is drawn
from scratch -- close enough in character to read as the same product, without
borrowing their artwork.

Two families:

* ``product_tile(product)``  -- a face-on cabinet door, one per product line.
* ``profile_swatch(shape, kind)`` -- a machined edge in section, the way a
  millwork catalogue draws it.  ``kind="inside"`` carries the panel groove and
  tongue; ``kind="outside"`` is just the shaped outer edge.
"""

from xml.sax.saxutils import escape

# Warm timber tones; the outside/inside swatches share them so a grid of mixed
# profiles still reads as one set.
WOOD_LIGHT = "#f0dcc0"
WOOD_MID = "#e3c9a4"
WOOD_DARK = "#c9a97c"
WOOD_EDGE = "#a8845a"
PAINT_LIGHT = "#fbfbfb"
PAINT_MID = "#eef0f1"
PAINT_EDGE = "#c8ced2"


# ---------------------------------------------------------------------------
# Profile cross-sections
# ---------------------------------------------------------------------------

# Section geometry. The stock runs left to right; the machined detail sits on
# the top-right corner, and an inside profile then steps down to a tongue.
TOP_Y = 14.0
BOTTOM_Y = 66.0
LEFT_X = 6.0
BODY_RIGHT = 138.0
TONGUE_RIGHT = 192.0
TONGUE_TOP = 44.0
TONGUE_BOTTOM = 58.0


def _edge(shape: str, x1: float, y1: float) -> str:
	"""Path fragment from the top edge down to (``x1``, ``y1``).

	Each entry starts at some point on the top edge and must finish exactly at
	(x1, y1) so the outline closes cleanly whatever the shape.
	"""
	w = 34.0  # how far back along the top edge the detail reaches
	x0 = x1 - w

	shapes = {
		# A plain square edge: straight along, straight down.
		"square": f"L {x1:.1f},{TOP_Y:.1f} L {x1:.1f},{y1:.1f}",
		# Straight bevels.
		"chamfer": f"L {x0:.1f},{TOP_Y:.1f} L {x1:.1f},{y1:.1f}",
		"22degree": f"L {x0 + 12:.1f},{TOP_Y:.1f} L {x1:.1f},{y1 - 10:.1f} L {x1:.1f},{y1:.1f}",
		"bevel": f"L {x0 + 6:.1f},{TOP_Y:.1f} L {x1:.1f},{y1 - 4:.1f} L {x1:.1f},{y1:.1f}",
		# Convex curves.
		"roundover": (
			f"L {x0 + 10:.1f},{TOP_Y:.1f} "
			f"Q {x1:.1f},{TOP_Y:.1f} {x1:.1f},{y1:.1f}"
		),
		"crown": (
			f"L {x0 + 4:.1f},{TOP_Y:.1f} "
			f"C {x0 + 20:.1f},{TOP_Y - 1:.1f} {x1 - 4:.1f},{TOP_Y + 8:.1f} {x1:.1f},{y1:.1f}"
		),
		"curve": f"L {x0 + 8:.1f},{TOP_Y:.1f} Q {x1 - 2:.1f},{TOP_Y + 4:.1f} {x1:.1f},{y1:.1f}",
		"ellipse": (
			f"L {x0 + 2:.1f},{TOP_Y:.1f} "
			f"C {x0 + 22:.1f},{TOP_Y:.1f} {x1:.1f},{TOP_Y + 12:.1f} {x1:.1f},{y1:.1f}"
		),
		# Concave.
		"cove": f"L {x0 + 10:.1f},{TOP_Y:.1f} Q {x0 + 10:.1f},{y1:.1f} {x1:.1f},{y1:.1f}",
		# Ogee: the classic S, convex into concave.
		"ogee": (
			f"L {x0:.1f},{TOP_Y:.1f} "
			f"C {x0 + 14:.1f},{TOP_Y:.1f} {x0 + 8:.1f},{y1 - 6:.1f} {x0 + 22:.1f},{y1 - 6:.1f} "
			f"L {x1:.1f},{y1 - 6:.1f} L {x1:.1f},{y1:.1f}"
		),
		# Bead: a half-round proud of the face.
		"bead": (
			f"L {x0 + 4:.1f},{TOP_Y:.1f} "
			f"A 9,9 0 1 1 {x0 + 22:.1f},{TOP_Y:.1f} "
			f"L {x1:.1f},{TOP_Y:.1f} L {x1:.1f},{y1:.1f}"
		),
		# Stepped shoulders.
		"half_shoulder": (
			f"L {x0 + 8:.1f},{TOP_Y:.1f} L {x0 + 8:.1f},{TOP_Y + 14:.1f} "
			f"L {x1:.1f},{TOP_Y + 14:.1f} L {x1:.1f},{y1:.1f}"
		),
		"double_shoulder": (
			f"L {x0:.1f},{TOP_Y:.1f} L {x0:.1f},{TOP_Y + 9:.1f} "
			f"L {x0 + 17:.1f},{TOP_Y + 9:.1f} L {x0 + 17:.1f},{TOP_Y + 18:.1f} "
			f"L {x1:.1f},{TOP_Y + 18:.1f} L {x1:.1f},{y1:.1f}"
		),
		"cascade": (
			f"L {x0:.1f},{TOP_Y:.1f} L {x0:.1f},{TOP_Y + 7:.1f} "
			f"L {x0 + 11:.1f},{TOP_Y + 7:.1f} L {x0 + 11:.1f},{TOP_Y + 14:.1f} "
			f"L {x0 + 22:.1f},{TOP_Y + 14:.1f} L {x0 + 22:.1f},{TOP_Y + 21:.1f} "
			f"L {x1:.1f},{TOP_Y + 21:.1f} L {x1:.1f},{y1:.1f}"
		),
		"cambridge": (
			f"L {x0 + 4:.1f},{TOP_Y:.1f} L {x0 + 4:.1f},{TOP_Y + 10:.1f} "
			f"L {x0 + 16:.1f},{TOP_Y + 10:.1f} L {x1:.1f},{y1 - 6:.1f} L {x1:.1f},{y1:.1f}"
		),
		# Named house profiles: a bevel over a shoulder.
		"regency": (
			f"L {x0:.1f},{TOP_Y:.1f} "
			f"Q {x0 + 13:.1f},{TOP_Y + 2:.1f} {x0 + 15:.1f},{TOP_Y + 12:.1f} "
			f"L {x0 + 26:.1f},{TOP_Y + 12:.1f} L {x1:.1f},{y1 - 5:.1f} L {x1:.1f},{y1:.1f}"
		),
		"parklane": (
			f"L {x0 + 2:.1f},{TOP_Y:.1f} L {x0 + 15:.1f},{TOP_Y + 11:.1f} "
			f"L {x0 + 26:.1f},{TOP_Y + 11:.1f} L {x0 + 26:.1f},{TOP_Y + 17:.1f} "
			f"L {x1:.1f},{TOP_Y + 17:.1f} L {x1:.1f},{y1:.1f}"
		),
		"shaker": (
			f"L {x0 + 12:.1f},{TOP_Y:.1f} L {x0 + 12:.1f},{TOP_Y + 16:.1f} "
			f"L {x1:.1f},{TOP_Y + 16:.1f} L {x1:.1f},{y1:.1f}"
		),
	}
	return shapes.get(shape, shapes["square"])


def profile_swatch(shape: str, kind: str = "inside", width: int = 200, height: int = 80) -> str:
	"""One machined edge, drawn in section."""
	shape = (shape or "square").lower()

	if kind == "outside":
		# No panel groove: the stock simply runs to the shaped outer edge.
		path = (
			f"M {LEFT_X:.1f},{TOP_Y:.1f} "
			f"{_edge(shape, BODY_RIGHT + 26, BOTTOM_Y)} "
			f"L {LEFT_X:.1f},{BOTTOM_Y:.1f} Z"
		)
	else:
		path = (
			f"M {LEFT_X:.1f},{TOP_Y:.1f} "
			f"{_edge(shape, BODY_RIGHT, TONGUE_TOP)} "
			f"L {TONGUE_RIGHT:.1f},{TONGUE_TOP:.1f} "
			f"L {TONGUE_RIGHT:.1f},{TONGUE_BOTTOM:.1f} "
			f"L {BODY_RIGHT:.1f},{TONGUE_BOTTOM:.1f} "
			f"L {BODY_RIGHT:.1f},{BOTTOM_Y:.1f} "
			f"L {LEFT_X:.1f},{BOTTOM_Y:.1f} Z"
		)

	gradient_id = f"gw{abs(hash((shape, kind))) % 100000}"
	return (
		f'<svg viewBox="0 0 200 80" width="{width}" height="{height}" '
		'xmlns="http://www.w3.org/2000/svg" role="img">'
		f'<defs><linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1">'
		f'<stop offset="0" stop-color="{WOOD_LIGHT}"/>'
		f'<stop offset="0.55" stop-color="{WOOD_MID}"/>'
		f'<stop offset="1" stop-color="{WOOD_DARK}"/>'
		"</linearGradient></defs>"
		f'<path d="{path}" fill="url(#{gradient_id})" stroke="{WOOD_EDGE}" '
		'stroke-width="1" stroke-linejoin="round"/>'
		"</svg>"
	)


# ---------------------------------------------------------------------------
# Product tiles
# ---------------------------------------------------------------------------


def product_tile(product: str, width: int = 150, height: int = 190) -> str:
	"""A face-on cabinet door for the Product picker."""
	product = (product or "SQUARE").upper()
	painted = product == "MDF"

	light, mid, edge = (
		(PAINT_LIGHT, PAINT_MID, PAINT_EDGE) if painted else (WOOD_LIGHT, WOOD_MID, WOOD_EDGE)
	)
	gradient_id = f"gp{product}"

	body = [
		f'<svg viewBox="0 0 150 190" width="{width}" height="{height}" '
		'xmlns="http://www.w3.org/2000/svg" role="img">',
		f'<defs><linearGradient id="{gradient_id}" x1="0" y1="0" x2="1" y2="1">'
		f'<stop offset="0" stop-color="{light}"/>'
		f'<stop offset="1" stop-color="{mid}"/></linearGradient></defs>',
	]

	if product == "SLAB":
		# A flat panel shown with a little thickness, so it reads as "no frame".
		body += [
			f'<path d="M 18,150 L 18,44 L 120,26 L 132,38 L 132,144 L 30,162 Z" '
			f'fill="url(#{gradient_id})" stroke="{edge}" stroke-width="1.2" stroke-linejoin="round"/>',
			f'<path d="M 18,44 L 120,26 L 132,38 L 30,56 Z" fill="{light}" '
			f'stroke="{edge}" stroke-width="1.2" stroke-linejoin="round"/>',
			f'<path d="M 30,56 L 30,162 L 18,150 L 18,44 Z" fill="{WOOD_DARK if not painted else PAINT_MID}" '
			f'stroke="{edge}" stroke-width="1.2" stroke-linejoin="round"/>',
		]
		return "".join(body) + "</svg>"

	# Framed doors: outer stile/rail frame with an inset panel.
	frame = 22
	body.append(
		f'<rect x="12" y="10" width="126" height="170" rx="2" '
		f'fill="url(#{gradient_id})" stroke="{edge}" stroke-width="1.4"/>'
	)

	if product == "MDF":
		# Routed one-piece door: no joints, just a moulded panel field.
		body += [
			f'<rect x="{12 + frame}" y="{10 + frame}" width="{126 - 2 * frame}" '
			f'height="{170 - 2 * frame}" rx="3" fill="{PAINT_LIGHT}" '
			f'stroke="{edge}" stroke-width="1.1"/>',
			f'<rect x="{12 + frame + 7}" y="{10 + frame + 7}" width="{126 - 2 * frame - 14}" '
			f'height="{170 - 2 * frame - 14}" rx="2" fill="{PAINT_MID}" '
			f'stroke="{edge}" stroke-width="0.8"/>',
		]
		return "".join(body) + "</svg>"

	# SQUARE / MITRE differ only in how the corner joints are drawn -- which is
	# precisely the distinction the tiles exist to communicate.
	body += [
		f'<rect x="{12 + frame}" y="{10 + frame}" width="{126 - 2 * frame}" '
		f'height="{170 - 2 * frame}" rx="2" fill="{mid}" stroke="{edge}" stroke-width="1.1"/>',
		f'<rect x="{12 + frame + 8}" y="{10 + frame + 8}" width="{126 - 2 * frame - 16}" '
		f'height="{170 - 2 * frame - 16}" rx="1" fill="{light}" stroke="{edge}" stroke-width="0.8"/>',
	]

	joints = []
	if product == "MITRE":
		# 45 degrees across each corner.
		joints = [
			(12, 10, 12 + frame, 10 + frame),
			(138, 10, 138 - frame, 10 + frame),
			(12, 180, 12 + frame, 180 - frame),
			(138, 180, 138 - frame, 180 - frame),
		]
	else:
		# Square frame: rails run through, stiles butt into them.
		joints = [
			(12 + frame, 10, 12 + frame, 10 + frame),
			(138 - frame, 10, 138 - frame, 10 + frame),
			(12 + frame, 180, 12 + frame, 180 - frame),
			(138 - frame, 180, 138 - frame, 180 - frame),
		]

	for x1, y1, x2, y2 in joints:
		body.append(
			f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{edge}" stroke-width="0.9"/>'
		)

	return "".join(body) + "</svg>"


def species_swatch(name: str, width: int = 120, height: int = 60) -> str:
	"""A small grain swatch, so species pickers are not bare text."""
	seed = abs(hash(name or "")) % 360
	tone = f"hsl({28 + seed % 18}, {30 + seed % 25}%, {62 + seed % 14}%)"
	grain = f"hsl({26 + seed % 16}, {34 + seed % 22}%, {48 + seed % 12}%)"

	lines = "".join(
		f'<path d="M 0,{8 + i * 9} Q {30 + (seed + i * 7) % 25},{4 + i * 9} 60,{8 + i * 9} '
		f'T 120,{8 + i * 9}" fill="none" stroke="{grain}" stroke-width="0.8" opacity="0.4"/>'
		for i in range(6)
	)
	return (
		f'<svg viewBox="0 0 120 60" width="{width}" height="{height}" '
		'xmlns="http://www.w3.org/2000/svg" role="img">'
		f'<rect width="120" height="60" fill="{tone}"/>{lines}'
		f'<title>{escape(name or "")}</title></svg>'
	)
