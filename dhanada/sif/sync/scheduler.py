import time
import frappe
from .github_client import GitHubClient
from .mapper import DataMapper
from .importer import DataImporter
from .logger import log_sync_start, log_sync_completed, log_error, log_warning

def sync_nav_performance(dry_run: bool = False):
    """
    Fetches, maps, and imports the latest NAV CSV and all Performance JSONs.
    """
    start_time = time.time()
    log_sync_start()
    
    try:
        client = GitHubClient()
        
        # 1. Fetch data
        nav_data = client.fetch_latest_nav()
        perf_data = client.fetch_performance()
        
        raw_data = {
            "nav_daily": nav_data,
            "performance": perf_data
        }
        
        # 2. Map data
        mapper = DataMapper()
        dataset = mapper.map_dataset(raw_data)
        validation_errors = mapper.validator.errors
        
        # 3. Import data
        importer = DataImporter(dry_run=dry_run)
        importer.import_dataset(dataset)
        
        duration = time.time() - start_time
        log_sync_completed(
            duration_seconds=round(duration, 2),
            stats=importer.stats,
            validation_errors=validation_errors
        )
        
        return {
            "status": "success",
            "type": "nav_performance",
            "dry_run": dry_run,
            "duration": round(duration, 2),
            "stats": importer.stats,
            "validation_errors_count": len(validation_errors)
        }
        
    except Exception as e:
        log_error(f"NAV and Performance Sync failed entirely: {e}", exc_info=True)
        raise

def sync_scheme_details(dry_run: bool = False):
    """
    Fetches, maps, and imports all Scheme Detail JSONs.
    """
    start_time = time.time()
    log_sync_start()
    
    try:
        client = GitHubClient()
        
        # 1. Fetch data
        frappe.logger("sif_sync").info("Starting to fetch scheme details from GitHub...")
        scheme_data = client.fetch_scheme_details()
        frappe.logger("sif_sync").info(f"Finished fetching scheme details. Received {len(scheme_data)} records.")
        
        
        raw_data = {
            "scheme_details": scheme_data
        }
        
        # 2. Map data
        frappe.logger("sif_sync").info("Starting data mapping...")
        mapper = DataMapper()
        dataset = mapper.map_dataset(raw_data)
        validation_errors = mapper.validator.errors
        frappe.logger("sif_sync").info(f"Finished mapping data. Found {len(validation_errors)} validation errors.")
        
        # 3. Import data
        frappe.logger("sif_sync").info(f"Starting database import (dry_run={dry_run})...")
        importer = DataImporter(dry_run=dry_run)
        importer.import_dataset(dataset)
        frappe.logger("sif_sync").info("Finished database import.")
        
        duration = time.time() - start_time
        log_sync_completed(
            duration_seconds=round(duration, 2),
            stats=importer.stats,
            validation_errors=validation_errors
        )
        
        return {
            "status": "success",
            "type": "scheme_details",
            "dry_run": dry_run,
            "duration": round(duration, 2),
            "stats": importer.stats,
            "validation_errors_count": len(validation_errors)
        }
        
    except Exception as e:
        log_error(f"Scheme Details Sync failed entirely: {e}", exc_info=True)
        raise

def run_github_sync_pipeline():
    """
    Master scheduled job to sync all data directly from GitHub.
    Serially executes scheme details, followed by nav and performance.
    """
    try:
        frappe.logger("sif_sync").info("Starting automated GitHub Sync Pipeline")
        sync_scheme_details()
        sync_nav_performance()
        frappe.logger("sif_sync").info("Completed automated GitHub Sync Pipeline successfully")
    except Exception as e:
        frappe.logger("sif_sync").error(f"GitHub Sync Pipeline failed: {str(e)}")
        raise
