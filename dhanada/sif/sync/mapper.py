from typing import Dict, Any, List, Optional
from datetime import datetime
import re
from .models import (
    AMC, Subcategory, FundManager, SchemeAllocation, SchemeFundManager, 
    Scheme, SchemePlan, NavUpdate, SchemePlanPerformance, SyncDataset
)
from .validator import DataValidator
from .logger import log_warning

class DataMapper:
    def __init__(self):
        self.validator = DataValidator()
        self.unmapped_fields_log = set()

    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        if not date_str:
            return None
        try:
            # Handle YYYY-MM-DD...
            if len(date_str) >= 10 and date_str[4] == "-" and date_str[7] == "-":
                return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            # Handle DD-MMM-YYYY...
            elif "-" in date_str and len(date_str) >= 11:
                return datetime.strptime(date_str[:11], "%d-%b-%Y").date()
            return None
        except ValueError:
            return None

    def _parse_currency(self, val_str: Any) -> float:
        if not val_str:
            return 0.0
        val = str(val_str).lower().replace(',', '')
        match = re.search(r'\d+(\.\d+)?', val)
        if match:
            num = float(match.group(0))
            if re.search(r'\b(lakh|lakhs|lac|lacs)\b', val):
                num *= 100000
            elif re.search(r'\b(cr|crore|crores)\b', val):
                num *= 10000000
                
            if num > 1000000000 or num <= 0:
                return 1000000.0
                
            return num
        return 1000000.0

    def _parse_float(self, val: Any) -> Optional[float]:
        if val is None or str(val).strip() in ("", "None", "null"):
            return None
        try:
            return float(val)
        except ValueError:
            return None

    def extract_numeric_risk(self, val: Any) -> Optional[int]:
        if val is None:
            return None
        match = re.search(r'\d+', str(val))
        if match:
            risk_val = int(match.group())
            return risk_val if 1 <= risk_val <= 5 else None
        return None

    def _derive_scheme_type(self, fund_type_desc: str) -> Optional[str]:
        desc = (fund_type_desc or "").lower()
        if "open ended" in desc or "open-ended" in desc:
            return "Open Ended"
        elif "close ended" in desc or "closed-ended" in desc or "close-ended" in desc:
            return "Close Ended"
        elif "interval" in desc:
            return "Interval"
        return None

    def _derive_investment_strategy(self, fund_type_desc: str, category: str) -> str:
        desc = (fund_type_desc + " " + (category or "")).lower()
        if "equity" in desc and "debt" not in desc:
            return "Equity"
        elif "debt" in desc and "equity" not in desc:
            return "Debt"
        elif "hybrid" in desc or ("equity" in desc and "debt" in desc):
            return "Hybrid"
        return "Equity" # Fallback

    def _parse_flat_plan(self, node: Dict, sebi_code: str, dataset: SyncDataset):
        if not isinstance(node, dict) or "isin_code" not in node:
            return
            
        name = node.get("name", "").lower()
        p_type = "Direct" if "direct" in name else "Regular"
        p_opt = "IDCW" if "idcw" in name or "dividend" in name or "income distribution" in name else "Growth"
        
        p_sub = None
        if "payout" in name: p_sub = "Payout"
        elif "reinvest" in name: p_sub = "Reinvestment"
        elif "transfer" in name: p_sub = "Transfer"
        
        self._create_plan_record(node, sebi_code, p_type, p_opt, p_sub, dataset)

    def _extract_plans(self, plans_dict: Dict, sebi_code: str, dataset: SyncDataset):
        if not plans_dict: return
        
        # Format 1: Flat/List structure with "additional_plans" at the root
        if "name" in plans_dict or "additional_plans" in plans_dict:
            self._parse_flat_plan(plans_dict, sebi_code, dataset)
            if "additional_plans" in plans_dict and isinstance(plans_dict["additional_plans"], list):
                for p in plans_dict["additional_plans"]:
                    self._parse_flat_plan(p, sebi_code, dataset)
            return

        # Format 2: Nested dictionary structure (regular -> growth)
        for plan_type_key, type_dict in plans_dict.items():
            if not isinstance(type_dict, dict): continue
            
            mapped_type = "Regular" if "regular" in plan_type_key.lower() else "Direct"
            
            # Level 2: option (growth / idcw)
            for option_key, option_val in type_dict.items():
                mapped_option = "Growth" if "growth" in option_key.lower() else "IDCW"
                
                # If option_val is a list, it's a leaf node array of records (Growth)
                if isinstance(option_val, list):
                    for rec in option_val:
                        self._create_plan_record(rec, sebi_code, mapped_type, mapped_option, None, dataset)
                    continue

                if not isinstance(option_val, dict): continue
                
                # Level 3: sub_option (payout, reinvestment, transfer, unknown)
                for sub_opt_key, sub_val in option_val.items():
                    mapped_sub = None
                    key_lower = sub_opt_key.lower()
                    if "payout" in key_lower:
                        mapped_sub = "Payout"
                    elif "reinvestment" in key_lower:
                        mapped_sub = "Reinvestment"
                    elif "transfer" in key_lower:
                        mapped_sub = "Transfer"
                        
                    # If sub_val is a list, it's a leaf node array of records (IDCW subtypes)
                    if isinstance(sub_val, list):
                        for rec in sub_val:
                            self._create_plan_record(rec, sebi_code, mapped_type, mapped_option, mapped_sub, dataset)
                        continue
                        
                    if not isinstance(sub_val, dict): continue
                        
                    # Backwards compatibility: Check if this is a leaf node dict
                    if "isin_code" in sub_val:
                        self._create_plan_record(sub_val, sebi_code, mapped_type, mapped_option, mapped_sub, dataset)
                    
                    # Backwards compatibility: Handle additional_plans array
                    if "additional_plans" in sub_val and isinstance(sub_val["additional_plans"], list):
                        for add_plan in sub_val["additional_plans"]:
                            self._create_plan_record(add_plan, sebi_code, mapped_type, mapped_option, mapped_sub, dataset)

    def _parse_managers(self, raw_managers_list: List[Dict], dataset: SyncDataset) -> List[SchemeFundManager]:
        parsed_managers = []
        
        # Regex helpers to extract standard dates
        date_pattern = re.compile(r'(\d{2}-[a-zA-Z]{3}-\d{4}|\d{2}-\d{2}-\d{4}|[a-zA-Z]+\s+\d{2},\s+\d{4}|\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}:\d{2})?)')
        
        # Pattern to capture trailing portions like "(Overseas portion)" or "Debt Portion"
        portion_extract_pattern = re.compile(r'(?i)(\([^)]*portion\)|Debt\s+Portion|Equity\s+Portion|Arbitrage\s+Portion)')
        
        # Pattern to strip labels and titles from the front or within the name
        label_pattern = re.compile(r'(?i)(Debt|Equity|Arbitrage)\s+Portion\s*[:\-]?\s*|\(for.*?portion\)|\bFM\s*[-_]?\s*\d+\s*[:\-]?\s*|^\d+[\.\-\)]?\s+')
        title_pattern = re.compile(r'^(Mr\.|Ms\.|Mrs\.|Dr\.|Mr|Ms|Mrs|Dr)\s*', flags=re.IGNORECASE)
        
        for fm in raw_managers_list:
            raw_name = fm.get("name", "") or ""
            raw_from = fm.get("from", "") or ""
            raw_to = fm.get("to")
            
            # 1. Parse dates (from and to)
            # Some strings might have multiple dates, we split them roughly by same delimiters as names
            from_chunks = [c.strip() for c in re.split(r';|,|\band\b|&|\n', str(raw_from), flags=re.IGNORECASE) if c.strip()]
            from_dates = []
            for fc in from_chunks:
                match = date_pattern.search(fc)
                from_dates.append(self._parse_date(match.group(1)) if match else None)
                
            parsed_to_date = None
            if raw_to:
                match_to = date_pattern.search(str(raw_to))
                if match_to:
                    parsed_to_date = self._parse_date(match_to.group(1))
            
            # 2. Split raw name into individual managers
            name_chunks = [c.strip() for c in re.split(r';|,|\band\b|&|\n|:', raw_name, flags=re.IGNORECASE) if c.strip()]
            
            for i, chunk in enumerate(name_chunks):
                # Extract portion if present in this specific chunk
                extracted_portion = None
                portion_match = portion_extract_pattern.search(chunk)
                if portion_match:
                    extracted_portion = portion_match.group(1).strip("() ")
                    chunk = portion_extract_pattern.sub('', chunk) # Remove it from the chunk
                
                # Use provided role_or_portion if extracted is missing
                final_portion = extracted_portion or fm.get("role_or_portion")
                
                # Clean up labels and titles
                clean_name = label_pattern.sub('', chunk).strip()
                clean_name = title_pattern.sub('', clean_name).strip()
                clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                
                if not clean_name: 
                    continue
                
                # Truncate to 140 chars to satisfy Frappe Link field limits for malformed upstream data
                clean_name = clean_name[:140].strip()
                
                # Determine date
                parsed_from_date = None
                if len(from_dates) == len(name_chunks):
                    parsed_from_date = from_dates[i]
                elif len(from_dates) == 1:
                    parsed_from_date = from_dates[0]
                elif len(from_dates) > i:
                    parsed_from_date = from_dates[i]
                    
                dataset.fund_managers.append(FundManager(manager_name=clean_name))
                parsed_managers.append(SchemeFundManager(
                    manager_name=clean_name,
                    manager_type=fm.get("type"),
                    role_or_portion=final_portion,
                    from_date=parsed_from_date,
                    to_date=parsed_to_date,
                    is_active=True if not parsed_to_date else False
                ))
                
        return parsed_managers

    def _create_plan_record(self, node: Dict, sebi_code: str, p_type: str, p_opt: str, p_sub: Optional[str], dataset: SyncDataset):
        isin = node.get("isin_code")
        if not isin:
            return
            
        # Map time_period to Frappe Select options
        period_val = node.get("time_period")
        frappe_period = None
        if period_val:
            period_map = {
                "daily": "Daily",
                "weekly": "Weekly",
                "fortnightly": "Fortnightly",
                "monthly": "Monthly",
                "quarterly": "Quarterly",
                "half_yearly": "Half Yearly",
                "annual": "Annual",
                "periodic": "Periodic"
            }
            frappe_period = period_map.get(period_val)
            
        dataset.scheme_plans.append(SchemePlan(
            isin=isin,
            sebi_code=sebi_code,
            type=p_type,
            option=p_opt,
            sub_option=p_sub,
            period=frappe_period,
            sif_code=node.get("amfi_code"),
            rta_code=node.get("rta_code")
        ))

    def map_dataset(self, raw_data: Dict[str, Any]) -> SyncDataset:
        dataset = SyncDataset()

        # We assume the caller passes raw_data grouped by source type for processing.
        # { "scheme_details": [...], "nav_daily": [...], "performance": [...] }

        # 1. Scheme Details
        for raw_scheme in raw_data.get("scheme_details", []):
            if self.validator.validate_amfi_scheme_details(raw_scheme):
                
                # Derive fields
                scheme_type = self._derive_scheme_type(raw_scheme.get("fund_type", ""))
                investment_strategy = self._derive_investment_strategy(raw_scheme.get("fund_type", ""), raw_scheme.get("category", ""))
                
                min_sub = 0.0
                min_sub_text = None
                inv_limits = raw_scheme.get("investment_limits", {})
                if isinstance(inv_limits, dict):
                    raw_min = inv_limits.get("minimum_application_amount")
                    min_sub_text = str(raw_min) if raw_min else None
                    min_sub = self._parse_currency(raw_min)
                
                if not min_sub or min_sub < 100:
                    min_sub = 1000000.00
                
                managers = self._parse_managers(raw_scheme.get("fund_managers") or [], dataset)
                
                allocations = []
                for alloc in (raw_scheme.get("asset_allocation") or []):
                    if isinstance(alloc, dict):
                        allocations.append(SchemeAllocation(
                            allocation_type=alloc.get("allocation_type") or "Unknown Allocation Type",
                            minimum_allocation_percentage=self._parse_float(alloc.get("minimum_percentage")),
                            maximum_allocation_percentage=self._parse_float(alloc.get("maximum_percentage"))
                        ))
                
                category_name = raw_scheme.get("category", "Uncategorized")
                dataset.subcategories.append(Subcategory(subcategory_name=category_name))
                
                raw_sif = raw_scheme.get("sif_name")
                sif_name = str(raw_sif).replace(" SIF", "").strip() if raw_sif else None

                # Extract AMC
                if sif_name:
                    sebi_code = raw_scheme.get("sebi_code", "")
                    code_fallback = sebi_code.split("/")[-1] if "/" in sebi_code else sif_name.upper()[:4]
                    
                    dataset.amcs.append(AMC(
                        code=code_fallback,
                        amc_name=f"{sif_name} Asset Management",
                        sif_name=sif_name,
                        registration_number=code_fallback, # Unavailable in JSON, fallback to code
                        rta="", # Unavailable at root level, safely default to empty
                        is_active=True
                    ))

                dataset.schemes.append(Scheme(
                    sebi_code=raw_scheme.get("sebi_code"),
                    scheme_name=raw_scheme.get("fund_name"),
                    amc_registration_number=None,
                    sif_name=sif_name,
                    investment_strategy=investment_strategy,
                    scheme_type=scheme_type,
                    scheme_subcategory=category_name,
                    risk_band=self.extract_numeric_risk(raw_scheme.get("riskometer_as_on_date")) or self.extract_numeric_risk(raw_scheme.get("riskometer_at_launch")),
                    riskometer_at_launch=raw_scheme.get("riskometer_at_launch"),
                    potential_risk_class=raw_scheme.get("potential_risk_class"),
                    scheme_objective=raw_scheme.get("scheme_objective") or "Objective not provided",
                    face_value=raw_scheme.get("face_value"),
                    exit_load=raw_scheme.get("exit_load"),
                    minimum_subscription=min_sub,
                    minimum_subscription_text=min_sub_text,
                    nfo_start_date=self._parse_date(raw_scheme.get("nfo_open_date")),
                    nfo_end_date=self._parse_date(raw_scheme.get("nfo_close_date")),
                    nfo_allotment_date=self._parse_date(raw_scheme.get("allotment_date")),
                    scheme_reopen_date=self._parse_date(raw_scheme.get("reopen_date")),
                    maturity_date=self._parse_date(raw_scheme.get("maturity_date")),
                    benchmark_tier_1=raw_scheme.get("benchmark_tier_1"),
                    benchmark_tier_2=raw_scheme.get("benchmark_tier_2"),
                    registrar=raw_scheme.get("registrar"),
                    custodian=raw_scheme.get("custodian"),
                    auditor=raw_scheme.get("auditor"),
                    is_active=True,
                    allocations=allocations,
                    managers=managers
                ))
                
                # Extract plans
                self._extract_plans(raw_scheme.get("plans", {}), raw_scheme.get("sebi_code"), dataset)


        # 2. NAV Daily
        for raw_nav in raw_data.get("nav_daily", []):
            if self.validator.validate_amfi_nav(raw_nav):
                dataset.nav_updates.append(NavUpdate(
                    sif_code=raw_nav.get("sif_code"),
                    nav_date=self._parse_date(raw_nav.get("nav_date")), # type: ignore
                    nav=self._parse_float(raw_nav.get("nav")) or 0.0
                ))

        # 3. Performance
        for raw_perf in raw_data.get("performance", []):
            if self.validator.validate_amfi_performance(raw_perf):
                ret = raw_perf.get("returns", {})
                
                # Log unmapped fields (e.g. 7_year)
                if "7_year" in ret and "7_year" not in self.unmapped_fields_log:
                    log_warning("Source field '7_year' in performance is ignored (no matching Frappe field).")
                    self.unmapped_fields_log.add("7_year")

                dataset.performances.append(SchemePlanPerformance(
                    sif_code=raw_perf.get("sif_code"),
                    performance_date=self._parse_date(raw_perf.get("last_updated")), # type: ignore
                    day_1=self._parse_float(ret.get("1_day")),
                    week_1=self._parse_float(ret.get("1_week")),
                    month_1=self._parse_float(ret.get("1_month")),
                    months_3=self._parse_float(ret.get("3_month")), # Mismatch handled
                    months_6=self._parse_float(ret.get("6_month")), # Mismatch handled
                    year_to_date=self._parse_float(ret.get("year_to_date")),
                    year_1=self._parse_float(ret.get("1_year")),
                    years_2=self._parse_float(ret.get("2_year")), # Mismatch handled
                    years_3=self._parse_float(ret.get("3_year")), # Mismatch handled
                    years_5=self._parse_float(ret.get("5_year")), # Mismatch handled
                    years_10=self._parse_float(ret.get("10_year")), # Mismatch handled
                    since_inception=self._parse_float(ret.get("since_launch")), # Mismatch handled
                ))

        # Remove duplicates from subcategories, fund_managers, and amcs lists
        # We do this cleanly by turning them into dicts keyed by their unique names
        unique_subs = {sub.subcategory_name: sub for sub in dataset.subcategories}
        dataset.subcategories = list(unique_subs.values())
        
        unique_fms = {}
        for fm in dataset.fund_managers:
            norm = re.sub(r'[^a-z0-9]', '', str(fm.manager_name).lower())
            if norm not in unique_fms:
                unique_fms[norm] = fm
        dataset.fund_managers = list(unique_fms.values())
        
        unique_amcs = {amc.sif_name: amc for amc in dataset.amcs if amc.sif_name}
        dataset.amcs = list(unique_amcs.values())

        return dataset
