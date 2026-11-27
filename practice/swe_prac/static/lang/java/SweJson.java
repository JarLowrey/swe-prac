import java.util.*;
import java.util.function.Function;
import java.util.function.IntFunction;

/**
 * JSON for the test harness: reading the tests' arguments and writing the solution's results.
 * Numbers read as Long (whole) or Double; arrays as ArrayList; null as null.
 */
final class SweJson {
    static final int MAX_NODES = 1_000_000;

    private SweJson() {}

    // -- reading -------------------------------------------------------------------------
    static Object parse(String text) {
        Reader r = new Reader(text);
        Object value = r.value();
        r.space();
        if (r.i != text.length()) throw new IllegalArgumentException("trailing JSON at " + r.i);
        return value;
    }

    private static final class Reader {
        final String s;
        int i;

        Reader(String s) {
            this.s = s;
        }

        void space() {
            while (i < s.length() && s.charAt(i) <= ' ') i++;
        }

        Object value() {
            space();
            char c = s.charAt(i);
            if (c == '[') {
                i++;
                List<Object> out = new ArrayList<>();
                space();
                if (s.charAt(i) == ']') {
                    i++;
                    return out;
                }
                while (true) {
                    out.add(value());
                    space();
                    char d = s.charAt(i++);
                    if (d == ']') return out;
                    if (d != ',') throw new IllegalArgumentException("bad JSON at " + i);
                }
            }
            if (c == '{') {
                i++;
                Map<String, Object> out = new LinkedHashMap<>();
                space();
                if (s.charAt(i) == '}') {
                    i++;
                    return out;
                }
                while (true) {
                    space();
                    String key = string();
                    space();
                    i++; // ':'
                    out.put(key, value());
                    space();
                    char d = s.charAt(i++);
                    if (d == '}') return out;
                    if (d != ',') throw new IllegalArgumentException("bad JSON at " + i);
                }
            }
            if (c == '"') return string();
            if (s.startsWith("true", i)) {
                i += 4;
                return Boolean.TRUE;
            }
            if (s.startsWith("false", i)) {
                i += 5;
                return Boolean.FALSE;
            }
            if (s.startsWith("null", i)) {
                i += 4;
                return null;
            }
            int start = i;
            boolean whole = true;
            while (i < s.length() && "+-0123456789.eE".indexOf(s.charAt(i)) >= 0) {
                if (".eE".indexOf(s.charAt(i)) >= 0) whole = false;
                i++;
            }
            String num = s.substring(start, i);
            return whole ? (Object) Long.parseLong(num) : (Object) Double.parseDouble(num);
        }

        String string() {
            StringBuilder out = new StringBuilder();
            i++; // opening quote
            while (true) {
                char c = s.charAt(i++);
                if (c == '"') return out.toString();
                if (c != '\\') {
                    out.append(c);
                    continue;
                }
                char e = s.charAt(i++);
                switch (e) {
                    case 'n' -> out.append('\n');
                    case 't' -> out.append('\t');
                    case 'r' -> out.append('\r');
                    case 'b' -> out.append('\b');
                    case 'f' -> out.append('\f');
                    case 'u' -> {
                        out.append((char) Integer.parseInt(s.substring(i, i + 4), 16));
                        i += 4;
                    }
                    default -> out.append(e);
                }
            }
        }
    }

    @SuppressWarnings("unchecked")
    static List<Object> list(Object v) {
        return (List<Object>) v;
    }

    static int toInt(Object v) {
        return (int) ((Number) v).longValue();
    }

    static long toLong(Object v) {
        return ((Number) v).longValue();
    }

    static double toDouble(Object v) {
        return ((Number) v).doubleValue();
    }

    static boolean toBool(Object v) {
        return (Boolean) v;
    }

    static String toStr(Object v) {
        return (String) v;
    }

    static int[] toIntArray(Object v) {
        List<Object> l = list(v);
        int[] out = new int[l.size()];
        for (int i = 0; i < out.length; i++) out[i] = toInt(l.get(i));
        return out;
    }

    static long[] toLongArray(Object v) {
        List<Object> l = list(v);
        long[] out = new long[l.size()];
        for (int i = 0; i < out.length; i++) out[i] = toLong(l.get(i));
        return out;
    }

    static double[] toDoubleArray(Object v) {
        List<Object> l = list(v);
        double[] out = new double[l.size()];
        for (int i = 0; i < out.length; i++) out[i] = toDouble(l.get(i));
        return out;
    }

