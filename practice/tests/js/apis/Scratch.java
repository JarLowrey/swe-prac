import java.math.BigInteger;
import java.util.*;
import java.util.function.*;
import java.util.stream.*;

// The parts of Java's standard library and language that interview code uses, run as a scratch
// file on the site's javac and TeaVM (solutions.test.mjs). Each check prints "ok <name>" or
// "FAIL <name>: ...".
public class Scratch {
    record Point(int x, int y) {}

    sealed interface Shape permits Circle, Square {}

    record Circle(int r) implements Shape {}

    record Square(int side) implements Shape {}

    enum Color { RED, GREEN }

    static class Boom extends RuntimeException {
        Boom(String message) {
            super(message);
        }
    }

    static int passed = 0;
    static int failed = 0;

    static void check(String name, Object got, Object want) {
        if (Objects.equals(got, want)) {
            passed++;
            System.out.println("ok " + name);
        } else {
            failed++;
            System.out.println("FAIL " + name + ": got " + got + ", want " + want);
        }
    }

    static int area(Shape shape) {
        return switch (shape) {
            case Circle c -> 3 * c.r() * c.r();
            case Square s -> s.side() * s.side();
        };
    }

    static <T extends Comparable<T>> T largest(List<T> items) {
        T best = items.get(0);
        for (T item : items) if (item.compareTo(best) > 0) best = item;
        return best;
    }

