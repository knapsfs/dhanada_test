// Copyright (c) 2026, KNAPS Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("SIF New Scheme Request", {
	refresh(frm) {
		frm.page.clear_actions();
		frm.page.clear_menu();

		if (frm.doc.docstatus === 0) {
			frm.page.set_primary_action("Save", () => frm.save());
		}

		if (frm.doc.scheme) {
			frm.add_custom_button(__('View Live Scheme'), function() {
				frappe.set_route('Form', 'SIF Scheme', frm.doc.scheme);
			});
		}
	},
});
