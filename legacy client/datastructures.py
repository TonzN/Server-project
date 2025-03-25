import asyncio


class Queue:    
    def __init__(self):
        self.queue = []
        self.event = asyncio.Event()  # Event to signal new data
        self.max_wait_time = 5  # Maximum wait time (seconds)

    async def get(self):
        while not self.queue:
            # If the event is already set, no need to wait; just proceed
            if self.event.is_set():
                self.event.clear()  # Clear the event immediately since we're proceeding
                break  # Proceed with the queue processing

            try:
                # Wait for the event to be set with a timeout
                await asyncio.wait_for(self.event.wait(), timeout=5)
            except asyncio.TimeoutError:
                return None  # Timeout occurred; return None if no message is available

            self.event.clear()  # Clear the event after being notified

        return self.queue.pop(0)

    def put(self, item):
        self.queue.append(item)
        self.event.set()  # Notify waiting consumers
        print("set")

class Stack:
    def __init__(self):
        self.stack = []

    def Pop(self):
        x = self.stack[len(self.stack)-1]
        self.stack.pop(len(self.stack)-1)
        return x
    
    def Push(self, Input):
        self.stack.append(Input)

