# Token usage tracking utilities
# Copyright 2026 Google LLC

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import google.auth
from google.cloud import storage

class TokenTracker:
    """Tracks and logs token usage for Gemini API calls."""

    def __init__(self, log_file: Optional[str] = None, use_gcs: bool = False, bucket_name: Optional[str] = None):
        self.log_file = log_file or "logs/token_usage.jsonl"
        self.use_gcs = use_gcs
        try:
            _, project_id = google.auth.default()
        except google.auth.exceptions.DefaultCredentialsError:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "unknown")
        self.bucket_name = bucket_name or f"{project_id}-token-logs"
        self.session_tokens = 0
        self.total_tokens = 0

        # Ensure log directory exists
        if not use_gcs and log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing token counts
        self._load_token_counts()

    def _load_token_counts(self):
        """Load existing token counts from persistent storage."""
        try:
            if self.use_gcs and self.bucket_name:
                # Load from GCS
                client = storage.Client()
                bucket = client.bucket(self.bucket_name)
                blob = bucket.blob("token_counts.json")

                if blob.exists():
                    data = json.loads(blob.download_as_text())
                    self.total_tokens = data.get("total_tokens", 0)
                    self.session_tokens = data.get("session_tokens", 0)
            else:
                # Load from local file
                count_file = Path(self.log_file).parent / "token_counts.json"
                if count_file.exists():
                    with open(count_file, 'r') as f:
                        data = json.load(f)
                        self.total_tokens = data.get("total_tokens", 0)
                        self.session_tokens = data.get("session_tokens", 0)
        except Exception as e:
            logging.warning(f"Failed to load token counts: {e}")
            self.total_tokens = 0
            self.session_tokens = 0

    def _save_token_counts(self):
        """Save current token counts to persistent storage."""
        try:
            data = {
                "total_tokens": self.total_tokens,
                "session_tokens": self.session_tokens,
                "last_updated": datetime.now().isoformat()
            }

            if self.use_gcs and self.bucket_name:
                # Save to GCS
                client = storage.Client()
                bucket = client.get_bucket(self.bucket_name)
                blob = bucket.blob("token_counts.json")
                blob.upload_from_string(json.dumps(data, indent=2))
            else:
                # Save to local file
                count_file = Path(self.log_file).parent / "token_counts.json"
                with open(count_file, 'w') as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            logging.warning(f"Failed to save token counts: {e}")

    def log_token_usage(self, tokens_used: int, model: str, operation: str, metadata: Optional[Dict] = None):
        """Log token usage for an operation.

        Args:
            tokens_used: Number of tokens consumed
            model: The model used (e.g., 'gemini-2.5-flash')
            operation: Description of the operation
            metadata: Additional metadata to log
        """
        # Update counters
        self.session_tokens += tokens_used
        self.total_tokens += tokens_used

        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "operation": operation,
            "tokens_used": tokens_used,
            "session_total": self.session_tokens,
            "cumulative_total": self.total_tokens,
            "metadata": metadata or {}
        }

        # Log to console
        logging.info(f"Token usage - {operation}: {tokens_used} tokens (Session: {self.session_tokens}, Total: {self.total_tokens})")

        # Save to file or GCS
        try:
            if self.use_gcs and self.bucket_name:
                # Save to GCS
                client = storage.Client()
                bucket = client.get_bucket(self.bucket_name)
                blob = bucket.blob(f"token_logs/{datetime.now().strftime('%Y-%m-%d')}.jsonl")
                current_content = ""
                if blob.exists():
                    current_content = blob.download_as_text()
                updated_content = current_content + json.dumps(log_entry) + "\n"
                blob.upload_from_string(updated_content)
            else:
                # Save to local file
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logging.error(f"Failed to log token usage: {e}")

        # Save updated counts
        self._save_token_counts()

    def get_usage_stats(self, days: int = 7) -> Dict:
        """Get token usage statistics for the specified number of days.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with usage statistics
        """
        stats = {
            "session_tokens": self.session_tokens,
            "total_tokens": self.total_tokens,
            "daily_usage": {},
            "model_breakdown": {}
        }

        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            if self.use_gcs and self.bucket_name:
                # Read from GCS
                client = storage.Client()
                bucket = client.bucket(self.bucket_name)

                # Get all log files for the date range
                blobs = bucket.list_blobs(prefix="token_logs/")
                for blob in blobs:
                    if blob.name.endswith('.jsonl'):
                        file_date_str = blob.name.split('/')[-1].replace('.jsonl', '')
                        try:
                            file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                            if file_date >= cutoff_date.date():
                                content = blob.download_as_text()
                                for line in content.strip().split('\n'):
                                    if line:
                                        entry = json.loads(line)
                                        self._process_log_entry_for_stats(entry, stats)
                        except ValueError:
                            continue
            else:
                # Read from local file
                if Path(self.log_file).exists():
                    with open(self.log_file, 'r') as f:
                        for line in f:
                            if line.strip():
                                entry = json.loads(line)
                                entry_date = datetime.fromisoformat(entry['timestamp'])
                                if entry_date >= cutoff_date:
                                    self._process_log_entry_for_stats(entry, stats)

        except Exception as e:
            logging.warning(f"Failed to read usage stats: {e}")

        return stats

    def _process_log_entry_for_stats(self, entry: Dict, stats: Dict):
        """Process a log entry for statistics calculation."""
        date_key = entry['timestamp'][:10]  # YYYY-MM-DD
        model = entry['model']
        tokens = entry['tokens_used']

        # Daily usage
        if date_key not in stats['daily_usage']:
            stats['daily_usage'][date_key] = 0
        stats['daily_usage'][date_key] += tokens

        # Model breakdown
        if model not in stats['model_breakdown']:
            stats['model_breakdown'][model] = 0
        stats['model_breakdown'][model] += tokens

    def reset_session(self):
        """Reset session token counter."""
        self.session_tokens = 0
        self._save_token_counts()
        logging.info("Token session counter reset")

# Global token tracker instance
_token_tracker = None

def get_token_tracker(log_file: Optional[str] = None, use_gcs: bool = False, bucket_name: Optional[str] = None) -> TokenTracker:
    """Get or create the global token tracker instance."""
    global _token_tracker
    if _token_tracker is None:
        _token_tracker = TokenTracker(log_file, use_gcs, bucket_name)
    return _token_tracker