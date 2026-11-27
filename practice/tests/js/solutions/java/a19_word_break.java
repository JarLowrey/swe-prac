import java.util.*;

class Solution {
    public boolean wordBreak(String s, String[] wordDict) {
        Set<String> words = new HashSet<>(Arrays.asList(wordDict));
        TreeSet<Integer> lengths = new TreeSet<>();
        for (String w : words) lengths.add(w.length());
        int n = s.length();
        boolean[] ok = new boolean[n + 1];
        ok[n] = true;
        for (int i = n - 1; i >= 0; i--) {
            for (int length : lengths) {
                int j = i + length;
                if (j > n) break;
                if (ok[j] && words.contains(s.substring(i, j))) {
                    ok[i] = true;
                    break;
                }
            }
        }
        return ok[0];
    }
}
