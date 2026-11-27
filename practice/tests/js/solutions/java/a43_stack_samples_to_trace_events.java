import java.util.*;

class Solution {
    public List<Event> convert(List<Sample> samples) {
        List<Event> events = new ArrayList<>();
        List<String> prev = new ArrayList<>();
        for (Sample sample : samples) {
            List<String> stack = sample.stack();
            int common = 0;
            int limit = Math.min(prev.size(), stack.size());
            while (common < limit && prev.get(common).equals(stack.get(common))) common++;
            for (int i = prev.size() - 1; i >= common; i--) {
                events.add(new Event("end", sample.timestamp(), prev.get(i)));
            }
            for (int i = common; i < stack.size(); i++) {
                events.add(new Event("start", sample.timestamp(), stack.get(i)));
            }
            prev = stack;
        }
        return events;
    }
}
