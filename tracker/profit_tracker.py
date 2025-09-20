from collections import defaultdict

class ProfitTracker:
    """
    Tracks profits per job (harvest + oracle)
    """
    def __init__(self):
        self.data = defaultdict(float)

    def add_profit(self, job_name, amount):
        self.data[job_name] += amount

    def total(self):
        return sum(self.data.values())

    def report(self):
        return dict(self.data)
