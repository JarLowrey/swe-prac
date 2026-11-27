You are given an array `prices`, where `prices[i]` is the price of a stock on day `i`. You may
buy one share on one day and sell it on a **later** day. Return the largest profit you can make.
If no trade makes money, return `0`: you don't have to trade.

**Example 1**

```
Input:  prices = [7, 1, 5, 3, 6, 4]
Output: 5
```

Buy on day 1 at price 1 and sell on day 4 at price 6, for a profit of 6 - 1 = 5. Buying at 1 and
selling at 7 is not allowed: day 0 comes before day 1, and you must buy before you sell.

```array
label: prices
values: 7 1 5 3 6 4
pointers: buy=1 sell=4
highlight: 1 4
caption: 6 - 1 = 5
```

**Example 2**

```
Input:  prices = [7, 6, 4, 3, 1]
Output: 0
```

The price only falls, so every trade loses money. Don't trade.

**Example 3**

```
Input:  prices = [3, 2, 1, 4]
Output: 3
```

Buy on day 2 at price 1 and sell on day 3 at price 4.

**Constraints**

- `0 <= len(prices) <= 10^5`
- `0 <= prices[i] <= 10^4`

**Follow-up:** checking every pair of days is O(n²). Can you do it in one pass?
