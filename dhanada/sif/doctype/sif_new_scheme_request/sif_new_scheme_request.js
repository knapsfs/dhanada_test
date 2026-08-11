// Copyright (c) 2026, KNAPS Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("SIF New Scheme Request", {
	refresh(frm) {
		frm.page.clear_actions();
		frm.page.clear_menu();

		if (frm.doc.docstatus === 0 && frm.doc.scheme) {
			frm.add_custom_button(__('View Live Scheme'), function() {
				frappe.set_route('Form', 'SIF Scheme', frm.doc.scheme);
			});
		}

		if (frm.doc.docstatus === 0) {
			frm.page.set_secondary_action("Save", () => frm.save());
			
			frm.page.set_primary_action("Submit", () => {
				if (frm._is_submitting) return;
				frm._is_submitting = true;
				
				const execute_submit = () => {
					frappe.xcall("frappe.model.workflow.apply_workflow", {
						doc: frm.doc,
						action: "Submit for Approval"
					}).then(() => {
						frm.reload_doc();
					}).catch((e) => {
						frappe.msgprint({ title: __('Submission Failed'), indicator: 'red', message: e.message || e.exc || e });
					}).finally(() => {
						frm._is_submitting = false;
					});
				};

				if (frm.is_new() || frm.is_dirty()) {
					frm.save('Save', () => {
						execute_submit();
					}, () => {
						frm._is_submitting = false;
					});
				} else {
					execute_submit();
				}
			});
		}
	},
});
