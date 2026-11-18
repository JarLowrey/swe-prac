class Solution:
    def isValid(self, s: str) -> bool:
        # Each closing bracket must close the most recently opened bracket that is still open:
        # last in, first out, so the open brackets go on a stack.
        opener = {")": "(", "]": "[", "}": "{"}  # closing bracket -> the opener it closes
        stack: list[str] = []
        for c in s:
            if c in opener:  # a closing bracket
                # Check for an empty stack first: pop() on [] raises IndexError (input ")").
                if not stack or stack.pop() != opener[c]:
                    return False
            else:
                stack.append(c)  # an opening bracket waits for its partner
        # Openers left on the stack were never closed (input "((").
        return not stack
