import frappe
from frappe.utils import flt, getdate, cstr, date_diff, nowdate

def get_default_plan(plans):
    if not plans:
        return None
    
    # Sort order: type='Direct' + option='Growth' is best.
    # We will score them to find the best match.
    def score(p):
        s = 0
        p_type = cstr(p.type).strip().lower()
        p_opt = cstr(p.option).strip().lower()
        if p_type == 'direct':
            s += 10
        if p_opt == 'growth':
            s += 5
        return s
        
    # Sort deterministically by score (desc) then name (desc)
    return sorted(plans, key=lambda p: (score(p), p.name or ""), reverse=True)[0]

def mask_invalid_returns(perf_dict, launch_date):
    """
    MariaDB defaults Float to 0.0. If a fund is too young for a period,
    convert 0.0 to None so the frontend displays N/A.
    """
    if not perf_dict or not launch_date:
        return perf_dict
        
    age_days = date_diff(nowdate(), getdate(launch_date))
    
    thresholds = {
        "1_day": 1,
        "1_week": 7,
        "1_month": 30,
        "3_months": 90,
        "6_months": 180,
        "1_year": 365,
        "2_years": 730,
        "3_years": 1095,
        "5_years": 1825,
        "10_years": 3650
    }
    
    for key, min_days in thresholds.items():
        if key in perf_dict:
            # If the fund is younger than the period and value is exactly 0.0, it's missing data.
            # Even if it's not 0.0, theoretically it shouldn't exist, but we only mask 0.0 to be safe.
            if age_days < min_days and flt(perf_dict[key]) == 0.0:
                perf_dict[key] = None
                
    return perf_dict

