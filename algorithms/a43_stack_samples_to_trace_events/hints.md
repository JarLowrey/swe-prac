**Hint 1.** Work Example 3 by hand. When is a frame in one sample "the same call" as a frame in
the next? Same name isn't enough, and neither is same name at the same depth.

**Hint 2.** A frame is the same call only if it *and everything below it* (all its callers)
match. So walk the two stacks from the outermost frame while they agree: the longest common
prefix. Everything above it in the previous stack ended; everything above it in the current
stack started.

**Hint 3.** Keep the previous sample's stack in a variable, starting with `[]`. For each sample:
compute the prefix length, emit the ends by walking the previous stack from its top down to the
prefix, then the starts by walking the current stack from the prefix up to its top.

**Hint 4.** Check the edges: identical stacks (the prefix is everything, so nothing is emitted),
an empty stack (every frame ends), recursion like `["f", "f"]`, and the last sample (emit
nothing extra after the loop).
