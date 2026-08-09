# Copyright (c) 2026, KNAPS Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SIFSchemeModificationRequest(Document):
	_DOCTYPE_NAME = "SIF Scheme Modification Request"

	def on_submit(self):
		pass # Natively submitted (Pending Approval). Execution deferred to on_update_after_submit.

	def on_update_after_submit(self):
		from frappe.utils import now_datetime
		if self.workflow_state in ["Approved", "Partially Approved"] and not self.approved_on:
			from dhanada.sif.sync.approval import process_approval
			process_approval(self)
			self.db_set("approved_by", frappe.session.user)
			self.db_set("approved_on", now_datetime())

	def on_cancel(self):
		if self.approved_on:
			from dhanada.sif.sync.approval import revert_approval
			revert_approval(self)

	def onload(self):
		from dhanada.sif.sync.constants import EDITABLE_FIELDS
		self.set_onload("editable_fields", EDITABLE_FIELDS)

@frappe.whitelist()
def get_editable_fields():
	from dhanada.sif.sync.constants import EDITABLE_FIELDS
	return EDITABLE_FIELDS