@frappe.whitelist(allow_guest=True)
def get_funds_list():
    try:
        schemes = frappe.get_all("SIF Scheme", fields=[
            "name", "sebi_code", "scheme_name", "amc", "investment_strategy",
            "scheme_subcategory", "scheme_type", "risk_band",
            "minimum_subscription", "exit_load", "nfo_start_date", "nfo_allotment_date"
        ])
        
        result = []
        for s in schemes:
            launch_date = s.nfo_allotment_date or s.nfo_start_date
            
            # Get plans for this scheme
            plans = frappe.get_all("SIF Scheme Plan", filters={"scheme": s.name}, fields=[
                "name", "type", "option", "sub_option", "nav", "nav_date", "performance"
            ])
            
            best_plan = get_default_plan(plans)
            
            plan_nav = None
            nav_date = None
            returns_1w = None
            returns_1m = None
            returns_3m = None
            returns_6m = None
            returns_ytd = None
            returns_1y = None
            returns_3y = None
            returns_5y = None
            
            if best_plan:
                plan_nav = best_plan.nav if best_plan.nav_date else None
                nav_date = best_plan.nav_date
                
                if best_plan.performance:
                    perf = frappe.db.get_value("SIF Scheme Plan Performance", best_plan.performance, 
                        ["1_week", "1_month", "3_months", "6_months", "year_to_date", "1_year", "3_years", "5_years"], as_dict=True)
                    if perf:
                        perf = mask_invalid_returns(perf, launch_date)
                        returns_1w = perf.get("1_week")
                        returns_1m = perf.get("1_month")
                        returns_3m = perf.get("3_months")
                        returns_6m = perf.get("6_months")
                        returns_ytd = perf.get("year_to_date")
                        returns_1y = perf.get("1_year")
                        returns_3y = perf.get("3_years")
                        returns_5y = perf.get("5_years")
                        
            # Get AMC name if it's a link
            amc_name = None
            if s.amc:
                amc_name = frappe.db.get_value("SIF Asset Management Company", s.amc, "amc_name") or s.amc
                
            cat_name = None
            if s.scheme_subcategory:
                cat_name = s.scheme_subcategory
                
            result.append({
                "id": s.sebi_code or s.name,
                "sebi_code": s.sebi_code,
                "name": s.scheme_name,
                "amc": amc_name,
                "category": cat_name,
                "assetClass": s.scheme_type,
                "investmentStrategy": s.investment_strategy,
                "risk": s.risk_band,
                "minInvestment": s.minimum_subscription,
                "nav": plan_nav,
                "navDate": nav_date,
                "returns1W": returns_1w,
                "returns1M": returns_1m,
                "returns3M": returns_3m,
                "returns6M": returns_6m,
                "returnsYTD": returns_ytd,
                "returns1Y": returns_1y,
                "returns3Y": returns_3y,
                "returns5Y": returns_5y,
                "exitLoad": s.exit_load,
                "launchDate": launch_date,
                # Fields that don't exist in backend, kept null
                "aum": None,
                "expenseRatio": None,
                "rating": None,
                "isNew": False
            })
            
        return {"status": "success", "data": result}
    except Exception as e:
        frappe.log_error(title="get_funds_list API Error", message=frappe.get_traceback())
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def get_fund_details(identifier):
    try:
        # Identifier can be sebi_code or name
        scheme_name = frappe.db.get_value("SIF Scheme", {"sebi_code": identifier}, "name")
        if not scheme_name:
            scheme_name = frappe.db.get_value("SIF Scheme", {"name": identifier}, "name")
            
        if not scheme_name:
            return {"status": "error", "message": "Fund not found"}
            
        scheme = frappe.get_doc("SIF Scheme", scheme_name)
        
        # Resolve related data
        amc_name = None
        if scheme.amc:
            amc_name = frappe.db.get_value("SIF Asset Management Company", scheme.amc, "amc_name") or scheme.amc
            
        launch_date = scheme.nfo_allotment_date or scheme.nfo_start_date
            
        # Get Plans and Performance
        plans = frappe.get_all("SIF Scheme Plan", filters={"scheme": scheme.name}, fields=[
            "name", "type", "option", "sub_option", "period", "isin", "sif_code", 
            "rta_code", "nav", "nav_date", "performance"
        ])
        
        for p in plans:
            # Fix False Zero NAV: if there is no nav_date, the nav 0.0 is a default artifact and should be None.
            if not p.nav_date:
                p.nav = None
                
            if p.performance:
                perf = frappe.db.get_value("SIF Scheme Plan Performance", p.performance, 
                    ["1_day", "1_week", "1_month", "3_months", "6_months", "year_to_date", "1_year", "3_years", "5_years", "since_inception", "performance_date"], as_dict=True)
                p["performance_data"] = mask_invalid_returns(perf, launch_date)
            else:
                p["performance_data"] = None
                
        # Managers
        managers = []
        if getattr(scheme, "managers", None):
            for m in scheme.managers:
                # Fetch actual name instead of relying on the Link ID
                actual_name = frappe.db.get_value("SIF Fund Manager", m.manager_name, "manager_name") or m.manager_name
                managers.append({
                    "name": actual_name,
                    "from": getattr(m, 'from', None),
                    "to": getattr(m, 'to', None),
                    "is_active": m.is_active
                })
        # Allocations
        allocations = [{"type": a.allocation_type, "min": a.minimum_allocation_percentage, "max": a.maximum_allocation_percentage} for a in scheme.allocations] if getattr(scheme, "allocations", None) else []
        
        # Find default plan for quick stats
        best_plan = get_default_plan(plans)
        
        data = {
            "id": scheme.sebi_code or scheme.name,
            "sebi_code": scheme.sebi_code,
            "name": scheme.scheme_name,
            "amc": amc_name,
            "category": scheme.scheme_subcategory,
            "assetClass": scheme.scheme_type,
            "schemeType": scheme.scheme_type,
            "benchmarkTier1": getattr(scheme, "benchmark_tier_1", None),
            "benchmarkTier2": getattr(scheme, "benchmark_tier_2", None),
            "launchDate": launch_date,
            "reopenDate": getattr(scheme, "scheme_reopen_date", None),
            "maturityDate": getattr(scheme, "maturity_date", None),
            "schemeObjective": scheme.scheme_objective,
            "exitLoad": scheme.exit_load,
            "minInvestment": scheme.minimum_subscription,
            "minInvestmentText": getattr(scheme, "minimum_subscription_text", None),
            "faceValue": getattr(scheme, "face_value", None),
            "registrar": getattr(scheme, "registrar", None),
            "custodian": getattr(scheme, "custodian", None),
            "auditor": getattr(scheme, "auditor", None),
            "risk": scheme.risk_band,
            "riskometerAtLaunch": getattr(scheme, "riskometer_at_launch", None),
            "potentialRiskClass": getattr(scheme, "potential_risk_class", None),
            "documents": {
                "factsheet": getattr(scheme, "factsheet_url", None),
                "kim": getattr(scheme, "kim_url", None),
                "sai": getattr(scheme, "sai_url", None),
                "isid": getattr(scheme, "isid_url", None)
            },
            "managers": managers,
            "allocations": allocations,
            "plans": plans,
            "defaultPlan": best_plan,
            # Null fields for gaps
            "fundSize": None,
            "expenseRatio": None,
            "metrics": None
        }
        
        return {"status": "success", "data": data}
        
    except Exception as e:
        frappe.log_error(title="get_fund_details API Error", message=frappe.get_traceback())
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def create_chatbot_lead():
    try:
        chat_summary_value = frappe.form_dict.get("chat_summary")
        
        first_name = frappe.form_dict.get("name", "Unknown")
        last_name = ""
        
        if " " in first_name and first_name != "Unknown":
            parts = first_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1]
            
        doc_data = {
            "doctype": "CRM Lead",
            "first_name": first_name,
            "last_name": last_name,
            "email": frappe.form_dict.get("email"),
            "mobile_no": frappe.form_dict.get("mobile"),
            "interest": frappe.form_dict.get("interest"),
            "chat_summary": chat_summary_value,
            "source": frappe.form_dict.get("source", "Website Chatbot")
        }
        
        lead = frappe.get_doc(doc_data)
        lead.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "lead_name": lead.name}
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Chatbot Lead Creation Failed")
        frappe.throw(f"Failed to create Lead: {str(e)}")

