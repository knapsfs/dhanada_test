import frappe
import json
from frappe.utils import cstr, flt, getdate
from .models import Scheme

from .constants import EDITABLE_FIELDS

def compare_scheme(existing_doc, incoming_scheme: Scheme) -> list:
    """
    Compares an existing SIF Scheme Frappe Document against an incoming Scheme dataclass.
    Returns a list of dictionaries containing 'field_name', 'old_value', and 'new_value'
    for any fields in EDITABLE_FIELDS that have changed.
    """
    changes = []
    
    def normalize_str(val):
        if val is None:
            return ""
        return cstr(val).strip()

    def normalize_float(val):
        if val is None:
            return 0.0
        return flt(val)
        
    def normalize_date(val):
        if not val:
            return None
        return getdate(val)
        
    def normalize_bool(val):
        return bool(val)
        
    def normalize_int(val):
        if val is None or str(val).strip() == "":
            return 0
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    for field in EDITABLE_FIELDS:
        if field == "allocations":
            old_allocs = []
            for a in existing_doc.get("allocations", []):
                old_allocs.append({
                    "allocation_type": normalize_str(a.allocation_type),
                    "minimum_allocation_percentage": normalize_float(a.minimum_allocation_percentage),
                    "maximum_allocation_percentage": normalize_float(a.maximum_allocation_percentage)
                })
            old_allocs.sort(key=lambda x: x["allocation_type"])
            
            new_allocs = []
            for a in incoming_scheme.allocations:
                new_allocs.append({
                    "allocation_type": normalize_str(a.allocation_type),
                    "minimum_allocation_percentage": normalize_float(a.minimum_allocation_percentage),
                    "maximum_allocation_percentage": normalize_float(a.maximum_allocation_percentage)
                })
            new_allocs.sort(key=lambda x: x["allocation_type"])
            
            if old_allocs != new_allocs:
                changes.append({
                    "field_name": "allocations",
                    "old_value": json.dumps(old_allocs, indent=2),
                    "old_value_json": json.dumps(old_allocs),
                    "new_value": json.dumps(new_allocs, indent=2),
                    "new_value_json": json.dumps(new_allocs)
                })
                
        elif field == "managers":
            old_mgrs = []
            for m in existing_doc.get("managers", []):
                old_mgrs.append({
                    "manager_name": normalize_str(m.manager_name),
                    "from_date": str(normalize_date(m.get("from"))) if normalize_date(m.get("from")) else "",
                    "to_date": str(normalize_date(m.get("to"))) if normalize_date(m.get("to")) else "",
                    "is_active": normalize_bool(m.is_active)
                })
            old_mgrs.sort(key=lambda x: x["manager_name"])
            
            new_mgrs = []
            for m in incoming_scheme.managers:
                # Resolve manager_name identical to how importer maps it
                fm_doc = None
                import re
                norm = re.sub(r'[^a-z0-9]', '', str(m.manager_name).lower())
                if norm:
                    managers_in_db = frappe.db.get_all("SIF Fund Manager", fields=["name", "manager_name"], order_by="creation asc")
                    for db_m in managers_in_db:
                        if re.sub(r'[^a-z0-9]', '', str(db_m.manager_name).lower()) == norm:
                            fm_doc = db_m.name
                            break
                
                if fm_doc:
                    new_mgrs.append({
                        "manager_name": normalize_str(fm_doc),
                        "from_date": str(normalize_date(m.from_date)) if normalize_date(m.from_date) else "",
                        "to_date": str(normalize_date(m.to_date)) if normalize_date(m.to_date) else "",
                        "is_active": normalize_bool(m.is_active)
                    })
            new_mgrs.sort(key=lambda x: x["manager_name"])
            
            if old_mgrs != new_mgrs:
                # Helper to format managers
                def _format_managers(mgrs):
                    if not mgrs:
                        return "None"
                    
                    try:
                        # Pre-fetch manager names
                        names = {}
                        for fm in frappe.db.get_all("SIF Fund Manager", fields=["name", "manager_name"]):
                            names[str(fm.name)] = fm.manager_name
                        
                        from frappe.utils import formatdate
                        
                        lines = []
                        for i, m in enumerate(mgrs, 1):
                            name = names.get(str(m['manager_name']), m['manager_name'])
                            line = f"{i}. {name}"
                            parts = []
                            if m.get('from_date'): parts.append(f"From: {formatdate(m['from_date'], 'dd-MM-yyyy')}")
                            if m.get('to_date'): parts.append(f"To: {formatdate(m['to_date'], 'dd-MM-yyyy')}")
                            if m.get('is_active') is not None:
                                parts.append(f"Active: {'Yes' if m['is_active'] else 'No'}")
                            if parts:
                                line += " | " + " | ".join(parts)
                            lines.append(line)
                        return "\n".join(lines)
                    except Exception:
                        return json.dumps(mgrs, indent=2)
                        
                changes.append({
                    "field_name": "managers",
                    "old_value": _format_managers(old_mgrs),
                    "old_value_json": json.dumps(old_mgrs),
                    "new_value": _format_managers(new_mgrs),
                    "new_value_json": json.dumps(new_mgrs)
                })
                
        else:
            old_raw = existing_doc.get(field)
            new_raw = getattr(incoming_scheme, field, None)
            
            if field in ["is_active", "is_active_for_subscription"]:
                old_val = normalize_bool(old_raw)
                new_val = normalize_bool(new_raw)
                
            elif field in ["minimum_subscription"]:
                old_val = normalize_float(old_raw)
                new_val = normalize_float(new_raw)
                
            elif field in ["maturity_date"]:
                old_val = str(normalize_date(old_raw)) if normalize_date(old_raw) else ""
                new_val = str(normalize_date(new_raw)) if normalize_date(new_raw) else ""
                
            elif field in ["risk_band"]:
                old_val = normalize_int(old_raw)
                new_val = normalize_int(new_raw)
                
            else:
                old_val = normalize_str(old_raw)
                new_val = normalize_str(new_raw)
                
            if old_val != new_val:
                changes.append({
                    "field_name": field,
                    "old_value": str(old_val) if old_val is not None else "",
                    "new_value": str(new_val) if new_val is not None else ""
                })
                
    return changes
