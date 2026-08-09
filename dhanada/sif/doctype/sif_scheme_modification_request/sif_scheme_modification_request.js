// Copyright (c) 2026, KNAPS Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("SIF Scheme Modification Request", {
	setup(frm) {
		frappe.call({
			method: "dhanada.sif.doctype.sif_scheme_modification_request.sif_scheme_modification_request.get_editable_fields",
			callback: function (r) {
				if (r.message) {
					frm.custom_editable_fields = r.message;
					frm.trigger("apply_dynamic_options");
				}
			}
		});
	},
	refresh(frm) {
		if (frm.doc.__onload && frm.doc.__onload.editable_fields) {
			frm.custom_editable_fields = frm.doc.__onload.editable_fields;
		}
		if (frm.custom_editable_fields) {
			frm.trigger("apply_dynamic_options");
		}
	},
	apply_dynamic_options(frm) {
		if (!frm.custom_editable_fields) return;
		const options = frm.custom_editable_fields.join("\n");

		let base_df = frappe.meta.get_docfield("SIF Scheme Modification Request Item", "field_name");
		if (base_df) base_df.options = options;

		let meta_df = frappe.meta.get_docfield("SIF Scheme Modification Request Item", "field_name", frm.doc.name);
		if (meta_df) meta_df.options = options;

		if (frm.fields_dict.changed_fields && frm.fields_dict.changed_fields.grid) {
			try {
				frm.fields_dict.changed_fields.grid.update_docfield_property("field_name", "options", options);
			} catch (e) { }

			let grid_df = frm.fields_dict.changed_fields.grid.docfields.find(d => d.fieldname === "field_name");
			if (grid_df) grid_df.options = options;
		}

		frm.refresh_field("changed_fields");
	}
});
