Koko has `piles` of bananas: pile `i` holds `piles[i]` bananas. She has `h` hours to eat them
all, and she chooses an eating speed of `k` bananas per hour.

Each hour she picks one pile and eats `k` bananas from it. If the pile has fewer than `k` left,
she finishes it and rests for the rest of that hour: she never starts a second pile in the same
hour.

Return the smallest whole number `k` that lets her finish every pile within `h` hours. There are
never more piles than hours, so an answer always exists.

**Example 1**

```
Input:  piles = [3, 5, 11], h = 6
Output: 4
```

At speed 4 the piles take 1, 2 and 3 hours: 6 in total, which fits. At speed 3 they take 1, 2
and 4 hours, 7 in total: too slow.

```array
label: piles
values: 3 5 11
---
label: hours
values: 1 2 3
caption: at k = 4: 1 + 2 + 3 = 6 hours, exactly h
```

**Example 2**

```
Input:  piles = [1, 2, 3, 100], h = 4
Output: 100
```

Four piles in four hours is one hour per pile, so she must eat the largest pile, 100 bananas, in
one hour.

**Example 3**

```
Input:  piles = [3, 6], h = 100
Output: 1
```

Even at 1 banana an hour she needs only 9 hours.

**Constraints**

- `1 <= len(piles) <= 10^4`
- `len(piles) <= h <= 10^9`
- `1 <= piles[i] <= 10^9`