    public static void main(String[] args) {
        // Strings and characters
        check("String.join", String.join(", ", List.of("a", "b", "c")), "a, b, c");
        check("repeat", "ab".repeat(3), "ababab");
        check("format", String.format("%d-%s-%.2f-%5s|%-3s|", 7, "x", 1.5, "r", "l"), "7-x-1.50-    r|l  |");
        check("StringBuilder", new StringBuilder("abc").reverse().insert(0, 'z').deleteCharAt(1).toString(), "zba");
        check("split", Arrays.toString("a,b,,c".split(",")), "[a, b, , c]");
        check("split regex", Arrays.toString("a1b22c".split("\\d+")), "[a, b, c]");
        check("chars", "hello".chars().filter(c -> c == 'l').count(), 2L);
        check("char math", (char) ('a' + 2), 'c');
        check("Character", Character.isDigit('7') && Character.isLetter('q') && Character.toUpperCase('q') == 'Q', true);
        check("char counts", "banana".toCharArray()[1] - 'a', 0);
        check("strip and blank", "  x ".strip() + "|" + " ".isBlank(), "x|true");
        check("compareTo", "apple".compareTo("banana") < 0, true);
        check("hashCode", "abc".hashCode(), 96354);
        check("valueOf", String.valueOf(new char[] {'h', 'i'}) + String.valueOf(42), "hi42");
        check("text block", """
            a
              b""", "a\n  b");

        // Numbers
        check("parseInt", Integer.parseInt("-42") + Long.parseLong("10000000000"), 9999999958L);
        check("binary", Integer.toBinaryString(10) + " " + Integer.bitCount(255) + " " + Integer.parseInt("ff", 16), "1010 8 255");
        check("overflow wraps", Integer.MAX_VALUE + 1, Integer.MIN_VALUE);
        check("floorMod", Math.floorMod(-7, 3) + " " + (-7 % 3) + " " + Math.floorDiv(-7, 2), "2 -1 -4");
        check("Math", Math.max(3, Math.abs(-5)) + Math.pow(2, 10) + Math.sqrt(16), 1033.0);
        check("Integer cache", Integer.valueOf(1000).equals(Integer.valueOf(1000)), true);
        check("BigInteger", BigInteger.valueOf(2).pow(100).toString(), "1267650600228229401496703205376");
        check("double print", 0.1 + 0.2 + " " + 1.0 / 3, "0.30000000000000004 0.3333333333333333");

        // Collections
        List<Integer> nums = new ArrayList<>(List.of(5, 3, 8, 1));
        Collections.sort(nums);
        check("sort", nums, List.of(1, 3, 5, 8));
        nums.sort(Comparator.reverseOrder());
        check("reverse order", nums.toString(), "[8, 5, 3, 1]");
        int[] arr = {4, 2, 9};
        Arrays.sort(arr);
        check("Arrays", Arrays.toString(arr) + Arrays.stream(arr).sum() + Arrays.toString(Arrays.copyOfRange(arr, 1, 3)), "[2, 4, 9]15[4, 9]");
        Integer[] boxed = {3, 1, 2};
        Arrays.sort(boxed, (a, b) -> b - a);
        check("sort with comparator", Arrays.asList(boxed), List.of(3, 2, 1));
        int[][] grid = new int[2][3];
        grid[1][2] = 7;
        check("deepToString", Arrays.deepToString(grid), "[[0, 0, 0], [0, 0, 7]]");
        check("fill and equals", Arrays.equals(new int[] {1, 1}, fillOnes(2)), true);
        check("Collections", Collections.max(List.of(2, 9, 4)) + Collections.frequency(List.of(1, 2, 1), 1) + Collections.nCopies(2, "x").toString(), "11[x, x]");

        Map<String, Integer> counts = new HashMap<>();
        for (String w : "a b a c a b".split(" ")) counts.merge(w, 1, Integer::sum);
        check("merge", new TreeMap<>(counts).toString(), "{a=3, b=2, c=1}");
        check("getOrDefault", counts.getOrDefault("z", 0), 0);
        Map<Integer, List<String>> groups = new HashMap<>();
        groups.computeIfAbsent(1, k -> new ArrayList<>()).add("x");
        check("computeIfAbsent", groups.get(1), List.of("x"));
        Map<String, Integer> order = new LinkedHashMap<>();
        order.put("z", 1);
        order.put("a", 2);
        check("LinkedHashMap order", String.join("", order.keySet()), "za");

        TreeMap<Integer, String> tree = new TreeMap<>(Map.of(10, "a", 20, "b", 30, "c"));
        check("TreeMap", tree.floorKey(25) + " " + tree.ceilingKey(11) + " " + tree.headMap(20).size() + " " + tree.firstEntry().getValue() + " " + tree.descendingMap().firstKey(), "20 20 1 a 30");
        TreeSet<Integer> set = new TreeSet<>(List.of(1, 5, 9));
        check("TreeSet", set.floor(6) + " " + set.higher(5) + " " + set.pollFirst() + " " + set, "5 9 1 [5, 9]");

        Deque<Integer> stack = new ArrayDeque<>();
        stack.push(1);
        stack.push(2);
        check("ArrayDeque stack", stack.pop() + " " + stack.peek(), "2 1");
        Deque<Integer> queue = new ArrayDeque<>();
        queue.offer(1);
        queue.offerLast(2);
        queue.offerFirst(0);
        check("ArrayDeque queue", queue.poll() + " " + queue.pollLast() + " " + queue.size(), "0 2 1");
        PriorityQueue<int[]> heap = new PriorityQueue<>((a, b) -> a[0] != b[0] ? Integer.compare(a[0], b[0]) : Integer.compare(b[1], a[1]));
        heap.add(new int[] {2, 1});
        heap.add(new int[] {1, 5});
        heap.add(new int[] {1, 9});
        check("PriorityQueue", heap.poll()[1] + " " + heap.poll()[1] + " " + heap.poll()[1], "9 5 1");
        PriorityQueue<Integer> maxHeap = new PriorityQueue<>(Collections.reverseOrder());
        maxHeap.addAll(List.of(3, 7, 5));
        check("max heap", maxHeap.peek(), 7);
        Iterator<Integer> it = new ArrayList<>(List.of(1, 2, 3, 4)).iterator();
        int kept = 0;
        while (it.hasNext()) if (it.next() % 2 == 0) kept++;
        check("Iterator", kept, 2);
        BitSet bits = new BitSet();
        bits.set(3);
        bits.set(10);
        check("BitSet", bits.cardinality() + " " + bits.nextSetBit(4), "2 10");
        check("Set.of contains", Set.of("a", "b").contains("b"), true);
        check("immutable", throwsOn(() -> List.of(1).add(2)), true);
        check("Optional", Optional.ofNullable((String) null).map(String::length).orElse(-1), -1);

        // Streams
        List<String> words = List.of("pear", "fig", "apple", "kiwi");
        check("map filter collect", words.stream().filter(w -> w.length() > 3).map(String::toUpperCase).collect(Collectors.toList()), List.of("PEAR", "APPLE", "KIWI"));
        check("joining", words.stream().sorted().collect(Collectors.joining("|", "<", ">")), "<apple|fig|kiwi|pear>");
        check("groupingBy", new TreeMap<>(words.stream().collect(Collectors.groupingBy(String::length, Collectors.counting()))).toString(), "{3=1, 4=2, 5=1}");
        check("toMap", words.stream().collect(Collectors.toMap(w -> w, String::length)).get("fig"), 3);
        check("IntStream", IntStream.rangeClosed(1, 5).map(x -> x * x).sum() + " " + IntStream.range(0, 3).boxed().toList(), "55 [0, 1, 2]");
        check("comparing", words.stream().sorted(Comparator.comparing(String::length).thenComparing(Comparator.reverseOrder())).toList(), List.of("fig", "pear", "kiwi", "apple"));
        check("max by", words.stream().max(Comparator.comparingInt(String::length)).get(), "apple");
        check("reduce", Stream.of(1, 2, 3, 4).reduce(0, Integer::sum), 10);
        check("anyMatch distinct", Stream.of(1, 1, 2).distinct().count() + " " + Stream.of(1, 2).anyMatch(x -> x > 1), "2 true");

        // Language features
        Point p = new Point(1, 2);
        Set<Point> points = new HashSet<>(List.of(new Point(1, 2), new Point(1, 2), new Point(3, 4)));
        check("record", p + " " + p.equals(new Point(1, 2)) + " " + points.size(), "Point[x=1, y=2] true 2");
        check("switch on sealed type", area(new Circle(2)) + area(new Square(3)), 21);
        Object o = "text";
        check("instanceof pattern", o instanceof String s && s.length() == 4, true);
        var day = Color.GREEN;
        String name = switch (day) {
            case RED -> "r";
            case GREEN -> "g";
        };
        check("enum switch", name + Color.valueOf("RED").ordinal() + Color.values().length, "g02");
        check("generic method", largest(List.of("b", "c", "a")), "c");
        Function<Integer, Integer> twice = x -> x * 2;
        BiFunction<Integer, Integer, Integer> add = Integer::sum;
        Supplier<List<String>> fresh = ArrayList::new;
        check("functions", twice.andThen(x -> x + 1).apply(5) + add.apply(2, 3) + fresh.get().size(), 16);
        int[] memo = new int[50];
        check("recursion with memo", fib(40, memo), 102334155);
        String caught = "";
        try {
            throw new Boom("bad");
        } catch (Boom e) {
            caught = e.getMessage();
        } finally {
            caught += "!";
        }
        check("exceptions", caught, "bad!");
        check("checked parse error", throwsOn(() -> Integer.parseInt("x")), true);
        outer:
        for (int i = 0; i < 3; i++) {
            for (int j = 0; j < 3; j++) {
                if (i * j == 2) {
                    check("labeled break", i + "," + j, "1,2");
                    break outer;
                }
            }
        }
        System.out.printf("printf %d %s%n", 1, "two");
        System.out.println(passed + " passed, " + failed + " failed");
    }

    static int[] fillOnes(int n) {
        int[] out = new int[n];
        Arrays.fill(out, 1);
        return out;
    }

    static boolean throwsOn(Runnable run) {
        try {
            run.run();
            return false;
        } catch (RuntimeException e) {
            return true;
        }
    }

    static int fib(int n, int[] memo) {
        if (n < 2) return n;
        if (memo[n] != 0) return memo[n];
        return memo[n] = fib(n - 1, memo) + fib(n - 2, memo);
    }
}
