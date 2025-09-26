import os
import logging
import datetime
from telegram_notifier import send_alert

logger = logging.getLogger("SummaryReporter")

class SummaryReporter:
    def __init__(self, config):
        self.config = config
        self.successes = []
        self.failures = []

    def log_success(self, watcher, tx_hash):
        msg = f"✅ {watcher['name']} harvested tx={tx_hash}"
        self.successes.append(msg)

    def log_failure(self, watcher, error):
        msg = f"❌ {watcher['name']} failed: {error}"
        self.failures.append(msg)

    def send_daily_summary(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        summary = [f"📊 Daily Summary ({now})"]

        if self.successes:
            summary.append("✅ Successes:")
            summary.extend(self.successes)
        if self.failures:
            summary.append("❌ Failures:")
            summary.extend(self.failures)

        if not self.successes and not self.failures:
            summary.append("No activity today.")

        message = "\n".join(summary)
        logger.info(message)
        if self.config["telegram"]["enable_real_time_alerts"]:
            send_alert(message)

        # Reset logs after summary
        self.successes = []
        self.failures = []
