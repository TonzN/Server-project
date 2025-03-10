from loads import *
from client.loads import *
import threading
import traceback

def check_threads():
    print("Active threads:", threading.enumerate())
    list_running_coroutines()
   # debug_stuck_coroutines()
    check_zombie_threads()
  #  dump_stuck_thread()

def dump_stuck_thread():
    for thread in threading.enumerate():
        if thread.name.startswith("asyncio_"):
            print(f"\n🔍 Debugging {thread.name}...")

            for thread_id, frame in sys._current_frames().items():
                if thread.ident == thread_id:
                    print("🔍 Stack trace of stuck thread:")
                    traceback.print_stack(frame)

def check_zombie_threads():
    for thread in threading.enumerate():
        if thread.name.startswith("asyncio_") or thread.name.startswith("Thread-"):
            print(f"⚠️ Possible zombie thread detected: {thread.name} (Alive: {thread.is_alive()})")

def debug_stuck_coroutines():
    try:
        loop = asyncio.get_event_loop()
        tasks = [task for task in asyncio.all_tasks() if not task.done()]
    
    except Exception as e:
        return

    if tasks:
        print(f"⚠️ {len(tasks)} stuck coroutine(s) found:")
        for task in tasks:
            print(f" - {task.get_coro()} (State: {task._state})")

    return tasks

def list_running_coroutines():
    try:
        loop = asyncio.get_event_loop()
        
        tasks = [task for task in asyncio.all_tasks() if not task.done()]
    except Exception as e:
        print("no running courotines")
        return
    
    print(f"⚠️ {len(tasks)} running coroutine(s) detected:")

    for task in tasks:
        coro = task.get_coro()  # Get coroutine object
        print(f"🔹 Coroutine: {coro} (State: {task._state})")

        # Extract where the coroutine was created
        frames = traceback.extract_stack(coro.cr_frame)
        print("🔍 Origin trace:")
        for frame in frames[-5:]:  # Show last 5 calls
            print(f"  📌 {frame.filename}:{frame.lineno} in {frame.name}")
        print("-" * 50)


class _Thread_Class:
    def __init__(self, target):
        self.stop = threading.Event()
        self.thread = threading.Thread(target=target, args=None, daemon=True)
        self.running_functions = []
        self.args = ()
    
    def run(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass

    def connect_function(self, func, is_async=False):
        pass

class Worker_Thread(_Thread_Class):
    def __init__(self):
        self.type = "normal"

class Q_Thread(QThread):
    def __init__(self, target):
        super.__init__(self, target)
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