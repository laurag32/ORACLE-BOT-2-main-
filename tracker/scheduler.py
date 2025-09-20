import schedule
from log_rotator import rotate_logs
from summary_reporter import generate_summary

def setup_schedules(schedule_time="23:55", profit_tracker=None):
    """
    Schedule daily summary and monthly log rotation
    """
    if profit_tracker:
        schedule.every().day.at(schedule_time).do(generate_summary, profit_tracker=profit_tracker)
    schedule.every().month.do(rotate_logs)
