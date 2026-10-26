package io.github.tomloscalzo.collusion.agents;

import io.github.tomloscalzo.collusion.engine.Decision;
import io.github.tomloscalzo.collusion.engine.Observation;
import java.util.Optional;

/** A player. Instances are stateful and created fresh for every run (see AgentFactory). */
public interface Agent {
    String id();

    Decision decide(Observation obs);

    /** The margin and tolerance this agent compares the inside quote against, if it monitors one. */
    default Optional<SignalReference> signalReference() {
        return Optional.empty();
    }

    /**
     * The grid-snapped margin s(theta) this agent quotes when it adheres, if it has one (BR-15). It is the s_p that a
     * counterparty's prompts state (payoff schedule, audit probability, comprehension probe) and that P(adhere) is
     * measured against. It defaults to the signal reference's margin; agents that quote s(theta) without monitoring a
     * signal (DefectOnce, TitForTat) override it. It never changes play or the engine's false-alarm count.
     */
    default Optional<Double> referenceMargin() {
        return signalReference().map(SignalReference::margin);
    }

    /** The plain-words rule that may be disclosed to a counterparty (empty when none). */
    default String disclosedRule() {
        return "";
    }

    /** Reference margin (snapped to the quote grid) and the tolerance below which a quote counts as a deviation. */
    record SignalReference(double margin, double tolerance) {}
}
