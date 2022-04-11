## Handler class as the model

from pymemcache.client import base
import json
import yaml
import time
import pandas as pd

empty_df = pd.DataFrame({
        'Time': [0],
        'Reading': [0],
        'Sensor': [0]
    })

class Handler(object):

    shared = base.Client(('localhost', 11211))
    log = empty_df
    inst = 0
    new_data_available = False
    last_data = {'reading': 0.0, 'sensor': 0}

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Handler, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        super(Handler, self).__init__()
        Handler.inst = Handler.inst + 1  # debug info
        self.update_log_file()

    def available(self):
        try:
            res = self.shared.get('new_data')
            if res is not None:
                if res == b'1':
                    self.new_data_available = True
                    n = self.shared.get('data').decode("utf-8")
                    self.last_data = yaml.load(n)
                else:
                    self.new_data_available = False
        except:
            pass

        if self.new_data_available:
            print("INFO/Handler: New data available", Handler.last_data)
            try:
                self.shared.replace('new_data', 0)
            except:
                print('WARNING/Handler: Cannot unset new_data flag')
        return self.new_data_available

    def last_log_values(self, n):
        self.update_log_file()
        l = self.log.loc[self.log["Sensor"] == n][-20:]
        if len(l) < 1:
            l = [0, 0]
        return l

    def update_log_file(self):
        date = time.strftime("%d%b%y", time.localtime())
        todays_log_path = date + ".csv"
        try:
            self.log = pd.read_csv(todays_log_path, index_col=False)
        except:
            print('WARNING/Handler: No log file for today')