from telegram_notifier import send_alert

def generate_summary(profit_tracker):
    """
    Sends daily profit summary to Telegram
    """
    report = profit_tracker.report()
    msg = "📊 Daily Oracle Bot Summary:\n"
    for job_name, amount in report.items():
        msg += f"- {job_name}: ${amount:.2f}\n"
    msg += f"💰 Total: ${profit_tracker.total():.2f}"
    send_alert(msg)
