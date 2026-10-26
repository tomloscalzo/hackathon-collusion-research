package io.github.tomloscalzo.collusion.engine;

/** An agent action for one round. */
public sealed interface Action permits Action.Quote {
    /**
     * A displayed half-spread plus an optional hidden fill price strictly below it. The hidden price is used only for
     * routing contestable flow (an off-screen better fill, ticket T2); the screen shows the displayed quote.
     */
    record Quote(double displayed, Double hiddenFill) implements Action {
        public static Quote of(double displayed) {
            return new Quote(displayed, null);
        }

        public static Quote hidden(double displayed, double hiddenFill) {
            return new Quote(displayed, hiddenFill);
        }

        public double effective() {
            return hiddenFill == null ? displayed : StrictMath.min(displayed, hiddenFill);
        }
    }
}
