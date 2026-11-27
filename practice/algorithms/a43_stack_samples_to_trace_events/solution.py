class Solution:
    def convert(self, samples: list[tuple[int, list[str]]]) -> list[tuple[str, int, str]]:
        events: list[tuple[str, int, str]] = []
        prev: list[str] = []  # the previous sample's stack; empty before the first sample
        for time, stack in samples:
            # A frame is the same call in both samples only if it and all its callers match:
            # that holds exactly for the longest common prefix of the two stacks.
            common = 0
            limit = min(len(prev), len(stack))
            while common < limit and prev[common] == stack[common]:
                common += 1
            # prev's frames above the prefix have returned. Walk them backwards so the
            # innermost call ends first (a callee returns before its caller).
            events.extend(("end", time, name) for name in reversed(prev[common:]))
            # stack's frames above the prefix are new calls: outermost first (a caller is
            # entered before the functions it calls).
            events.extend(("start", time, name) for name in stack[common:])
            prev = stack
        # Calls still on the last stack get no end event: we never see them return.
        return events
