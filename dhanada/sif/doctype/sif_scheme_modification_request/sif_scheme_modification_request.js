// Copyright (c) 2026, KNAPS Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("SIF Scheme Modification Request", {
	setup(frm) {
		// Fetch editable fields
		frappe.call({
			method: "dhanada.sif.doctype.sif_scheme_modification_request.sif_scheme_modification_request.get_editable_fields",
			callback: function (r) {
				if (r.message) {
					frm.custom_editable_fields = r.message;
					frm.trigger("apply_dynamic_options");
				}
			}
		});

		// Fetch managers map for human-readable formatter
		frappe.db.get_list("SIF Fund Manager", {
			fields: ["name", "manager_name"],
			limit: 0
		}).then(records => {
			frm.manager_name_map = {};
			records.forEach(r => {
				frm.manager_name_map[r.name] = r.manager_name;
			});
			frm.trigger("setup_formatters");
		});
	},
	
	setup_formatters(frm) {
		if (!frm.fields_dict.changed_fields || !frm.fields_dict.changed_fields.grid) return;
		
		const format_json_field = (value, doc) => {
			if (!value) return value;
			if (doc.field_name === "managers") {
				try {
					const arr = JSON.parse(value);
					if (!Array.isArray(arr)) return value;
					
					let html = "<ol style='margin-left: 15px; padding-left: 0;'>";
					arr.forEach(m => {
						const name = (frm.manager_name_map && frm.manager_name_map[m.manager_name]) || m.manager_name;
						let details = name;
						if (m.from_date) details += ` &mdash; From: ${frappe.datetime.str_to_user(m.from_date)}`;
						if (m.to_date) details += ` &mdash; To: ${frappe.datetime.str_to_user(m.to_date)}`;
						if (!m.is_active) details += ` (Inactive)`;
						html += `<li>${details}</li>`;
					});
					html += "</ol>";
					return html;
				} catch (e) {
					return value;
				}
			}
			// Pretty print other JSON arrays (like allocations)
			try {
				const obj = JSON.parse(value);
				return `<pre style="font-size: 11px; max-height: 200px;">${JSON.stringify(obj, null, 2)}</pre>`;
			} catch (e) {
				return value;
			}
		};

		frm.fields_dict.changed_fields.grid.formatters.old_value = format_json_field;
		frm.fields_dict.changed_fields.grid.formatters.new_value = format_json_field;
		frm.fields_dict.changed_fields.grid.formatters.override_value = format_json_field;
	},

	refresh(frm) {
		frm.page.clear_actions();
		frm.page.clear_menu();

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

		if (frm.doc.__onload && frm.doc.__onload.editable_fields) {
			frm.custom_editable_fields = frm.doc.__onload.editable_fields;
		}
		if (frm.custom_editable_fields) {
			frm.trigger("apply_dynamic_options");
		}
		frm.trigger("setup_formatters");
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
