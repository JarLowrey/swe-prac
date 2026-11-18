**Hint 1.** Start with recursion: from index `i`, try every jump from 1 to `nums[i]`, and
memoise which indices can reach the end. That's correct, but O(n²) in the worst case. What is it
really computing?

**Hint 2.** Always taking the biggest jump fails: on `[3, 0, 5, 0, 0, 0]` it lands on a 0 and
gets stuck, while a jump of 2 reaches the 5. So don't commit to any one jump. Track everything
you *could* reach instead.

**Hint 3.** If you can reach index `j`, you can also reach every index before it: some jump on
the way passes over it, and a shorter jump from the same place lands on it. So the reachable
indices are always `0..reach`, one unbroken prefix, and `reach` is the only number you need.

**Hint 4.** Walk `i` from left to right. If `i > reach`, nothing can get to `i`, so return
`False`. Otherwise extend `reach = max(reach, i + nums[i])`. If you get through the array, the
last index was reachable.
