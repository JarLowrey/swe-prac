## Understand the problem

Each output slot is the product of all the *other* numbers. The obvious idea, multiply everything
once and divide by `nums[i]`, is ruled out, and it would fail anyway: with a zero in the array
the total is 0, and you can't divide by the zero itself.

| `nums` | `answer` | Why |
|---|---|---|
| `[1, 2, 3, 4]` | `[24, 12, 8, 6]` | |
| `[1, 2, 0, 4]` | `[0, 0, 8, 0]` | one zero: only its own slot avoids it |
| `[0, 2, 0]` | `[0, 0, 0]` | two zeros: every product includes at least one |
| `[3, 4]` | `[4, 3]` | each slot gets the other number |
| `[5]` | `[1]` | the product of no numbers is 1, just as the sum of no numbers is 0 |
| `[]` | `[]` | |

## Brute force: multiply the others for every index

```python
answer = []
for i in range(len(nums)):
    product = 1
    for j in range(len(nums)):
        if j != i:
            product *= nums[j]
    answer.append(product)
return answer
```

That is n - 1 multiplications for each of n slots: **O(n²) time**. For n = 10^5 it's 10 billion
multiplications. Notice how much work repeats: neighbouring slots share almost all their
factors.

```array
label: nums
values: 1 2 3 4
pointers: i=1
highlight: 0 2 3
caption: answer[1] = 1 × 3 × 4
---
label: nums
values: 1 2 3 4
pointers: i=2
highlight: 0 1 3
caption: answer[2] = 1 × 2 × 4: the 1 and the 4 are multiplied again
```

## The key insight: what's left of i, times what's right of i

"Everything except `nums[i]`" is two pieces: everything to the left of `i`, and everything to
the right. Multiplication is associative, so we can multiply each piece on its own and then
combine them:

```array
label: nums
values: 1 2 3 4 5
pointers: i=2
highlight: 0 1 3 4
caption: answer[2] = (1 × 2) × (4 × 5) = 2 × 20 = 40
```

Call them `left[i]`, the product of `nums[0..i-1]`, and `right[i]`, the product of
`nums[i+1..n-1]`. Both are easy to build because each one extends its neighbour by a single
number:

- `left[0] = 1` (nothing to the left), and `left[i + 1] = left[i] × nums[i]`: one pass from the
  left.
- `right[n-1] = 1` (nothing to the right), and `right[i - 1] = right[i] × nums[i]`: one pass from
  the right.

