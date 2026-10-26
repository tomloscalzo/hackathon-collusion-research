package io.github.tomloscalzo.collusion.scenario;

/** Raised when a scenario file cannot be parsed or fails validation. */
public class ScenarioLoadException extends RuntimeException {
    private static final long serialVersionUID = 1L;

    public ScenarioLoadException(String message) {
        super(message);
    }

    public ScenarioLoadException(String message, Throwable cause) {
        super(message, cause);
    }
}
