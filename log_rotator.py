import os
import shutil
import datetime

LOG_FILE = "logs/profit_log.csv"

def rotate_logs():
    """
    Moves profit_log.csv to archive monthly and creates a new log
    """
    if not os.path.exists(LOG_FILE):
        return
    now = datetime.datetime.now()
    archive_file = f"logs/profit_log_{now.strftime('%Y_%m')}.csv"
    shutil.move(LOG_FILE, archive_file)
    open(LOG_FILE, "w").close()
