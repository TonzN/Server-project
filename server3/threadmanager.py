from loads import * 
import threading
import queue
import traceback
import itertools
import server3.datapacket_manager as dc

"""YALALALALAL im not working on this right now
"""

class WorkerThread:
    def __init__(self, target, *args):
        self.target = target
        self.args = args
        self.thread = None
        self.thread_id = None
        self.start_time = None
        self.end_time = None
        self.stop_event = threading.Event()
        self.status = "initialized"
        self.return_value = None
    
    def stop(self):
        """Signal the thread to stop."""
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=1)  # Wait for the thread to finish
            if self.thread.is_alive():
                print(f"\nThread {self.thread.name} is still running, forcing stop...")
                self._force_stop()
                print(f"Thread {self.thread.name} has been stopped.\n")

        self.end_time = time.time()
        self.status = "Stopped"
    
    def _run(self):
        """Run the target function."""
        try:
            
            self.thread_id = self.thread.ident
            self.start_time = time.time()
            self.status = "Running"
            result = self.target(self.stop_event, *self.args)
            self.status = "Finished"
            return result

        except Exception as e:
            print(f"Error in thread {self.thread.name}: {e}")
            traceback.print_exc()
        finally:
            self.end_time = time.time()
            self.status = "Finished"

    def start(self):
        """Start the thread."""
        if self.target:
            self.thread = threading.Thread(target=self._run, args=self.args)
            self.thread.start()
        else:
            raise ValueError("WorkerThread->Start-> No target function provided for the thread.")

    def is_alive(self):
        """Check if the thread is still running."""
        return self.thread.is_alive()

    def get_runtime(self):
        """Get the runtime of the thread."""
        if self.start_time:
            return (self.end_time or time.time()) - self.start_time
        return 0

class ThreadScheduler:
    """A class to manage a pool of threads for handling tasks.
    Handles scheduling and queueing of threads."""
    pass

    
class ThreadManager:
    """A class to manage threads for handling tasks.
    \nIt allows for dynamic threading, scheduling tasks, and managing thread pools."""

    def __init__(self):
        self.scheduler = ThreadScheduler()
        self.auto_threading = False
        self.max_threads = 10  # Set a maximum number of threads to prevent overloading
    
    def set_max_threads(self, max_threads):
        """Set the maximum number of threads."""
        self.max_threads = max_threads
    
    def start_thread(self, target, *args):
        """Start a new thread with the given target function and arguments."""
        thread = WorkerThread(target, *args)
        thread.start()
        self.worker_threads.append(thread)
    
    def schedule_task(self, task, *args):
        """Schedule a task to be run in a thread. 
        \nIf auto_threading is enabled, the task will be added to the queue.
        \nIf auto_threading is disabled and the number of threads is less than max_threads, 
        \nthe task will be run immediately in a new thread."""
        pass

    def _dispatcher(self, task, *args):
        pass

    
    def dynamic_threading(self, enable):
        pass
    
    def thread_pool(self):
        pass

    def thread_status(self):
        pass
        
    def auto_thread(self):
        """Automatically run scheduled tasks in separate threads."""
        pass

    def join_threads(self):
        """Wait for all threads to finish."""
        for thread in self.worker_threads:
            thread.join()

    def find_thread(self, thread_id):
        pass

    def stop_threads(self):
        """Stop all threads."""
        pass
