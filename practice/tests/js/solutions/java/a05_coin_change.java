import java.util.*;

class Solution {
    public int coinChange(int[] coins, int amount) {
        int[] fewest = new int[amount + 1];
        Arrays.fill(fewest, Integer.MAX_VALUE);
        fewest[0] = 0;
        for (int a = 1; a <= amount; a++) {
            for (int c : coins) {
                if (c <= a && fewest[a - c] != Integer.MAX_VALUE && fewest[a - c] + 1 < fewest[a]) {
                    fewest[a] = fewest[a - c] + 1;
                }
            }
        }
        return fewest[amount] == Integer.MAX_VALUE ? -1 : fewest[amount];
    }
}
