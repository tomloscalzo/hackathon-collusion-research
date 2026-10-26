package io.github.tomloscalzo.collusion.llm;

/** Settles the actual tokens of every real call against a run-level reservation (T9). Put it under the cache. */
public final class BudgetedLlmClient implements LlmClient {
    private final LlmClient delegate;
    private final Budget.Reservation reservation;

    public BudgetedLlmClient(LlmClient delegate, Budget.Reservation reservation) {
        this.delegate = delegate;
        this.reservation = reservation;
    }

    @Override
    public LlmResponse complete(LlmRequest request) {
        LlmResponse r;
        try {
            r = delegate.complete(request);
        } catch (LlmException.EmptyContent e) { // E1: the empty reply cost tokens too; still thrown, the caller decides
            reservation.settle((long) e.response().tokensIn() + e.response().tokensOut());
            throw e;
        }
        reservation.settle((long) r.tokensIn() + r.tokensOut());
        return r;
    }
}
