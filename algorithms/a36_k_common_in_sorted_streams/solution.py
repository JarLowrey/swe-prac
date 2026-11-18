import heapq


class Solution:
    def kCommon(self, streams: list[list[int]], k: int) -> list[int]:
        # Read each stream only from the front, one value at a time, as if it were a live feed.
        feeds = [iter(stream) for stream in streams]

        # One entry per stream that still has values: (head, stream index). The heap never holds
        # more than x entries, however long the streams are.
        heap = []
        for i, feed in enumerate(feeds):
            head = next(feed, None)  # None marks the end: values are numbers, never None
            if head is not None:
                heap.append((head, i))
        heapq.heapify(heap)

        found = []
        # With fewer than k streams left, every unread value is in fewer than k streams.
        while len(heap) >= k:
            # The smallest head is the smallest value not handled yet. Every stream containing
            # it has it at the front right now (their smaller values are all handled).
            value = heap[0][0]
            count = 0
            while heap and heap[0][0] == value:
                _, i = heapq.heappop(heap)
                count += 1  # each stream has one entry, so this counts streams, not copies
                head = next(feeds[i], None)
                while head == value:  # skip this stream's other copies of value
                    head = next(feeds[i], None)
                if head is not None:
                    heapq.heappush(heap, (head, i))  # the stream's next, larger value
            if count >= k:
                found.append(value)
        return found
