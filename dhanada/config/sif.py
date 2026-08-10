from frappe import _


def get_data():
    return [
        {
            "label": _("SIF"),
            "icon": "octicon octicon-briefcase",
            "items": [
                {
                    "type": "page",
                    "name": "sif",
                    "label": _("SIF"),
                    "description": _("SIF Investment Management"),
                }
            ],
        }
    ]