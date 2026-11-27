import java.util.*;

class Solution {
    public String longestPalindrome(String s) {
        int start = 0, end = 0;
        for (int i = 0; i < s.length(); i++) {
            for (int[] range : new int[][] {expand(s, i, i), expand(s, i, i + 1)}) {
                if (range[1] - range[0] > end - start) {
                    start = range[0];
                    end = range[1];
                }
            }
        }
        return s.substring(start, end);
    }

    private int[] expand(String s, int lo, int hi) {
        while (lo >= 0 && hi < s.length() && s.charAt(lo) == s.charAt(hi)) {
            lo--;
            hi++;
        }
        return new int[] {lo + 1, hi};
    }
}
