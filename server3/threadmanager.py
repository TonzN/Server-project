from loads import * 
import threading
import queue
import dataclass as dc

class WorkerThread:
    def __init__(self, target=[], *args):
        self.schedule = [] # List to hold scheduled tasks: (target, args key)
        self.failed_tasks = [] # List to hold failed tasks: (target, args key)
        self.target = None
        self.args = {}
        self.thread = None
        self.thread_id = None
        self.start_time = None
        self.end_time = None
        self.stop_event = threading.Event()
        self.status = "initialized"
    
    def stop(self):
        """Signal the thread to stop."""
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=1)  # Wait for the thread to finish
            if self.thread.is_alive():
                print(f"Thread {self.thread.name} is still running, forcing stop...")
                self._force_stop()
    
    def _run_wrapper(self):
        """Wrapper function to track thread execution and handle stopping."""
        self.start_time = time.time()
        self.status = "Running"
        try:
            if not self.stop_event.is_set() and len(self.schedule) > 0:
                self.target(*self.a)
        except Exception as e:
            self.status = f"Error: {e}"
        finally:
            self.end_time = time.time()
            if self.status != "Error":
                self.status = "Completed"

    def start(self):
        """Start the thread."""
        self.thread.start()
        self.thread_id 

    def is_alive(self):
        """Check if the thread is still running."""
        return self.thread.is_alive()

    def get_runtime(self):
        """Get the runtime of the thread."""
        if self.start_time:
            return (self.end_time or time.time()) - self.start_time
        return 0

class ThreadPool:
    """A class to manage a pool of threads for handling tasks.
    Handles scheduling and queueing of threads."""
    pass

    
class ThreadManager:
    """A class to manage threads for handling tasks.
    \nIt allows for dynamic threading, scheduling tasks, and managing thread pools."""

    def __init__(self):
        self.worker_threads = []
        self.auto_threading = False
        self.max_threads = 10  # Set a maximum number of threads to prevent overloading
        self.scheduled_tasks = queue.Queue()  # List to hold scheduled ta
    
    def set_max_threads(self, max_threads):
        """Set the maximum number of threads."""
        self.max_threads = max_threads
    
    def start_thread(self, target, *args):
        """Start a new thread with the given target function and arguments."""
        thread = threading.Thread(target=target, args=args)
        thread.start()
        self.worker_threads.append(thread)
    
    def schedule_task(self, task, *args):
        """Schedule a task to be run in a thread. 
        \nIf auto_threading is enabled, the task will be added to the queue.
        \nIf auto_threading is disabled and the number of threads is less than max_threads, 
        \nthe task will be run immediately in a new thread."""
        if self.auto_threading:
            self.scheduled_tasks.put((task, args))
        elif len(self.worker_threads) < self.max_threads:
            self.start_thread(task, *args)
    
    def dynamic_threading(self, enable):
        pass

    def priority(self, task, *args):
        """Set the priority of a task."""
        # Implement priority logic here (e.g., using a priority queue)
        pass
    
    def thread_pool(self):
        pass

    def thread_status(self):
        pass

        
    def auto_thread(self):
        """Automatically run scheduled tasks in separate threads."""
        if self.auto_threading:
            while not self.scheduled_tasks.empty():
                if len(self.worker_threads) < self.max_threads:
                    try:
                        task, args = self.scheduled_tasks.get_nowait()
                    except queue.Empty:
                        break
                    self.start_thread(task, *args)
                    self.scheduled_tasks.task_done()
                else:
                    print("Max threads reached, waiting for a thread to finish...")
                    self.join_threads()

    def join_threads(self):
        """Wait for all threads to finish."""
        for thread in self.worker_threads:
            thread.join()

    def find_thread(self, thread_id):
        pass

    def stop_threads(self):
        """Stop all threads."""
        for thread in self.worker_threads:
            if thread.is_alive():
                thread.join(timeout=1)  # Wait for the thread to finish
                if thread.is_alive():
                    print(f"Thread {thread.name} is still running, terminating...")
                    thread._stop()  # Forcefully stop the thread (not recommended, but for demonstration purposes)