    static boolean[] toBoolArray(Object v) {
        List<Object> l = list(v);
        boolean[] out = new boolean[l.size()];
        for (int i = 0; i < out.length; i++) out[i] = toBool(l.get(i));
        return out;
    }

    static <T> T[] toArray(Object v, IntFunction<T[]> make, Function<Object, T> each) {
        List<Object> l = list(v);
        T[] out = make.apply(l.size());
        for (int i = 0; i < out.length; i++) out[i] = each.apply(l.get(i));
        return out;
    }

    /** A mutable list (ArrayList), as a solution may change its arguments. */
    static <T> List<T> toList(Object v, Function<Object, T> each) {
        List<Object> l = list(v);
        List<T> out = new ArrayList<>(l.size());
        for (Object x : l) out.add(each.apply(x));
        return out;
    }

    // -- writing -------------------------------------------------------------------------
    /** Compact JSON for the page. Throws SweAdapterError for a malformed list, tree or graph. */
    static String encode(Object value) {
        StringBuilder out = new StringBuilder();
        write(out, value, false);
        return out.toString();
    }

    /** A value as the tests write it, for people: [1, 2], "text", null, true. */
    static String show(Object value) {
        StringBuilder out = new StringBuilder();
        write(out, value, true);
        return out.toString();
    }

    static String quote(String s) {
        StringBuilder out = new StringBuilder();
        writeString(out, s);
        return out.toString();
    }

    private static void write(StringBuilder out, Object v, boolean pretty) {
        String sep = pretty ? ", " : ",";
        if (v == null) {
            out.append("null");
        } else if (v instanceof Boolean || v instanceof Integer || v instanceof Long || v instanceof Short || v instanceof Byte) {
            out.append(v);
        } else if (v instanceof Double || v instanceof Float) {
            double d = ((Number) v).doubleValue();
            if (Double.isNaN(d) || Double.isInfinite(d)) out.append(pretty ? String.valueOf(d) : "null");
            else if (d == Math.rint(d) && Math.abs(d) < 1e15) out.append((long) d).append(".0");
            else out.append(d);
        } else if (v instanceof String s) {
            writeString(out, s);
        } else if (v instanceof Character c) {
            writeString(out, String.valueOf(c));
        } else if (v instanceof int[] a) {
            out.append('[');
            for (int i = 0; i < a.length; i++) out.append(i == 0 ? "" : sep).append(a[i]);
            out.append(']');
        } else if (v instanceof long[] a) {
            out.append('[');
            for (int i = 0; i < a.length; i++) out.append(i == 0 ? "" : sep).append(a[i]);
            out.append(']');
        } else if (v instanceof double[] a) {
            out.append('[');
            for (int i = 0; i < a.length; i++) {
                if (i > 0) out.append(sep);
                write(out, a[i], pretty);
            }
            out.append(']');
        } else if (v instanceof boolean[] a) {
            out.append('[');
            for (int i = 0; i < a.length; i++) out.append(i == 0 ? "" : sep).append(a[i]);
            out.append(']');
        } else if (v instanceof char[] a) {
            out.append('[');
            for (int i = 0; i < a.length; i++) {
                if (i > 0) out.append(sep);
                writeString(out, String.valueOf(a[i]));
            }
            out.append(']');
        } else if (v instanceof Object[] a) {
            writeAll(out, Arrays.asList(a), pretty);
        } else if (v instanceof Collection<?> c) {
            writeAll(out, c, pretty);
        } else {
            Object plain = SweAdapt.plain(v);
            if (plain == NOT_MINE) writeString(out, String.valueOf(v));
            else write(out, plain, pretty);
        }
    }

    /** What SweAdapt.plain returns for a value that isn't a node or record of the problem. */
    static final Object NOT_MINE = new Object();

    private static void writeAll(StringBuilder out, Collection<?> items, boolean pretty) {
        out.append('[');
        boolean first = true;
        for (Object x : items) {
            if (!first) out.append(pretty ? ", " : ",");
            first = false;
            write(out, x, pretty);
        }
        out.append(']');
    }

    private static void writeString(StringBuilder out, String s) {
        out.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                default -> {
                    if (c < 0x20 || c > 0x7e) {
                        String hex = Integer.toHexString(c);
                        out.append("\\u").append("0000", hex.length(), 4).append(hex);
                    } else {
                        out.append(c);
                    }
                }
            }
        }
        out.append('"');
    }
}
