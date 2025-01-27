class Queue:    
    def __init__(self, Input = []):
        self.queue = Input

    def Pop(self):
        x = self.queue[0]
        self.queue.pop(0)
        return x
    
    def Push(self, Input):
        self.queue.append(Input)

class Stack:
    def __init__(self, Input = []):
        self.stack = Input

    def Pop(self):
        x = self.stack[len(self.stack)-1]
        self.stack.pop(len(self.stack)-1)
        return x
    
    def Push(self, Input):
        self.stack.append(Input)