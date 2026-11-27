**Hint 1.** The brute force multiplies the other n - 1 numbers for every index: O(n²). Dividing
the total product by `nums[i]` is forbidden, and it would break on zeros anyway.

**Hint 2.** Split "everything except `nums[i]`" into two parts: everything to the **left** of `i`,
and everything to the **right** of `i`. The answer is their product.

**Hint 3.** The product of everything left of `i + 1` is the product left of `i`, times
`nums[i]`. So all the left products come out of one pass from the left, and all the right
products out of one pass from the right.

**Hint 4.** For O(1) extra space, store the left products in the answer array itself, then sweep
from the right with a single running product, multiplying it into each slot. In both passes,
use the running product *before* multiplying `nums[i]` into it, so `nums[i]` is never included.
