/** The solution returned something that isn't a well-formed list, tree or graph. */
final class SweAdapterError extends RuntimeException {
    SweAdapterError(String message) {
        super(message);
    }
}
