# Copyright (c) 2026, KNAPS Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SIFSchemeModificationRequest(Document):
	_DOCTYPE_NAME = "SIF Scheme Modification Request"

	def validate(self):
		pass

	def before_cancel(self):
		pass

	def on_submit(self):
		self._determine_and_execute_outcome()

	def on_update(self):
		pass

	def _determine_and_execute_outcome(self):
		total_rows = len(self.get("changed_fields", []))
		checked_rows = sum(1 for row in self.get("changed_fields", []) if row.apply_change)

		if total_rows == 0 or checked_rows == 0:
			outcome = "Cancelled"
		elif checked_rows == total_rows:
			outcome = "Approved"
		else:
			outcome = "Partially Approved"

		frappe.logger("sif_sync").info(f"[OUTCOME] {outcome} determined for {self.name}")

		self.db_set("workflow_state", outcome)
		self.workflow_state = outcome

		if outcome in ["Approved", "Partially Approved"]:
			if not self.approved_on:
				from frappe.utils import now_datetime
				from dhanada.sif.sync.approval import process_approval
				process_approval(self)
				self.db_set("approved_by", frappe.session.user)
				self.db_set("approved_on", now_datetime())
		elif outcome == "Cancelled":
			self.cancel()

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
