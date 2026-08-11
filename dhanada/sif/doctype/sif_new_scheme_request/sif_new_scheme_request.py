# Copyright (c) 2026, KNAPS Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json


class SIFNewSchemeRequest(Document):
	_DOCTYPE_NAME = "SIF New Scheme Request"

	def on_submit(self):
		self._determine_and_execute_outcome()

	def on_update(self):
		pass

	def _determine_and_execute_outcome(self):
		completion_fields = ["scheme_name", "sebi_code", "allocations", "managers"]
		filled_count = 0

		for field in completion_fields:
			val = self.get(field)
			if isinstance(val, list):
				if len(val) > 0:
					filled_count += 1
			elif val:
				filled_count += 1

		if filled_count == 0:
			outcome = "Cancelled"
		elif filled_count == len(completion_fields):
			outcome = "Approved"
		else:
			outcome = "Partially Approved"

		frappe.logger("sif_sync").info(f"[OUTCOME] {outcome} determined for {self.name}")

		self.db_set("workflow_state", outcome)
		self.workflow_state = outcome

		if outcome in ["Approved", "Partially Approved"]:
			if not self.scheme:
				self._generate_sif_scheme()
		elif outcome == "Cancelled":
			self.cancel()

	def _generate_sif_scheme(self):
		# Generate the actual SIF Scheme
		scheme_doc = frappe.new_doc("SIF Scheme")
		
		# Copy fields
		for field in self.meta.fields:
			if field.fieldtype not in ("Table", "Table MultiSelect"):
				if scheme_doc.meta.has_field(field.fieldname) and field.fieldname not in ('name', 'amended_from'):
					scheme_doc.set(field.fieldname, self.get(field.fieldname))
					
		# Copy child tables
		for table_field in ["allocations", "managers"]:
			for row in self.get(table_field, []):
				new_row = row.as_dict().copy()
				for key in ["name", "parent", "parenttype", "parentfield", "creation", "modified", "owner", "modified_by"]:
					new_row.pop(key, None)
				scheme_doc.append(table_field, new_row)
				
		# Bypass direct-creation safety net
		scheme_doc.flags.from_approval = True
		scheme_doc.insert(ignore_permissions=True)
		
		# Link it back
		self.db_set('scheme', scheme_doc.name)
		
	def on_cancel(self):
		pass # Natively cancelled, no further action required.

@frappe.whitelist()
def create_approval_from_ui(data):
	"""
	Safely intercepts a UI request to create a New Scheme 
	and converts it into a SIF New Scheme Request document.
	"""
	if isinstance(data, str):
		data = json.loads(data)
		
	approval_doc = frappe.new_doc("SIF New Scheme Request")
	
	# Set simple fields
	for field in approval_doc.meta.fields:
		if field.fieldtype not in ("Table", "Table MultiSelect"):
			if field.fieldname in data:
				approval_doc.set(field.fieldname, data.get(field.fieldname))
				
	# Handle child tables dynamically
	for field in approval_doc.meta.fields:
		if field.fieldtype in ("Table", "Table MultiSelect"):
			if field.fieldname in data:
				for row in data.get(field.fieldname, []):
					new_row = dict(row)
					for key in ["name", "parent", "parenttype", "parentfield", "creation", "modified", "owner", "modified_by"]:
						new_row.pop(key, None)
					approval_doc.append(field.fieldname, new_row)
				
	approval_doc.insert(ignore_permissions=True)
	return approval_doc.name

