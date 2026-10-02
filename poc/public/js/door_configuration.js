// Live configurator behaviour for Door Configuration.
//
// The server owns every rule; this script pushes the current form state to
// `recalculate` and paints what comes back, and supplies the three visual
// controls the Desk form has no native equivalent for: the Product tile row,
// the profile picker grid, and the segmented radios.

const RECALC_DEBOUNCE_MS = 300;
const API = "poc.poc.doctype.door_configuration.door_configuration";

const WATCHED_FIELDS = [
	"product", "door_type", "units", "panel_type", "thickness", "thickness_uom",
	"frame_species", "panel_species", "corner_pegs",
	"inside_profile", "outside_profile", "applied_moulding",
	"right_inside_profile", "top_inside_profile", "bottom_inside_profile",
	"right_outside_profile", "top_outside_profile", "bottom_outside_profile",
	"all_sides_equal_inside", "all_sides_equal_outside",
	"width_imperial", "height_imperial", "width_metric", "height_metric",
	"custom_frame_widths", "inverted_joints",
	"frame_width_imperial", "frame_width_metric",
	"frame_width_left_imperial", "frame_width_right_imperial",
	"frame_width_top_imperial", "frame_width_bottom_imperial",
	"frame_width_left_metric", "frame_width_right_metric",
	"frame_width_top_metric", "frame_width_bottom_metric",
	"hinge_qty", "hinge_side", "hinge_distance_from_edge",
];

// Fields rendered as a horizontal radio row instead of a <select>, matching the
// client's screens. Frappe has no native radio control for Select fields.
const SEGMENTED = ["units", "door_type", "thickness", "thickness_uom", "hinge_side"];

// Link fields that open the image grid rather than a plain search.
const PROFILE_FIELDS = {
	inside_profile: "Inside",
	right_inside_profile: "Inside",
	top_inside_profile: "Inside",
	bottom_inside_profile: "Inside",
	outside_profile: "Outside",
	right_outside_profile: "Outside",
	top_outside_profile: "Outside",
	bottom_outside_profile: "Outside",
};

frappe.ui.form.on("Door Configuration", {
	onload(frm) {
		frm.trigger("render_product_tiles");
	},

	refresh(frm) {
		frm.trigger("render_product_tiles");
		frm.trigger("render_preview");
		frm.trigger("decorate_controls");
		frm.trigger("add_buttons");
	},

	add_buttons(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Create Quotation"), () => create_quotation(frm));
		}
	},

	catalogue(frm) {
		load_catalogue_item(frm);
	},

	// --- Product tiles ------------------------------------------------------

	render_product_tiles(frm) {
		const wrapper = frm.get_field("product_picker");
		if (!wrapper || !wrapper.$wrapper) return;

		if (frm._product_tiles) {
			paint_tiles(frm, frm._product_tiles);
			return;
		}

		frappe.call({ method: `${API}.get_product_tiles` }).then((r) => {
			frm._product_tiles = (r && r.message) || [];
			paint_tiles(frm, frm._product_tiles);
		});
	},

	// --- Controls -----------------------------------------------------------

	decorate_controls(frm) {
		SEGMENTED.forEach((fieldname) => segment(frm, fieldname));
		Object.keys(PROFILE_FIELDS).forEach((fieldname) =>
			attach_profile_picker(frm, fieldname, PROFILE_FIELDS[fieldname])
		);
	},

	all_sides_equal_inside(frm) {
		frm.trigger("decorate_controls");
		frm.trigger("render_preview");
	},

	all_sides_equal_outside(frm) {
		frm.trigger("decorate_controls");
		frm.trigger("render_preview");
	},

	custom_frame_widths(frm) {
		// Seed the four members from the master so the operator starts from
		// what they were already looking at, rather than four blanks.
		if (frm.doc.custom_frame_widths) {
			["left", "right", "top", "bottom"].forEach((side) => {
				if (!frm.doc[`frame_width_${side}_imperial`]) {
					frm.set_value(`frame_width_${side}_imperial`, frm.doc.frame_width_imperial);
				}
			});
		}
		frm.trigger("render_preview");
	},

	door_type(frm) {
		frm.trigger("decorate_controls");
		frm.trigger("render_preview");
	},

	units(frm) {
		frm.trigger("decorate_controls");
		frm.trigger("render_preview");
	},

	rail_dividers(frm) {
		resize_table(frm, "rails", frm.doc.rail_dividers);
		frm.trigger("render_preview");
	},

	stile_dividers(frm) {
		resize_table(frm, "stiles", frm.doc.stile_dividers);
		frm.trigger("render_preview");
	},

	render_preview: frappe.utils.debounce(function (frm) {
		frappe
			.call({
				method: `${API}.recalculate`,
				args: { doc: JSON.stringify(frm.doc) },
				freeze: false,
			})
			.then((r) => paint(frm, r && r.message));
	}, RECALC_DEBOUNCE_MS),
});

