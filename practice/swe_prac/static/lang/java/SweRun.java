import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * The test loop (static/lang-runner.js drives it). The first line of stdin is the tests as JSON:
 * {"tests": [{"steps": [{"call": "add_file", "args": [...]}, ...]}, ...]}. For each test it
 * makes a fresh instance and calls the steps in turn, writing one JSON line per event to stdout:
 *
 *   {"e":"start"}                          a test begins
 *   {"e":"ctor","raised":"..."}            the constructor threw (the test ends)
 *   {"e":"call"}                           a step's call is about to start
 *   {"e":"step","ms":1.5,"value":...}      it returned this (as JSON)
 *   {"e":"step","raised":"..."}            it threw this
 *   {"e":"step","adapter":"..."}           it returned a malformed list, tree or graph
 *   {"e":"end"} ... {"e":"done"}
 *
 * After each step it reads a line from stdin: "1" to go on with the test, "0" to end it (the
 * page compares the results; a failed step ends its test). What the solution prints goes to
 * stderr, so it can't be mistaken for an event.
 */
final class SweRun {
    private SweRun() {}

    interface Target {
        Object create();

        Object step(Object self, String name, List<Object> args, Clock clock);
    }

    /** The harness starts and stops it around the solution's own call. */
    static final class Clock {
        private long started;
        long nanos;

        void start() {
            started = System.nanoTime();
        }

        void stop() {
            nanos = System.nanoTime() - started;
        }
    }

    private static PrintStream events;

    static void run(Target target) {
        events = System.out;
        System.setOut(System.err);
        Map<String, Object> input = map(SweJson.parse(readLine()));
        for (Object raw : SweJson.list(input.get("tests"))) {
            emit("{\"e\":\"start\"}");
            Object self;
            try {
                self = target.create();
            } catch (Throwable t) {
                emit("{\"e\":\"ctor\",\"raised\":" + SweJson.quote(describe(t)) + "}");
                emit("{\"e\":\"end\"}");
                continue;
            }
            for (Object rawStep : SweJson.list(map(raw).get("steps"))) {
                Map<String, Object> step = map(rawStep);
                Clock clock = new Clock();
                String event;
                emit("{\"e\":\"call\"}");
                try {
                    Object result = target.step(self, (String) step.get("call"), SweJson.list(step.get("args")), clock);
                    String value = SweJson.encode(result);
                    event = "{\"e\":\"step\",\"ms\":" + (clock.nanos / 1e6) + ",\"value\":" + value + "}";
                } catch (SweAdapterError e) {
                    event = "{\"e\":\"step\",\"adapter\":" + SweJson.quote(e.getMessage()) + "}";
                } catch (Throwable t) {
                    event = "{\"e\":\"step\",\"raised\":" + SweJson.quote(describe(t)) + "}";
                }
                emit(event);
                if (!"1".equals(readLine())) break;
            }
            emit("{\"e\":\"end\"}");
        }
        emit("{\"e\":\"done\"}");
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Object v) {
        return (Map<String, Object>) v;
    }

    private static void emit(String line) {
        System.err.flush();
        events.print(line);
        events.print('\n');
        events.flush();
    }

    /** One line of stdin (UTF-8), read a byte at a time: the page adds lines as it goes. */
    private static String readLine() {
        java.io.ByteArrayOutputStream bytes = new java.io.ByteArrayOutputStream();
        try {
            int b;
            while ((b = System.in.read()) != -1 && b != '\n') bytes.write(b);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        return new String(bytes.toByteArray(), StandardCharsets.UTF_8);
    }

    /** An exception as Java prints it, with the solution's frames (not the harness's). */
    static String describe(Throwable t) {
        StringBuilder out = new StringBuilder();
        Throwable cause = t;
        for (int depth = 0; cause != null && depth < 5; depth++, cause = cause.getCause()) {
            if (depth > 0) out.append("\nCaused by: ");
            out.append(cause);
            int shown = 0;
            for (StackTraceElement frame : cause.getStackTrace()) {
                String cls = frame.getClassName();
                if (cls.startsWith("Swe") || cls.startsWith("java.") || cls.startsWith("org.teavm.")) continue;
                if (shown++ == 30) {
                    out.append("\n\t...");
                    break;
                }
                out.append("\n\tat ").append(frame);
            }
        }
        return out.toString();
    }
}
