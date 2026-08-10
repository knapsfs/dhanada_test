import frappe
from typing import List
from .models import SyncDataset
from .logger import log_error, log_warning
from .comparator import compare_scheme
from .approval import create_approval_request

class DataImporter:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            "created": 0,
            "updated": 0,
            "deleted": 0,
            "skipped": 0,
            "errors": 0,
            "approvals_requested": 0
        }

    def import_dataset(self, dataset: SyncDataset):
        """
        Imports the dataset idempotently.
        Follows strictly the order required for SIF DocTypes.
        """

        self.dataset = dataset

        for amc in dataset.amcs:
            self._upsert_amc(amc)
            
        for sub in dataset.subcategories:
            self._upsert_subcategory(sub)
            
        for fm in dataset.fund_managers:
            self._upsert_fund_manager(fm)
            
        for scheme in dataset.schemes:
            self._upsert_scheme(scheme)
            
        for plan in dataset.scheme_plans:
            self._upsert_scheme_plan(plan)
            
        self._reconcile_all_scheme_plans()
            
        for nav_update in dataset.nav_updates:
            self._update_nav(nav_update)
            
        for perf in dataset.performances:
            self._upsert_performance(perf)

    def _upsert_amc(self, amc):
        try:
            exists = frappe.db.exists("SIF Asset Management Company", {"code": amc.code}) or \
                     frappe.db.exists("SIF Asset Management Company", {"registration_number": amc.registration_number})
            
            if exists:
                if not self.dry_run:
                    doc = frappe.get_doc("SIF Asset Management Company", exists)
                    doc.amc_name = amc.amc_name
                    doc.sif_name = amc.sif_name
                    if amc.rta:
                        doc.rta = amc.rta
                    doc.is_active = int(amc.is_active)
                    doc.save(ignore_permissions=True)
                self.stats["updated"] += 1
            else:
                if not self.dry_run:
                    doc = frappe.get_doc({
                        "doctype": "SIF Asset Management Company",
                        "code": amc.code,
                        "amc_name": amc.amc_name,
                        "sif_name": amc.sif_name,
                        "registration_number": amc.registration_number,
                        "rta": amc.rta or "CAMS",
                        "is_active": int(amc.is_active)
                    })
                    doc.insert(ignore_permissions=True)
                self.stats["created"] += 1
        except Exception as e:
            self.stats["errors"] += 1
            log_error(f"Failed to upsert AMC {amc.code}: {e}", exc_info=True)

    def _upsert_subcategory(self, sub):
        try:
            exists = frappe.db.exists("SIF Investment Strategy Subcategory", sub.subcategory_name)
            if exists:
                self.stats["skipped"] += 1 # Nothing to update
            else:
                if not self.dry_run:
                    doc = frappe.get_doc({
                        "doctype": "SIF Investment Strategy Subcategory",
                        "subcategory_name": sub.subcategory_name
                    })
                    doc.insert(ignore_permissions=True)
                self.stats["created"] += 1
        except Exception as e:
            self.stats["errors"] += 1
            log_error(f"Failed to upsert Subcategory {sub.subcategory_name}: {e}", exc_info=True)

    def _get_existing_fund_manager(self, manager_name):
        import re
        
        if not hasattr(self, "_manager_cache"):
            self._manager_cache = {}
            managers = frappe.db.get_all("SIF Fund Manager", fields=["name", "manager_name"], order_by="creation asc")
            for m in managers:
                norm = re.sub(r'[^a-z0-9]', '', str(m.manager_name).lower())
                if norm and norm not in self._manager_cache:
                    self._manager_cache[norm] = m.name

        norm = re.sub(r'[^a-z0-9]', '', str(manager_name).lower())
        if not norm: 
            return None
            
        return self._manager_cache.get(norm)

    def _upsert_fund_manager(self, fm):
        try:
            exists = self._get_existing_fund_manager(fm.manager_name)
            if exists:
                self.stats["skipped"] += 1 # Nothing to update
            else:
                if not self.dry_run:
                    doc = frappe.get_doc({
                        "doctype": "SIF Fund Manager",
                        "manager_name": fm.manager_name
                    })
                    doc.insert(ignore_permissions=True)
                    import re
                    norm = re.sub(r'[^a-z0-9]', '', str(fm.manager_name).lower())
                    if norm:
                        self._manager_cache[norm] = doc.name
                self.stats["created"] += 1
        except Exception as e:
            self.stats["errors"] += 1
            log_error(f"Failed to upsert Fund Manager {fm.manager_name}: {e}", exc_info=True)

    def _upsert_scheme(self, scheme):
        try:

            amc_doc = None
            if scheme.sif_name:
                amc_doc = frappe.db.get_value("SIF Asset Management Company", {"sif_name": scheme.sif_name}, "name")

            if not amc_doc:
                log_warning(f"Skipping Scheme {scheme.sebi_code} - Missing AMC for SIF Name: {scheme.sif_name}")
                self.stats["skipped"] += 1
                return

            if scheme.sebi_code.startswith("TEMP_"):
                has_plans = getattr(self, "dataset", None) and any(p.sebi_code == scheme.sebi_code for p in self.dataset.scheme_plans)
                if not has_plans:
                    log_warning(f"Skipping Scheme {scheme.sebi_code} - Incomplete data (fallback SEBI code and no plans)")
                    self.stats["skipped"] += 1
                    return

            exists = frappe.db.exists("SIF Scheme", {"sebi_code": scheme.sebi_code})
            
            if not exists:
                temp_exists = frappe.db.exists("SIF Scheme", {
                    "scheme_name": scheme.scheme_name,
                    "sebi_code": ["like", "TEMP_%"]
                })
                if temp_exists:
                    if not self.dry_run:
                        frappe.db.set_value("SIF Scheme", temp_exists, "sebi_code", scheme.sebi_code)
                    exists = temp_exists

            if exists:
                doc = frappe.get_doc("SIF Scheme", exists)
                
                # 1. Detect Changes
                changes = compare_scheme(doc, scheme)
                
                if changes:
                    # 2a. Delegate to Approval Service
                    if not self.dry_run:
                        _ = create_approval_request(doc, changes)
                    self.stats["approvals_requested"] += 1
                else:
                    # 2b. Auto-Update (No editable fields changed)
                    if not self.dry_run:
                        self._map_scheme_fields(doc, scheme, amc_doc, update_child_tables=False)
                        doc.save(ignore_permissions=True)
                    self.stats["updated"] += 1
            else:
                if not self.dry_run:
                    pending = frappe.db.exists("SIF New Scheme Request", {"sebi_code": scheme.sebi_code, "docstatus": 0})
                    if not pending:
                        doc = frappe.new_doc("SIF New Scheme Request")
                        doc.sebi_code = scheme.sebi_code
                        self._map_scheme_fields(doc, scheme, amc_doc)
                        doc.flags.skip_auto_submit = True
                        doc.insert(ignore_permissions=True)
                        self.stats["approvals_requested"] += 1
                    else:
                        self.stats["skipped"] += 1
                        log_warning(f"Skipping new scheme {scheme.sebi_code} - New Scheme Approval already pending")

            if not self.dry_run:
                frappe.db.commit()
        except Exception as e:
            if not self.dry_run:
                frappe.db.rollback()
            self.stats["errors"] += 1
            log_error(f"Failed to upsert Scheme {scheme.sebi_code}: {e}", exc_info=True)

    def _map_scheme_fields(self, doc, scheme, amc_doc, update_child_tables=True):
        doc.scheme_name = scheme.scheme_name
        if amc_doc:
            doc.amc = amc_doc
        doc.investment_strategy = scheme.investment_strategy
        doc.scheme_type = scheme.scheme_type
        doc.scheme_subcategory = scheme.scheme_subcategory
        doc.riskometer_at_launch = scheme.riskometer_at_launch
        doc.risk_band = scheme.risk_band
        doc.potential_risk_class = scheme.potential_risk_class
        doc.scheme_objective = scheme.scheme_objective
        doc.exit_load = scheme.exit_load
        doc.minimum_subscription = scheme.minimum_subscription
        doc.minimum_subscription_text = scheme.minimum_subscription_text
        doc.nfo_start_date = scheme.nfo_start_date
        doc.nfo_end_date = scheme.nfo_end_date
        doc.nfo_allotment_date = scheme.nfo_allotment_date
        doc.scheme_reopen_date = scheme.scheme_reopen_date
        doc.benchmark_tier_1 = scheme.benchmark_tier_1
        doc.benchmark_tier_2 = scheme.benchmark_tier_2
        doc.face_value = scheme.face_value
        doc.maturity_date = scheme.maturity_date
        doc.registrar = scheme.registrar
        doc.custodian = scheme.custodian
        doc.auditor = scheme.auditor
        doc.is_active = int(scheme.is_active)
        doc.is_active_for_subscription = int(scheme.is_active_for_subscription)
        doc.isid_url = scheme.isid_url
        doc.kim_url = scheme.kim_url
        doc.sai_url = scheme.sai_url
        doc.factsheet_url = scheme.factsheet_url
        doc.monthly_portfolio_disclosure_url = scheme.monthly_portfolio_disclosure_url
        
        if update_child_tables:
            doc.set("allocations", [])
            for alloc in scheme.allocations:
                doc.append("allocations", {
                    "allocation_type": alloc.allocation_type,
                    "minimum_allocation_percentage": alloc.minimum_allocation_percentage,
                    "maximum_allocation_percentage": alloc.maximum_allocation_percentage
                })

            doc.set("managers", [])
            for mgr in scheme.managers:
                fm_doc = self._get_existing_fund_manager(mgr.manager_name)
                if fm_doc:
                    doc.append("managers", {
                        "manager_name": fm_doc,
                        "from": mgr.from_date,
                        "to": mgr.to_date,
                        "is_active": int(mgr.is_active)
                    })
                else:
                    log_warning(f"Fund manager {mgr.manager_name} not found, skipping for scheme {scheme.sebi_code}")

    def _upsert_scheme_plan(self, plan):
        try:
            scheme_doc = frappe.db.exists("SIF Scheme", {"sebi_code": plan.sebi_code})
            if not scheme_doc:
                log_warning(f"Skipping Scheme Plan {plan.isin} - Missing Scheme {plan.sebi_code}")
                self.stats["skipped"] += 1
                return

            exists = frappe.db.exists("SIF Scheme Plan", {"isin": plan.isin})
            if exists:
                if not self.dry_run:
                    doc = frappe.get_doc("SIF Scheme Plan", exists)
                    doc.scheme = scheme_doc
                    doc.type = plan.type
                    doc.option = plan.option
                    doc.sub_option = plan.sub_option
                    doc.period = plan.period
                    doc.sif_code = plan.sif_code
                    doc.rta_code = plan.rta_code
                    # Do not overwrite nav and nav_date if None (to preserve NAV syncs)
                    if plan.nav is not None:
                        doc.nav = plan.nav
                    if plan.nav_date is not None:
                        doc.nav_date = plan.nav_date
                    doc.save(ignore_permissions=True)
                self.stats["updated"] += 1
            else:
                if not self.dry_run:
                    doc = frappe.new_doc("SIF Scheme Plan")
                    doc.isin = plan.isin
                    doc.scheme = scheme_doc
                    doc.type = plan.type
                    doc.option = plan.option
                    doc.sub_option = plan.sub_option
                    doc.period = plan.period
                    doc.sif_code = plan.sif_code
                    doc.rta_code = plan.rta_code
                    if plan.nav is not None:
                        doc.nav = plan.nav
                    if plan.nav_date is not None:
                        doc.nav_date = plan.nav_date
                    doc.insert(ignore_permissions=True)
                self.stats["created"] += 1

            if not self.dry_run:
                frappe.db.commit()
        except Exception as e:
            if not self.dry_run:
                frappe.db.rollback()
            self.stats["errors"] += 1
            log_error(f"Failed to upsert Scheme Plan {plan.isin}: {e}", exc_info=True)

    def _reconcile_all_scheme_plans(self):
        """
        Deletes SIF Scheme Plan records from the database that belong to the schemes in the current 
        dataset but are no longer present in the dataset's scheme_plans list.
        This cleans up old Direct plans or stale mappings.
        """
        if not getattr(self, "dataset", None) or not self.dataset.schemes:
            return
            
        try:
            for scheme in self.dataset.schemes:
                # Find the parent Scheme in Frappe
                scheme_doc = frappe.db.exists("SIF Scheme", {"sebi_code": scheme.sebi_code})
                if not scheme_doc:
                    continue
                    
                # Identify ISINs present in the incoming payload for THIS scheme
                incoming_isins = {p.isin for p in self.dataset.scheme_plans if p.sebi_code == scheme.sebi_code}
                
                # Identify ISINs currently in the Frappe DB for THIS scheme
                existing_plans = frappe.get_all("SIF Scheme Plan", filters={"scheme": scheme_doc}, pluck="isin")
                
                stale_isins = set(existing_plans) - incoming_isins
                
                for stale_isin in stale_isins:
                    if not self.dry_run:
                        # Deleting a Scheme Plan might have side effects on Performance
                        # Frappe handles referential integrity natively if configured, 
                        # but we force delete it to ensure cleanup.
                        frappe.delete_doc("SIF Scheme Plan", stale_isin, force=1, ignore_permissions=True)
                    self.stats["deleted"] += 1
            
            if not self.dry_run:
                frappe.db.commit()
        except Exception as e:
            if not self.dry_run:
                frappe.db.rollback()
            self.stats["errors"] += 1
            log_error(f"Failed to reconcile Scheme Plans: {e}", exc_info=True)

    def _update_nav(self, nav_update):
        try:
            matching_plans = frappe.get_all("SIF Scheme Plan", filters={"sif_code": nav_update.sif_code}, pluck="name")
            if not matching_plans:
                log_warning(f"Skipping NAV update for sif_code {nav_update.sif_code} - Scheme Plan not found")
                self.stats["skipped"] += 1
                return

            for plan_doc in matching_plans:
                if not self.dry_run:
                    doc = frappe.get_doc("SIF Scheme Plan", plan_doc)
                    if not doc.nav_date or str(nav_update.nav_date) >= str(doc.nav_date):
                        doc.nav = nav_update.nav
                        doc.nav_date = nav_update.nav_date
                        doc.save(ignore_permissions=True)
                self.stats["updated"] += 1

            if not self.dry_run:
                frappe.db.commit()
        except Exception as e:
            if not self.dry_run:
                frappe.db.rollback()
            self.stats["errors"] += 1
            log_error(f"Failed to update NAV for sif_code {nav_update.sif_code}: {e}", exc_info=True)

    def _upsert_performance(self, perf):
        try:
            matching_plans = frappe.get_all("SIF Scheme Plan", filters={"sif_code": perf.sif_code}, pluck="name")
            if not matching_plans:
                log_warning(f"Skipping Performance for sif_code {perf.sif_code} - Missing Scheme Plan")
                self.stats["skipped"] += 1
                return

            for plan_doc in matching_plans:
                perf_doc = None
                exists = frappe.db.exists("SIF Scheme Plan Performance", {"scheme_plan": plan_doc})
                if exists:
                    if not self.dry_run:
                        doc = frappe.get_doc("SIF Scheme Plan Performance", exists)
                        self._map_perf_fields(doc, perf)
                        doc.save(ignore_permissions=True)
                        perf_doc = doc.name
                    self.stats["updated"] += 1
                else:
                    if not self.dry_run:
                        doc = frappe.new_doc("SIF Scheme Plan Performance")
                        doc.scheme_plan = plan_doc
                        self._map_perf_fields(doc, perf)
                        doc.insert(ignore_permissions=True)
                        perf_doc = doc.name
                    self.stats["created"] += 1

                # Update the bidirectional link on the Scheme Plan
                if not self.dry_run and perf_doc:
                    plan = frappe.get_doc("SIF Scheme Plan", plan_doc)
                    if plan.performance != perf_doc:
                        plan.performance = perf_doc
                        plan.save(ignore_permissions=True)
                        
            if not self.dry_run:
                frappe.db.commit()
        except Exception as e:
            if not self.dry_run:
                frappe.db.rollback()
            self.stats["errors"] += 1
            log_error(f"Failed to upsert Performance for sif_code {perf.sif_code}: {e}", exc_info=True)

    def _map_perf_fields(self, doc, perf):
        doc.performance_date = perf.performance_date
        doc.set("1_day", perf.day_1)
        doc.set("1_week", perf.week_1)
        doc.set("1_month", perf.month_1)
        doc.set("3_months", perf.months_3)
        doc.set("6_months", perf.months_6)
        doc.year_to_date = perf.year_to_date
        doc.set("1_year", perf.year_1)
        doc.set("2_years", perf.years_2)
        doc.set("3_years", perf.years_3)
        doc.set("5_years", perf.years_5)
        doc.set("10_years", perf.years_10)
        doc.since_inception = perf.since_inception
