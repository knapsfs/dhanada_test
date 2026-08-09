// Copyright (c) 2026, KNAPS Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("SIF Scheme", {
	validate: function (frm) {
		if (frm.is_new()) {
			frappe.validated = false;

			if (frm._creating_approval) {
				return Promise.resolve();
			}

			frm._creating_approval = true;

			return new Promise((resolve) => {
				frappe.call({
					method: "dhanada.sif.doctype.sif_new_scheme_request.sif_new_scheme_request.create_approval_from_ui",
					args: { data: frm.doc },
					freeze: true,
					freeze_message: __("Generating Approval Request..."),
					callback: function (r) {
						if (r.message) {
							frappe.msgprint({
								title: __("Waiting for Approval"),
								message: __("Your new scheme has been submitted for approval. It will be added to SIF Scheme once approved."),
								indicator: 'blue'
							});
							frappe.set_route("List", "SIF Scheme");
						} else {
							frm._creating_approval = false;
						}
						resolve();
					},
					error: function () {
						frm._creating_approval = false;
						resolve();
					}
				});
			});
		}
	}
});
