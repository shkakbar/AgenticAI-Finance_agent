"""
Data Loader - Loads analysis data from JSON files for the Streamlit dashboard.
Reads the latest analysis from data/reports/ and provides clean access to all data.
"""
import os
import json
import glob
from datetime import datetime
from typing import Optional, Dict, Any

class DataLoader:
    """Loads and caches analysis data for the Streamlit dashboard."""
    def __init__(self, reports_dir='data/reports'):
        self.reports_dir = reports_dir
        self._cache = {}
        self._cache_timestamp = None

    def get_latest_report_path(self) -> Optional[str]:
        """Find the most recent JSON report file."""
        pattern = os.path.join(self.reports_dir, 'analysis_*.json')
        files = glob.glob(pattern)
        if not files:
            return None
        # Sort by filename (which includes timestamp) - newest first
        files.sort(reverse=True)
        return files[0]

    def load_latest_analysis(self, force_reload: bool = False) -> Optional[Dict[str, Any]]:
        """
        Load the most recent analysis data.
        Caches the result for performance.
        """
        latest_file = self.get_latest_report_path()

        if not latest_file:
            return None

        # Check cache
        file_mtime = os.path.getmtime(latest_file)
        if (not force_reload and
            self._cache_timestamp is not None and
            self._cache_timestamp == file_mtime and
            self._cache):
            return self._cache

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._cache = data
            self._cache_timestamp = file_mtime
            return data
        except Exception as e:
            print(f"⚠️  Error loading report: {e}")
            return None

    def get_report_metadata(self) -> Dict[str, Any]:
        """Get metadata about the latest report (without loading full data)."""
        latest_file = self.get_latest_report_path()
        if not latest_file:
            return {'exists': False}

        # Extract timestamp from filename
        filename = os.path.basename(latest_file)
        try:
            # Format: analysis_YYYYMMDD_HHMMSS.json
            timestamp_str = filename.replace('analysis_', '').replace('.json', '')
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            file_size = os.path.getsize(latest_file)
            return {
                'exists': True,
                'path': latest_file,
                'timestamp': timestamp,
                'timestamp_str': timestamp.strftime('%B %d, %Y at %I:%M %p'),
                'file_size_kb': round(file_size / 1024, 1)
            }
        except Exception as e:
            return {'exists': False, 'error': str(e)}

    def get_all_reports(self, limit: int = 10) -> list:
        """Get list of all available reports (most recent first)."""
        pattern = os.path.join(self.reports_dir, 'analysis_*.json')
        files = glob.glob(pattern)
        files.sort(reverse=True)

        reports = []
        for f in files[:limit]:
            filename = os.path.basename(f)
            try:
                timestamp_str = filename.replace('analysis_', '').replace('.json', '')
                timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                reports.append({
                    'path': f,
                    'timestamp': timestamp,
                    'timestamp_str': timestamp.strftime('%Y-%m-%d %H:%M'),
                    'file_size_kb': round(os.path.getsize(f) / 1024, 1)
                })
            except:
                continue
        return reports

    def clear_cache(self):
        """Clear the data cache."""
        self._cache = {}
        self._cache_timestamp = None

_loader = None
def get_loader() -> DataLoader:
    """Get the singleton DataLoader instance."""
    global _loader
    if _loader is None:
        _loader = DataLoader()
    return _loader