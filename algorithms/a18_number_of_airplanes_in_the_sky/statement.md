You are given `airplanes`, where `airplanes[i] = [takeoff_i, landing_i]` gives the time plane `i`
takes off and the time it lands. Return the largest number of planes that are in the sky at the
same moment.

A plane is in the sky from its takeoff time up to, **but not including**, its landing time. So if
one plane lands at time `t` and another takes off at time `t`, they are never in the sky
together: the landing happens first.

**Example 1**

```
Input:  airplanes = [[1, 10], [2, 3], [5, 8], [4, 7]]
Output: 3
```

Between times 5 and 7, the planes `[1, 10]`, `[4, 7]` and `[5, 8]` are all flying.

```intervals
flights: [1,10] [2,3] [5,8] [4,7]
caption: stacked flights: the stack is three high between 5 and 7
```

**Example 2**

```
Input:  airplanes = [[1, 2], [2, 3], [3, 4]]
Output: 1
```

Each plane lands at the moment the next one takes off, so only one is ever in the sky.

**Example 3**

```
Input:  airplanes = [[1, 2], [1, 4]]
Output: 2
```

Both take off at time 1.

**Constraints**

- `0 <= len(airplanes) <= 10^4`
- `0 <= takeoff_i < landing_i <= 10^9`
