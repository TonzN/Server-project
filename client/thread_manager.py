from loads import *
from client.loads import *

class _Thread_Class:
    def __init__(self):
        self.stop = None
        self.running_functions = []

    def stop(self):
        pass

    def close(self):
        pass

    def connect_function(self, func, is_async=False):
        pass

class Thread(_Thread_Class):
    def __init__(self):
        self.type = "normal"

class Q_Thread(QThread):
    def __init__(self):
        self.signal = None

class Thread_Manager:
    def __init__(self):
        self.threads = []
        self.threads_info = {}

    def new_thread(self):
        pass

    def start_thread(self):
        pass

    def status(self):
        pass

    def close_threads(self):
        pass

    def force_close(self):
        pass

    def revive(self):
        pass