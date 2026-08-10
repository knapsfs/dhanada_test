# Copyright (c) 2026, KNAPS Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SIFSchemeModificationRequest(Document):
	_DOCTYPE_NAME = "SIF Scheme Modification Request"

	def validate(self):
		if not self.get("changed_fields"):
			return

		total_rows = len(self.changed_fields)
		checked_rows = sum(1 for row in self.changed_fields if row.apply_change)

		if self.workflow_state == "Approved":
			if checked_rows != total_rows:
				frappe.throw("To Approve, all modification rows must have 'Apply Change' checked. For partial selections, use 'Partially Approve'.")

		elif self.workflow_state == "Partially Approved":
			if checked_rows == 0:
				frappe.throw("To Partially Approve, at least one modification row must be checked. To reject all changes, use 'Cancel'.")
			if checked_rows == total_rows:
				frappe.throw("To Partially Approve, you cannot check all rows. Use 'Approve' instead.")

	def before_cancel(self):
		checked_rows = sum(1 for row in self.get("changed_fields", []) if row.apply_change)
		if checked_rows > 0:
			frappe.throw("To Cancel, no modification rows should have 'Apply Change' checked.")

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
