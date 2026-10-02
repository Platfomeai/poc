"""Create an ERPNext Quotation from a configuration.

The configured door becomes a non-stock Item named by the resolved part number,
with the spec sheet as its description, and lands on a draft Quotation.

Pricing here is deliberately crude -- area x the species' rate_per_sqft -- and
is labelled as a placeholder everywhere it surfaces.  Real pricing lives in the
part-number matrix and cost tables we were not given.
"""

import frappe
from frappe import _

ITEM_GROUP = "Configured Doors"
UOM = "Nos"


def ensure_item_group() -> str:
	if not frappe.db.exists("Item Group", ITEM_GROUP):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": ITEM_GROUP,
				"parent_item_group": "All Item Groups",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
	return ITEM_GROUP


def spec_description(config) -> str:
	"""The OrderDetails lines, rendered as the item description."""
	rows = "".join(
		f"<tr><td style='padding:1px 8px 1px 0'>{frappe.utils.escape_html(d.description)}</td>"
		f"<td style='padding:1px 0'>{frappe.utils.escape_html(d.value or '')}</td></tr>"
		for d in config.details
		if d.visible and d.description
	)
	return f"<table style='font-size:11px'>{rows}</table>"


def ensure_item(config) -> str:
	"""Find or create the Item for this part number.

	Configured doors are made to order, so the item is non-stock -- this keeps
	the POC clear of stock ledger setup while still producing a real Quotation.
	"""
	item_code = config.configured_part_number
	if not item_code:
		frappe.throw(_("Save the configuration first so a part number is resolved."))

	if frappe.db.exists("Item", item_code):
		item = frappe.get_doc("Item", item_code)
		item.description = spec_description(config)
		item.save(ignore_permissions=True)
		return item.name

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": f"{config.product} Door - {config.configuration_name}",
			"item_group": ensure_item_group(),
			"stock_uom": UOM,
			"is_stock_item": 0,
			"include_item_in_manufacturing": 0,
			"description": spec_description(config),
		}
	)
	item.insert(ignore_permissions=True)
	return item.name


def estimate_rate(config) -> float:
	"""Placeholder: door area in square feet x the frame species' rate."""
	from poc.configurator import units as u

	width = u.from_fraction(config.width_imperial) or 0
	height = u.from_fraction(config.height_imperial) or 0
	square_feet = (width * height) / 144.0

	rate_per_sqft = 0.0
	if config.frame_species:
		rate_per_sqft = frappe.db.get_value("Door Species", config.frame_species, "rate_per_sqft") or 0.0

	return round(square_feet * rate_per_sqft, 2)


@frappe.whitelist()
def create_quotation(configuration: str, customer: str | None = None, qty: float = 1) -> str:
	"""Create a draft Quotation for a saved Door Configuration."""
	config = frappe.get_doc("Door Configuration", configuration)
	item_code = ensure_item(config)

	quotation = frappe.get_doc(
		{
			"doctype": "Quotation",
			"quotation_to": "Customer",
			"party_name": customer,
			"order_type": "Sales",
			"items": [
				{
					"item_code": item_code,
					"item_name": f"{config.product} Door",
					"description": spec_description(config),
					"qty": qty,
					"uom": UOM,
					"rate": estimate_rate(config),
				}
			],
		}
	)

	if not customer:
		# Let the operator pick the customer on the draft rather than blocking
		# the demo flow on party setup.
		quotation.flags.ignore_mandatory = True

	quotation.insert(ignore_permissions=True, ignore_mandatory=not customer)

	config.db_set("quotation", quotation.name)
	return quotation.name
