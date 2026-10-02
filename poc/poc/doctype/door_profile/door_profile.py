import frappe
from frappe.model.document import Document

from poc.configurator import artwork


class DoorProfile(Document):
	def onload(self):
		self.set_onload("cross_section", self.cross_section())

	def cross_section(self) -> str:
		"""The drawn section, as shown in the profile picker."""
		kind = "outside" if self.profile_type == "Outside" else "inside"
		return artwork.profile_swatch(self.shape, kind, width=260, height=104)