frappe.ui.form.on("Door Rail Divider", {
	height_imperial: (frm) => frm.trigger("render_preview"),
	width_imperial: (frm) => frm.trigger("render_preview"),
	rails_remove: (frm) => frm.trigger("render_preview"),
});

frappe.ui.form.on("Door Stile Divider", {
	distance_imperial: (frm) => frm.trigger("render_preview"),
	width_imperial: (frm) => frm.trigger("render_preview"),
	stiles_remove: (frm) => frm.trigger("render_preview"),
});

WATCHED_FIELDS.forEach((fieldname) => {
	frappe.ui.form.on("Door Configuration", {
		[fieldname]: (frm) => frm.trigger("render_preview"),
	});
});

// ---------------------------------------------------------------------------
// Product tiles
// ---------------------------------------------------------------------------

function paint_tiles(frm, tiles) {
	const wrapper = frm.get_field("product_picker");
	if (!wrapper || !wrapper.$wrapper) return;

	const html = tiles
		.map((tile) => {
			const selected = tile.value === frm.doc.product;
			return `
				<div class="door-tile ${selected ? "selected" : ""}" data-product="${tile.value}"
					role="button" tabindex="0" aria-pressed="${selected}">
					<div class="door-tile-art">${tile.svg}</div>
					<div class="door-tile-label">${frappe.utils.escape_html(tile.label)}</div>
					<div class="door-tile-bar"></div>
				</div>`;
		})
		.join("");

	wrapper.$wrapper.html(`
		<style>
		.door-tiles{display:flex;gap:14px;flex-wrap:wrap;padding:4px 0 10px}
		.door-tile{border:1px solid var(--border-color,#d1d8dd);border-radius:6px;overflow:hidden;
			cursor:pointer;background:var(--card-bg,#fff);transition:border-color .12s, box-shadow .12s;
			width:164px;text-align:center}
		.door-tile:hover{border-color:var(--blue-500,#0289f7)}
		.door-tile:focus-visible{outline:2px solid var(--blue-500,#0289f7);outline-offset:2px}
		.door-tile.selected{border-color:var(--blue-500,#0289f7);
			box-shadow:0 0 0 1px var(--blue-500,#0289f7)}
		.door-tile-art{padding:10px 8px 2px}
		.door-tile-art svg{max-width:100%;height:auto}
		.door-tile-label{font-size:11px;color:var(--text-muted,#8d99a6);padding:4px 6px 8px}
		.door-tile.selected .door-tile-label{color:var(--text-color,#1f272e);font-weight:600}
		.door-tile-bar{height:6px;background:transparent}
		.door-tile.selected .door-tile-bar{background:var(--blue-500,#0289f7)}
		</style>
		<div class="door-tiles">${html}</div>`);

	const choose = (el) => {
		const product = el.getAttribute("data-product");
		if (product && product !== frm.doc.product) {
			frm.set_value("product", product).then(() => frm.trigger("render_product_tiles"));
		}
	};

	wrapper.$wrapper.find(".door-tile").on("click", function () {
		choose(this);
	});
	wrapper.$wrapper.find(".door-tile").on("keydown", function (e) {
		if (e.key === "Enter" || e.key === " ") {
			e.preventDefault();
			choose(this);
		}
	});
}

// ---------------------------------------------------------------------------
// Segmented radios
// ---------------------------------------------------------------------------

function segment(frm, fieldname) {
	const field = frm.get_field(fieldname);
	if (!field || !field.$wrapper || !field.df || field.df.fieldtype !== "Select") return;

	const $control = field.$wrapper.find(".control-input");
	if (!$control.length || !$control.find("select").length) return;

	const options = (field.df.options || "").split("\n").filter(Boolean);
	if (!options.length || options.length > 4) return;

	$control.hide();
	field.$wrapper.find(".door-segment").remove();

	const buttons = options
		.map((option) => {
			const on = option === frm.doc[fieldname];
			return `<label class="door-segment-option ${on ? "on" : ""}">
				<input type="radio" name="seg-${fieldname}" value="${frappe.utils.escape_html(option)}"
					${on ? "checked" : ""}>
				<span>${frappe.utils.escape_html(option)}</span></label>`;
		})
		.join("");

	const $seg = $(`
		<div class="door-segment">
		<style>
		.door-segment{display:flex;gap:16px;align-items:center;padding:2px 0}
		.door-segment-option{display:inline-flex;align-items:center;gap:6px;margin:0;
			font-weight:400;cursor:pointer;font-size:13px}
		.door-segment-option.on span{font-weight:600;color:var(--text-color,#1f272e)}
		</style>
		${buttons}</div>`);

	$seg.find("input").on("change", function () {
		frm.set_value(fieldname, this.value);
	});

	field.$wrapper.find(".control-input-wrapper").append($seg);
}