@frappe.whitelist(allow_guest=True)
def create_website_lead():
    try:
        full_name = frappe.form_dict.get("full_name", "").strip()
        email = frappe.form_dict.get("email", "").strip()
        phone = frappe.form_dict.get("phone", "").strip()
        
        if not full_name:
            frappe.throw("Full Name is a required field.")
            
        if not email and not phone:
            frappe.throw("Please provide either your email address or phone number.")
            
        first_name = full_name
        last_name = ""
        
        if " " in full_name:
            parts = full_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1]
            
        doc_data = {
            "doctype": "CRM Lead",
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "mobile_no": phone,
            "source": "Website Form"
        }
        
        lead = frappe.get_doc(doc_data)
        lead.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "lead_name": lead.name}
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Website Lead Creation Failed")
        # Return error cleanly to frontend
        frappe.local.response['http_status_code'] = 400
        return {"success": False, "message": str(e)}

@frappe.whitelist(allow_guest=True)
def get_chatbot_config():
    """Returns non-sensitive chatbot configuration like the API Base URL."""
    try:
        # Check if the doctype exists in case it hasn't been migrated yet
        if not frappe.db.exists("DocType", "Chatbot AI Credentials"):
            return {"api_base_url": ""}
            
        api_base_url = frappe.db.get_single_value("Chatbot AI Credentials", "api_base_url")
        return {"api_base_url": api_base_url or ""}
    except Exception as e:
        frappe.log_error(message=str(e), title="Chatbot Config Error")
        return {"api_base_url": ""}

@frappe.whitelist(allow_guest=True)
def chatbot_response():
    """Securely proxies the chat request to Gemini API."""
    import requests
    import json
    
    try:
        # 1. Fetch Credentials securely from Single DocType
        if not frappe.db.exists("DocType", "Chatbot AI Credentials"):
            return {"success": False, "message": "Chatbot AI Credentials DocType not found"}

        credentials=frappe.get_doc("Chatbot AI Credentials")    
        api_key = credentials.get_password("gemini_api_key")
        
        if not api_key:
            return {"success": False, "message": "Gemini API key is not configured"}
            
        # 2. Parse request payload
        try:
            payload = json.loads(frappe.request.data)
            contents = payload.get("conversation_history", [])
            system_instruction = payload.get("system_instruction", "")
        except Exception:
            return {"success": False, "message": "Invalid JSON payload"}
            
        if not contents:
            return {"success": False, "message": "Missing conversation history"}
            
        # 3. Format payload for Gemini REST API
        gemini_payload = {
            "contents": contents
        }
        
        if system_instruction:
            gemini_payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
            
        # 4. Fallback loop over models
        models = [
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite',
            'gemini-3.1-flash-lite'
        ]
        
        headers = {"Content-Type": "application/json"}
        last_error = None
        
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                response = requests.post(url, json=gemini_payload, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    try:
                        reply_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        return {"success": True, "message": reply_text}
                    except (KeyError, IndexError):
                        return {"success": False, "message": "Invalid response format from Gemini"}
                else:
                    last_error = f"{response.status_code}: {response.text}"
            except Exception as e:
                last_error = str(e)
                
        # If all models fail
        frappe.log_error(message=f"Gemini API completely failed. Last error: {last_error}", title="Chatbot Gemini Error")
        return {"success": False, "message": "I'm unable to fetch that information right now."}
        
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Chatbot Response Wrapper Error")
        return {"success": False, "message": "Internal Server Error"}

