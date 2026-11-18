## Understand the problem

Pick a buy day and a later sell day; the profit is the sell price minus the buy price. We want
the largest profit, or 0 if every possible trade loses money (we can simply not trade).

| `prices` | Answer | Why |
|---|---|---|
| `[7, 1, 5, 3, 6, 4]` | 5 | buy at 1, sell at 6 |
| `[7, 6, 4, 3, 1]` | 0 | every later price is lower: don't trade |
| `[5, 9, 1]` | 4 | buy at 5, sell at 9; the 1 comes too late to buy |
| `[2, 4, 1, 3]` | 2 | two different trades tie, and either is fine |
| `[]`, `[5]` | 0 | there is no pair of days |

The trap is the tempting shortcut `max(prices) - min(prices)`. It ignores the order of the days:

```array
label: prices
values: 5 9 1
highlight: 1 2
caption: max - min = 9 - 1 = 8, but the 1 comes after the 9
---
label: prices
values: 5 9 1
pointers: buy=0 sell=1
highlight: 0 1
caption: the real answer: buy at 5, sell at 9, profit 4
```

## Brute force: try every pair of days

```python
best = 0
for i in range(len(prices)):  # buy day
    for j in range(i + 1, len(prices)):  # a later sell day
        best = max(best, prices[j] - prices[i])
return best
```

Picture every trade as a table: row `i` is the buy day, column `j` the sell day, and each cell
above the diagonal is that trade's profit. The brute force fills in the whole triangle and takes
the largest cell.

```grid
collabels: 7 1 5 3 6 4
rowlabels: 7 1 5 3 6 4
_ -6 -2 -4 -1 -3
_ _ 4 2 5 3
_ _ _ -2 1 -1
_ _ _ _ 3 1
_ _ _ _ _ -2
_ _ _ _ _ _
highlight: 1,4
caption: rows are buy prices, columns sell prices; the best cell is 6 - 1 = 5
```

That is n(n-1)/2 cells: **O(n²) time**, O(1) space. With 10^5 days it's 5 billion trades, far
too slow. But the table shows where the waste is.

## The key insight: buy at the lowest price before the sell day

Look at one column at a time. Fixing the sell day fixes the sell price, so the best cell in the
column is the one with the **lowest buy price** above it. We don't need the rest of the column.

```grid
collabels: 7 1 5 3 6 4
rowlabels: 7 1 5 3 6 4
_ -6 -2 -4 -1 -3
_ _ 4 2 5 3
_ _ _ -2 1 -1
_ _ _ _ 3 1
_ _ _ _ _ -2
_ _ _ _ _ _
dim: 0,1 0,2 0,3 0,5 1,2 1,3 1,5 2,3 2,5 3,5 4,5
highlight: 1,4
caption: selling at 6: the best buy is the cheapest earlier price, 1
```

And "the lowest price before day `j`" is easy to keep up to date as we walk forward: it's the
lowest price before day `j - 1`, or the price on day `j - 1` if that is lower. So one pass
keeps two numbers, the lowest price so far and the best profit so far. This is the
[running state](#/algo/learn/patterns/running-state-in-one-pass) pattern: carry a small summary
of everything to the left instead of looking back at it.

```array
label: prices
values: 7 1 5 3 6 4
pointers: low=0 i=0
caption: day 0: lowest = 7, selling today earns 0, best = 0
---
values: 7 1 5 3 6 4
pointers: low=1 i=1
caption: day 1: 1 is a new low; selling today earns 0, best = 0
---
values: 7 1 5 3 6 4
pointers: low=1 i=2
highlight: 1 2
caption: day 2: 5 - 1 = 4, best = 4
---
values: 7 1 5 3 6 4
pointers: low=1 i=3
caption: day 3: 3 - 1 = 2, best stays 4
---
values: 7 1 5 3 6 4
pointers: low=1 i=4
highlight: 1 4
caption: day 4: 6 - 1 = 5, best = 5
---
values: 7 1 5 3 6 4
pointers: low=1 i=5
caption: day 5: 4 - 1 = 3, best stays 5
```

Here is the same walk as a table for `[3, 2, 1, 4]` (Example 3). The low keeps falling, and the
profit only appears on the last day:

```grid
collabels: "day 0" "day 1" "day 2" "day 3"
rowlabels: price lowest "sell now" best
3 2 1 4
3 2 1 1
0 0 0 3
0 0 0 3
highlight: 3,3
caption: best never goes below 0: not trading is always an option
```

## The solution

```python
class Solution:
    def maxProfit(self, prices: list[int]) -> int:
        lowest = float("inf")  # cheapest price so far; infinity before the first day
        best = 0  # "don't trade" is always allowed
        for price in prices:
            lowest = min(lowest, price)
            best = max(best, price - lowest)
        return best
```

Why it's correct: the best trade sells on some day `j` and, for that day, must buy at the lowest
price on or before `j`. When the loop reaches day `j`, `lowest` is exactly that price, so
`price - lowest` is the best trade selling on day `j`. `best` is the maximum over all days.

Updating `lowest` before computing the profit means that on a new low we "buy and sell the same
day" for a profit of 0. That's harmless because `best` starts at 0, and it lets one line handle
the first day. Starting `lowest` at infinity, rather than `prices[0]`, also handles an empty
array without a special case.

## Complexity

- **Time: O(n).** One pass, constant work per day.
- **Space: O(1).** Two numbers, however long the array is.

## Pitfalls and variations

- **`max(prices) - min(prices)`** ignores the order of the days (`[5, 9, 1]` gives 8, not 4).
- **Negative answers.** Starting `best` at minus infinity, or at `prices[1] - prices[0]`, returns
  a loss for a falling market. The problem allows not trading, so the answer is at least 0.
- **`prices[0]` on an empty array** raises an `IndexError`. Infinity as the starting low avoids it.
- **Return the days too:** remember the index where `lowest` was set, and copy it when `best`
  improves.
- **The same problem in disguise.** The daily changes of `[7, 1, 5, 3, 6, 4]` are
  `[-6, 4, -2, 3, -2]`, and a trade's profit is the sum of the changes it holds through. So the
  answer is the largest sum of a contiguous run of changes (the maximum subarray problem, solved by
  Kadane's algorithm, another running-state pass):

```array
label: change
values: -6 4 -2 3 -2
highlight: 1..3
caption: hold from day 1 to day 4: 4 - 2 + 3 = 5
```

- **Unlimited trades** (one share at a time): add up every positive daily change. That's
  [greedy](#/algo/learn/patterns/greedy): every rise is worth taking.
- **At most two trades, or k trades, a cooldown day after selling, or a fee per trade:** each
  becomes a small dynamic program over "holding" and "not holding" states, the same shape as
  [House Robber](#/algo/problem/a33_house_robber).