// ---------------------------------------------------------------------------
// Profile picker
// ---------------------------------------------------------------------------

function attach_profile_picker(frm, fieldname, profile_type) {
	const field = frm.get_field(fieldname);
	if (!field || !field.$wrapper) return;
	if (field.df.hidden || !field.$wrapper.is(":visible")) return;

	field.$wrapper.find(".door-browse").remove();

	const $button = $(
		`<button type="button" class="btn btn-xs btn-default door-browse" style="margin-top:4px">
			${__("Browse profiles")}</button>`
	);
	$button.on("click", () => open_profile_dialog(frm, fieldname, profile_type));
	field.$wrapper.find(".control-input-wrapper").append($button);
}

function open_profile_dialog(frm, fieldname, profile_type) {
	frappe
		.call({
			method: `${API}.get_profiles`,
			args: { profile_type, product: frm.doc.product },
		})
		.then((r) => {
			const profiles = (r && r.message) || [];
			if (!profiles.length) {
				frappe.msgprint(__("No {0} profiles are set up yet.", [profile_type.toLowerCase()]));
				return;
			}

			const dialog = new frappe.ui.Dialog({
				title: __("Select {0} Profile", [profile_type]),
				size: "large",
				fields: [{ fieldname: "grid", fieldtype: "HTML" }],
			});

			const cells = profiles
				.map((p) => {
					const selected = p.value === frm.doc[fieldname];
					return `
					<div class="profile-cell ${selected ? "selected" : ""}" data-value="${frappe.utils.escape_html(
						p.value
					)}" role="button" tabindex="0">
						<div class="profile-art">${p.svg}</div>
						<div class="profile-name">${frappe.utils.escape_html(p.label)}</div>
						${p.detail ? `<div class="profile-detail">${frappe.utils.escape_html(p.detail)}</div>` : ""}
					</div>`;
				})
				.join("");

			dialog.fields_dict.grid.$wrapper.html(`
				<style>
				.profile-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));
					gap:10px;max-height:60vh;overflow-y:auto;padding:2px}
				.profile-cell{border:1px solid var(--border-color,#d1d8dd);border-radius:6px;
					padding:8px;text-align:center;cursor:pointer;background:var(--card-bg,#fff);
					transition:border-color .12s, box-shadow .12s}
				.profile-cell:hover{border-color:var(--blue-500,#0289f7)}
				.profile-cell:focus-visible{outline:2px solid var(--blue-500,#0289f7);outline-offset:2px}
				.profile-cell.selected{border-color:var(--blue-500,#0289f7);
					box-shadow:0 0 0 1px var(--blue-500,#0289f7)}
				.profile-art svg{max-width:100%;height:auto}
				.profile-name{font-size:12px;color:var(--blue-500,#0289f7);margin-top:4px}
				.profile-detail{font-size:10px;color:var(--text-muted,#8d99a6)}
				</style>
				<div class="profile-grid">${cells}</div>`);

			const pick = (el) => {
				frm.set_value(fieldname, el.getAttribute("data-value"));
				dialog.hide();
			};

			dialog.fields_dict.grid.$wrapper.find(".profile-cell").on("click", function () {
				pick(this);
			});
			dialog.fields_dict.grid.$wrapper.find(".profile-cell").on("keydown", function (e) {
				if (e.key === "Enter" || e.key === " ") {
					e.preventDefault();
					pick(this);
				}
			});

			dialog.show();
		});
}

// ---------------------------------------------------------------------------
// Catalogue
// ---------------------------------------------------------------------------

function load_catalogue_item(frm) {
	const catalogue = frm.doc.catalogue;
	if (!catalogue || catalogue === "CONFIGURE" || frm._loading_catalogue) return;

	frm._loading_catalogue = true;
	frappe
		.call({ method: `${API}.load_catalogue_item`, args: { catalogue } })
		.then((r) => {
			const values = (r && r.message) || {};

			Object.keys(values).forEach((key) => {
				if (key === "rails" || key === "stiles") return;
				if (frm.fields_dict[key]) frm.set_value(key, values[key]);
			});

			["rails", "stiles"].forEach((table) => {
				frm.clear_table(table);
				(values[table] || []).forEach((row) => frm.add_child(table, row));
				frm.refresh_field(table);
			});

			frm.trigger("render_product_tiles");
			frm.trigger("decorate_controls");
			frm.trigger("render_preview");
			frappe.show_alert({
				message: __("Loaded catalogue item {0}", [catalogue]),
				indicator: "green",
			});
		})
		.always(() => {
			frm._loading_catalogue = false;
		});
}

