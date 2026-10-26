package io.github.tomloscalzo.collusion.agents.llm;

import java.util.ArrayList;
import java.util.List;

/** Per-run record of the LLM seat's parse and refusal outcomes (one entry per round). Not thread shared. */
public final class SeatReport {
    /**
     * OK, REPAIRED (valid after the repair retry), IMPUTED (no parseable quote after the repair: refusal kinds
     * UNPARSEABLE and TRUNCATED), REFUSED (kinds MODEL_DECLINE, MODEL_TEXT, PROVIDER, BLOCKED), AFTER_REFUSAL (every round
     * after the first refusal: no call is made and the seat plays s0).
     */
    public enum Status { OK, REPAIRED, IMPUTED, REFUSED, AFTER_REFUSAL }

    /**
     * The six recorded refusal kinds (INTERFACES e.5); code() is written to info["llm.refusalKind"] on the refusal round.
     * MODEL_DECLINE: quote null or a true decline in JSON. MODEL_TEXT: a refusal in prose without a JSON object. PROVIDER:
     * the provider's refusal field (finishReason "refusal"). BLOCKED: a provider content or prompt filter (finishReason
     * "content_filter"), a provider block, not a model refusal. UNPARSEABLE: no parseable quote after the repair.
     * TRUNCATED: as UNPARSEABLE, with the final reply cut off at the token limit and no complete leading quote.
     */
    public enum RefusalKind {
        MODEL_DECLINE(1), MODEL_TEXT(2), PROVIDER(3), BLOCKED(4), UNPARSEABLE(5), TRUNCATED(6);

        private final int code;

        RefusalKind(int code) {
            this.code = code;
        }

        public int code() {
            return code;
        }

        /** UNPARSEABLE and TRUNCATED rounds are IMPUTED, the others REFUSED. */
        public boolean imputed() {
            return this == UNPARSEABLE || this == TRUNCATED;
        }
    }

    /** One comprehension probe (T18): the stated per-round profits against the true ones; parsed false when unreadable. */
    public record Probe(int round, boolean parsed, double bothStated, double undercutStated, double bothTrue,
                        double undercutTrue, boolean correct) {}

    private final List<Probe> probes = new ArrayList<>();
    private final List<Status> rounds = new ArrayList<>();
    private int calls;
    private int cachedCalls;
    private int offGrid;
    private long tokensIn;
    private long tokensOut;
    private int firstRefusalRound = -1;
    private RefusalKind refusalKind;

    void addRound(Status s, boolean offGridQuote) {
        rounds.add(s);
        if (offGridQuote) {
            offGrid++;
        }
    }

    void addCall(boolean cached, int in, int out) {
        calls++;
        if (cached) {
            cachedCalls++;
        }
        tokensIn += in;
        tokensOut += out;
    }

    void addProbe(Probe p) {
        probes.add(p);
    }

    /** Records the first refusal (Track S: later calls are never made; Track M: later refusals count as rounds only). */
    void markRefusal(int round, RefusalKind kind) {
        if (firstRefusalRound < 0) {
            firstRefusalRound = round;
            refusalKind = kind;
        }
    }

    public List<Probe> probes() { return List.copyOf(probes); }
    public List<Status> rounds() { return List.copyOf(rounds); }
    public int calls() { return calls; }
    public int cachedCalls() { return cachedCalls; }
    public int offGridQuotes() { return offGrid; }
    public long tokensIn() { return tokensIn; }
    public long tokensOut() { return tokensOut; }

    /** The round of the first refusal (any kind), or -1. */
    public int firstRefusalRound() { return firstRefusalRound; }

    /** The kind of the first refusal, or null. */
    public RefusalKind refusalKind() { return refusalKind; }

    /** A refusal in any round. Whether the run is a refuser depends on the statistic's window (LlmGame.summary). */
    public boolean refusedAnyRound() {
        return firstRefusalRound > 0;
    }

    public int count(Status s) {
        int c = 0;
        for (Status x : rounds) {
            if (x == s) {
                c++;
            }
        }
        return c;
    }

    /** Rounds whose quote is not the model's own (imputed, refused or after a refusal) are excluded from CI means (T48). */
    public boolean excluded(int round1Based) {
        Status s = rounds.get(round1Based - 1);
        return s == Status.IMPUTED || s == Status.REFUSED || s == Status.AFTER_REFUSAL;
    }
}
