from frappe import _


def get_data():
    return [
        {
            "module_name": "SIF",
            "category": "Modules",
            "label": _("SIF"),
            "color": "#6C63FF",
            "icon": "octicon octicon-briefcase",
            "type": "module",
            "description": _("SIF Investment Management"),
        }
    ]