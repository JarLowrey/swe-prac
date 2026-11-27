You are given an array `coins` of different coin values and an `amount` of money. Return the
fewest coins needed to make up exactly `amount`. You have an unlimited supply of every coin.

If no combination of the coins adds up to `amount`, return `-1`.

**Example 1**

```
Input:  coins = [1, 2, 5], amount = 11
Output: 3
```

`11 = 5 + 5 + 1`. No two coins add up to 11.

**Example 2**

```
Input:  coins = [2], amount = 3
Output: -1
```

Only even amounts can be made from 2s.

**Example 3**

```
Input:  coins = [1], amount = 0
Output: 0
```

An amount of 0 needs no coins at all.

**Constraints**

- `1 <= len(coins) <= 12`
- `1 <= coins[i] <= 2^31 - 1`, and the values are all different
- `0 <= amount <= 10^4`
