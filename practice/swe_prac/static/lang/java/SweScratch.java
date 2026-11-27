/**
 * Runs Scratch.main for Run scratch, printing an uncaught exception as Java does. Then it stops
 * the program with EXIT, which static/lang-job.js reads as exit code 1.
 */
final class SweScratch {
    static final String EXIT = "swe-scratch-exit-1";

    private SweScratch() {}

    public static void main(String[] args) {
        try {
            Scratch.main(args);
        } catch (Throwable t) {
            System.out.flush();
            System.err.println("Exception in thread \"main\" " + SweRun.describe(t));
            System.err.flush();
            throw new SweAdapterError(EXIT);
        }
    }
}
