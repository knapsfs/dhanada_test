import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import frappe
from typing import List, Dict, Any, Optional
import csv
import io
import re
import json
import logging
from .logger import log_error, log_warning

logger = logging.getLogger("sif_sync")

class GitHubClient:
    def __init__(self):
        self.repo_url = frappe.conf.get("sif_sync_github_repo_url", "https://github.com/Satyam4755/AMFI_Fetcher")
        self.branch = frappe.conf.get("sif_sync_github_branch", "main")
        self.token = frappe.conf.get("sif_sync_github_token")
        
        self.session = requests.Session()
        retry = Retry(
            total=3,
            read=3,
            connect=3,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 503, 504)
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        self.session.headers.update(headers)

        # Dedicated session for downloading raw files to prevent 
        # API headers from interfering and to reuse connections.
        self.dl_session = requests.Session()
        self.dl_session.mount("http://", adapter)
        self.dl_session.mount("https://", adapter)
        if self.token:
            self.dl_session.headers.update({"Authorization": f"token {self.token}"})
        
        if self.repo_url:
            self._owner, self._repo = self._parse_repo_url(self.repo_url)
        else:
            self._owner, self._repo = None, None
        
    def _parse_repo_url(self, repo_url: str):
        base_url = repo_url.rstrip("/")
        if "api.github.com" in base_url:
            parts = base_url.split("/")
            return parts[-2], parts[-1]
            
        parts = base_url.replace("https://github.com/", "").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
        raise ValueError(f"Invalid github repo url: {repo_url}")
        
    def _get_api_url(self, path: str) -> str:
        if not self._owner or not self._repo:
            raise ValueError("sif_sync_github_repo_url is not configured in site_config.json")
        return f"https://api.github.com/repos/{self._owner}/{self._repo}/contents/{path}?ref={self.branch}"
        
    def _list_directory(self, path: str) -> List[Dict[str, Any]]:
        """Lists files in a GitHub directory using Contents API."""
        url = self._get_api_url(path)
        try:
            # Using tuple timeout: 5s connect, 30s read. Prevents 2-minute IPv6 deadlocks.
            response = self.session.get(url, timeout=(5.0, 30.0))
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "message" in data:
                log_warning(f"GitHub API Error listing {path}: {data['message']}")
                return []
            else:
                log_warning(f"Path {path} is not a directory or returned unexpected format.")
                return []
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                log_warning(f"Directory not found on GitHub: {path}")
                return []
            log_error(f"HTTP Error listing {path}: {e}", exc_info=True)
            raise
        except requests.exceptions.RequestException as e:
            log_error(f"Network Error listing {path}: {e}", exc_info=True)
            raise

    def _download_file(self, download_url: str) -> bytes:
        """Downloads a raw file from GitHub."""
        try:
            # Reusing dl_session with connection pooling.
            # Tuple timeout (5.0, 30.0) ensures dead IPv6 resolves fail quickly.
            response = self.dl_session.get(download_url, timeout=(5.0, 30.0))
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            log_error(f"Failed to download file from {download_url}: {e}", exc_info=True)
            raise

    # 1. SCHEME DETAILS DISCOVERY
    def fetch_scheme_details(self) -> List[Dict[str, Any]]:
        directory = "data/sif/scheme/details"
        logger.info(f"Using repository: {self.repo_url} (branch: {self.branch})")
        logger.info(f"Fetching scheme details from directory: {directory}")
        
        files = self._list_directory(directory)
        json_files = [f for f in files if f.get("name", "").endswith(".json")]
        
        logger.info(f"Discovered {len(json_files)} JSON files in {directory}")
        
        parsed_schemes = []
        skipped = 0
        
        for file_info in json_files:
            try:
                content = self._download_file(file_info["download_url"])
                data = json.loads(content)
                parsed_schemes.append(data)
            except Exception as e:
                skipped += 1
                log_error(f"Failed to fetch or parse scheme detail file {file_info.get('name')}: {e}", exc_info=True)
                
        logger.info(f"Successfully parsed {len(parsed_schemes)} scheme files. Skipped {skipped}.")
        return parsed_schemes

    # 2. DAILY NAV DISCOVERY
    def fetch_latest_nav(self) -> List[Dict[str, Any]]:
        directory = "data/sif/scheme/nav/daily"
        logger.info(f"Using repository: {self.repo_url} (branch: {self.branch})")
        logger.info(f"Fetching latest NAV from directory: {directory}")
        
        files = self._list_directory(directory)
        csv_files = []
        for f in files:
            name = f.get("name", "")
            if re.match(r"^\d{8}\.csv$", name):
                csv_files.append(f)
                
        if not csv_files:
            log_warning(f"No matching YYYYMMDD.csv files found in {directory}")
            return []
            
        # Sort files descending to find the latest date
        csv_files.sort(key=lambda x: x["name"], reverse=True)
        latest_file = csv_files[0]
        
        logger.info(f"Latest NAV file selected: {latest_file['name']}")
        
        parsed_rows = []
        try:
            content = self._download_file(latest_file["download_url"])
            text = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(text))
            
            for row in reader:
                if "sif_code" in row and "nav_date" in row and "nav" in row:
                    parsed_rows.append(row)
                else:
                    log_warning(f"Skipping malformed row in {latest_file['name']}: {row}")
                    
            logger.info(f"Successfully parsed {len(parsed_rows)} NAV rows from {latest_file['name']}.")
        except Exception as e:
            log_error(f"Failed to fetch or parse NAV CSV {latest_file['name']}: {e}", exc_info=True)
            
        return parsed_rows

    # 3. PERFORMANCE DISCOVERY
    def fetch_performance(self) -> List[Dict[str, Any]]:
        directory = "data/sif/scheme/performance"
        logger.info(f"Using repository: {self.repo_url} (branch: {self.branch})")
        logger.info(f"Fetching performance data from directory: {directory}")
        
        files = self._list_directory(directory)
        json_files = [f for f in files if f.get("name", "").endswith(".json")]
        
        logger.info(f"Discovered {len(json_files)} JSON performance files in {directory}")
        
        parsed_performance = []
        skipped = 0
        
        for file_info in json_files:
            try:
                content = self._download_file(file_info["download_url"])
                data = json.loads(content)
                parsed_performance.append(data)
            except Exception as e:
                skipped += 1
                log_error(f"Failed to fetch or parse performance file {file_info.get('name')}: {e}", exc_info=True)
                
        logger.info(f"Successfully parsed {len(parsed_performance)} performance files. Skipped {skipped}.")
        return parsed_performance

    # 6. BACKWARD COMPATIBILITY
    def fetch_json(self, path: str) -> Dict[str, Any]:
        """
        Fetches a JSON file from the configured GitHub repository.
        Preserved for backward compatibility with older importer logic.
        """
        url = self._get_api_url(path)
        try:
            headers = {"Accept": "application/vnd.github.v3.raw"}
            if self.token:
                headers["Authorization"] = f"token {self.token}"
            response = requests.get(url, headers=headers, timeout=(5.0, 30.0))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            log_error(f"HTTP Error fetching {path} from GitHub: {e}", exc_info=True)
            raise
        except requests.exceptions.RequestException as e:
            log_error(f"Network Error fetching {path} from GitHub: {e}", exc_info=True)
            raise
        except ValueError as e:
            log_error(f"Failed to parse JSON from {path}: {e}", exc_info=True)
            raise

    def fetch_all_data(self) -> Dict[str, Any]:
        """
        Preserved for backward compatibility with `run_sync` in `scheduler.py`.
        """
        paths_config = frappe.conf.get("sif_sync_json_paths", "data.json")
        paths = [p.strip() for p in paths_config.split(",")]
        
        combined_data = {}
        for path in paths:
            try:
                data = self.fetch_json(path)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if k in combined_data and isinstance(combined_data[k], list) and isinstance(v, list):
                            combined_data[k].extend(v)
                        else:
                            combined_data[k] = v
                else:
                    log_warning(f"Expected dict from {path}, got {type(data)}. Skipping merge.")
            except Exception as e:
                raise Exception(f"Failed to fetch required data from {path}") from e
                
        return combined_data
