class Solution:
    def threeSum(self, nums: list[int]) -> list[list[int]]:
        # Sorting lets two pointers find each pair in O(n) (instead of a set per first number),
        # and puts equal values next to each other, so repeated triplets are easy to skip.
        nums = sorted(nums)  # a sorted copy: the caller's list is left alone
        n = len(nums)
        triplets: list[list[int]] = []

        for i in range(n - 2):  # empty when there are fewer than three numbers
            if nums[i] > 0:
                break  # the smallest of the three is positive, so no total can be 0
            if i > 0 and nums[i] == nums[i - 1]:
                # Same first value as the previous i: every pair it could use, the previous i
                # could use too. Keep the FIRST copy, so [-1, -1, 2] is still found.
                continue

            # Two Sum on the sorted rest of the array: find nums[lo] + nums[hi] == -nums[i].
            lo, hi = i + 1, n - 1
            while lo < hi:
                total = nums[i] + nums[lo] + nums[hi]
                if total < 0:
                    lo += 1  # too small even with the largest partner left: drop nums[lo]
                elif total > 0:
                    hi -= 1  # too big even with the smallest partner left: drop nums[hi]
                else:
                    triplets.append([nums[i], nums[lo], nums[hi]])
                    # Step past every copy of both values, or this triplet is found again.
                    low_value, high_value = nums[lo], nums[hi]
                    while lo < hi and nums[lo] == low_value:
                        lo += 1
                    while lo < hi and nums[hi] == high_value:
                        hi -= 1

        return triplets
