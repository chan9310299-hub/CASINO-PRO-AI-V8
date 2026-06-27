class UndoEngine:

    def __init__(self):
        self.stack = []

    def push(self, result):
        self.stack.append(result)

    def pop(self):
        if len(self.stack) == 0:
            return None

        return self.stack.pop()

    def clear(self):
        self.stack.clear()

    def size(self):
        return len(self.stack)

    def is_empty(self):
        return len(self.stack) == 0