These are [prefix products](#/algo/learn/patterns/prefix-sums-and-products), the multiplying twin
of prefix sums. They start at 1 because 1 is to multiplication what 0 is to addition: it changes
nothing.

```grid
collabels: 0 1 2 3
rowlabels: nums left right answer
1 2 3 4
1 1 2 6
24 12 4 1
24 12 8 6
highlight: 1,2 2,2 3,2
caption: answer[2] = left[2] × right[2] = 2 × 4 = 8
```

```python
n = len(nums)
left, right = [1] * n, [1] * n
for i in range(1, n):
    left[i] = left[i - 1] * nums[i - 1]
for i in range(n - 2, -1, -1):
    right[i] = right[i + 1] * nums[i + 1]
return [left[i] * right[i] for i in range(n)]
```

**O(n) time** (three passes) and O(n) extra space for the two arrays.

## Dropping the extra arrays

The follow-up asks for O(1) extra space, not counting the output. Two observations get there:

1. Build `left` directly in the answer array.
2. `right` is only ever read once per slot, in order from the right. So sweep from the right with
   a single running product and multiply it into each slot.

The left pass on `[1, 2, 3, 4]` (empty cells are not written yet):

```array
label: answer
values: 1 _ _ _
pointers: i=0
caption: answer[0] = left = 1, then left = 1 × 1 = 1
---
label: answer
values: 1 1 _ _
pointers: i=1
caption: answer[1] = left = 1, then left = 1 × 2 = 2
---
label: answer
values: 1 1 2 _
pointers: i=2
caption: answer[2] = left = 2, then left = 2 × 3 = 6
---
label: answer
values: 1 1 2 6
pointers: i=3
caption: answer[3] = left = 6: each slot now holds its left product
```

The right pass multiplies in the right products (finished slots highlighted):

```array
label: answer
values: 1 1 2 6
pointers: i=3
highlight: 3
caption: answer[3] = 6 × right(1) = 6, then right = 1 × 4 = 4
---
label: answer
values: 1 1 8 6
pointers: i=2
highlight: 2 3
caption: answer[2] = 2 × 4 = 8, then right = 4 × 3 = 12
---
label: answer
values: 1 12 8 6
pointers: i=1
highlight: 1..3
caption: answer[1] = 1 × 12 = 12, then right = 12 × 2 = 24
---
label: answer
values: 24 12 8 6
pointers: i=0
highlight: 0..3
caption: answer[0] = 1 × 24 = 24: done
```

The order inside each step is the whole trick: **use** the running product, **then** multiply
`nums[i]` into it. Swap the two lines and every slot includes its own number.

## The solution

```python
class Solution:
    def productExceptSelf(self, nums: list[int]) -> list[int]:
        n = len(nums)
        answer = [1] * n

        left = 1  # product of nums[0..i-1]
        for i in range(n):
            answer[i] = left
            left *= nums[i]

        right = 1  # product of nums[i+1..n-1]
        for i in range(n - 1, -1, -1):
            answer[i] *= right
            right *= nums[i]

        return answer
```

Why it's correct: at the start of step `i` of the first loop, `left` is the product of
`nums[0..i-1]`, so after the loop each `answer[i]` holds its left product. At the start of step
`i` of the second loop, `right` is the product of `nums[i+1..n-1]`, and multiplying it in makes
`answer[i]` the product of everything except `nums[i]`. Tiny inputs need no special case: with
n = 0 both loops are skipped and `[]` is returned, and with n = 1 the answer is `[1 × 1] = [1]`.

## Zeros take care of themselves

```grid
collabels: 0 1 2 3
rowlabels: nums left right answer
1 2 0 4
1 1 2 0
0 0 4 1
0 0 8 0
highlight: 0,2 3,2
caption: the 0 wipes out every product that crosses it
```

A zero makes every left product after it 0 and every right product before it 0, so only the
zero's own slot can be nonzero. With two zeros, every slot has a zero on at least one side, and
the answer is all zeros. The division approach needs special cases for exactly these inputs; the
prefix approach needs none.

## Complexity

- **Time: O(n).** Two passes with constant work per element.
- **Space: O(1) extra.** Two running products. The answer array is the output; say out loud that
  you're not counting it. If the interviewer does count it, it's O(n), and nothing can do better,
  since the output itself has n numbers.

The two-array version is also O(n) time, with O(n) extra space. It's a fine first answer: get it
working, then remove the arrays.
See [space complexity](#/algo/learn/complexity/space-complexity) for what counts.

## Pitfalls and variations

- **Updating the running product before writing the slot**, which multiplies `nums[i]` into its
  own answer.
- **Special-casing small inputs.** Returning `nums` itself when it has one element is wrong:
  `[5]` gives `[1]`. The loops already handle 0 and 1 elements.
- **If division were allowed**, count the zeros first. No zeros: `total // x` for each slot
  (exact, since `x` divides the total; floating-point `/` would lose precision on big products).
  One zero: every slot is 0 except the zero's, which gets the product of the rest. Two or more
  zeros: all 0.
- **Overflow.** In a language with fixed-size integers, the guarantee that every prefix and suffix
  product fits in 32 bits is what makes this safe. Python's integers never overflow.
- **Prefix sums** are the same idea with `+` and 0: the sum of `nums[i..j]` is
  `prefix[j + 1] - prefix[i]`, an O(1) answer to any range-sum query after an O(n) pass.
- **The same left-and-right split** shows up elsewhere: trapping rain water needs the tallest bar
  to the left and to the right of each position, built with one pass from each side.
  [Best Time to Buy and Sell Stock](#/algo/problem/a03_best_time_to_buy_and_sell_stock) carries a
  running summary of the left side only.