// ---------------------------------------------------------------------------
// Preview
// ---------------------------------------------------------------------------

function paint(frm, result) {
	const wrapper = frm.get_field("preview");
	if (!wrapper || !wrapper.$wrapper) return;

	if (!result || result.error) {
		wrapper.$wrapper.html(
			`<div class="text-muted small" style="padding:1rem">${frappe.utils.escape_html(
				(result && result.error) || __("Preview unavailable.")
			)}</div>`
		);
		return;
	}

	wrapper.$wrapper.html(banners(result.messages) + result.svg);

	// These are read-only values the server just derived. Assign them directly
	// rather than via set_value: set_value marks the form dirty, which would
	// flag every record as "Not Saved" the moment it was opened.
	show(frm, "inside_width_display", result.inside_width);
	show(frm, "inside_height_display", result.inside_height);
	show(frm, "horizontal_panels", result.horizontal_panels);
	show(frm, "vertical_panels", result.vertical_panels);
	show(frm, "total_panels", result.total_panels);
	show(frm, "configured_part_number", result.part_number);

	apply_divider_defaults(frm, result);
}

function show(frm, fieldname, value) {
	if (frm.doc[fieldname] === value) return;
	frm.doc[fieldname] = value;
	frm.refresh_field(fieldname);
}

// The server fills in even spacing for any divider the operator has not
// positioned yet; mirror that into the grid so they can see and adjust it.
function apply_divider_defaults(frm, result) {
	let changed = false;

	(frm.doc.rails || []).forEach((row, i) => {
		const computed = result.rails[i];
		if (!computed) return;
		if (!row.height_imperial && computed.centre) {
			row.height_imperial = computed.centre;
			changed = true;
		}
		if (!row.width_imperial && computed.width) {
			row.width_imperial = computed.width;
			changed = true;
		}
	});

	(frm.doc.stiles || []).forEach((row, i) => {
		const computed = result.stiles[i];
		if (!computed) return;
		if (!row.distance_imperial && computed.centre) {
			row.distance_imperial = computed.centre;
			changed = true;
		}
		if (!row.width_imperial && computed.width) {
			row.width_imperial = computed.width;
			changed = true;
		}
	});

	if (changed) {
		frm.refresh_field("rails");
		frm.refresh_field("stiles");
	}
}

function banners(messages) {
	if (!messages || !messages.length) return "";

	return messages
		.map((m) => {
			// Levels 1 and 2 block the save; level 4 is advisory -- notably the
			// collapse warning, which fires after frame widths were rewritten.
			const style = m.blocking
				? "background:var(--bg-red,#fff5f5);border-left:3px solid var(--red-500,#e24c4c)"
				: "background:var(--bg-orange,#fffaf0);border-left:3px solid var(--orange-500,#f0a02b)";
			return `<div style="${style};padding:6px 10px;margin-bottom:6px;font-size:11px">
				<b>${frappe.utils.escape_html(m.title)}</b>:
				${frappe.utils.escape_html(m.message)}</div>`;
		})
		.join("");
}

function resize_table(frm, table, target) {
	target = Math.max(0, Math.min(3, parseInt(target || 0, 10)));

	while ((frm.doc[table] || []).length > target) frm.doc[table].pop();
	while ((frm.doc[table] || []).length < target) frm.add_child(table, {});

	frm.refresh_field(table);
}

function create_quotation(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Create Quotation"),
		fields: [
			{ fieldname: "customer", fieldtype: "Link", options: "Customer", label: __("Customer") },
			{ fieldname: "qty", fieldtype: "Float", label: __("Quantity"), default: frm.doc.quantity || 1 },
			{
				fieldname: "note",
				fieldtype: "HTML",
				options: `<div class="text-muted small">${__(
					"Pricing is a placeholder for this POC: door area x the frame species rate."
				)}</div>`,
			},
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			frappe
				.call({
					method: "poc.configurator.quotation.create_quotation",
					args: { configuration: frm.doc.name, customer: values.customer, qty: values.qty || 1 },
					freeze: true,
					freeze_message: __("Creating Quotation..."),
				})
				.then((r) => {
					dialog.hide();
					if (r && r.message) frappe.set_route("Form", "Quotation", r.message);
				});
		},
	});
	dialog.show();
}
