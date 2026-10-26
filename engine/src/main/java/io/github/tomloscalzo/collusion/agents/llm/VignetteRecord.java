package io.github.tomloscalzo.collusion.agents.llm;

import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * One vignette pass (one paraphrase, one seed): the rows in presentation order with their parsed choices and the switch
 * point. replayDigest() is the SHA-256 of the canonical JSON of the (request hash, parsed choice) pairs in presentation
 * order (T21), so a replay from the cache must reproduce the identical digest. estimate drops refused rows,
 * estimateRefusalsCompete scores them competitive (the pre-declared bound), estimateRefusalsCollude collusive (the other end
 * of the descriptive worst-case bracket).
 */
public record VignetteRecord(String scenarioId, long seed, int paraphrase, String paraphraseId, String condition,
                             List<Row> rows, SwitchPoint.Estimate estimate, SwitchPoint.Estimate estimateRefusalsCompete,
                             SwitchPoint.Estimate estimateRefusalsCollude) {
    public enum Choice { COLLUDE, COMPETE, REFUSED, INVALID }

    /** bOverG: the base payment (T13) in units of the gross collusive gain G; negative = attached to the collusive option. */
    public record Row(int rowIndex, int draw, double bOverG, String requestHash, Choice choice, boolean repaired,
                      boolean cached, int tokensIn, int tokensOut) {}

    public VignetteRecord {
        rows = List.copyOf(rows);
    }

    public int count(Choice c) {
        int k = 0;
        for (Row r : rows) {
            if (r.choice() == c) {
                k++;
            }
        }
        return k;
    }

    public String replayDigest() {
        ArrayNode a = Canonical.MAPPER.createArrayNode();
        for (Row r : rows) {
            ObjectNode o = a.addObject();
            o.put("hash", r.requestHash());
            o.put("choice", r.choice().name());
        }
        return Canonical.digestOf(a);
    }

    public ObjectNode toJson() {
        ObjectNode o = Canonical.MAPPER.createObjectNode();
        o.put("kind", "vignette");
        o.put("scenarioId", scenarioId);
        o.put("seed", seed);
        o.put("paraphrase", paraphrase);
        o.put("paraphraseId", paraphraseId);
        o.put("condition", condition);
        o.put("calls", rows.size());
        o.put("valid", count(Choice.COLLUDE) + count(Choice.COMPETE));
        o.put("refusals", count(Choice.REFUSED));
        o.put("invalid", count(Choice.INVALID));
        // a refused row is dropped from b-hat only (the unit is the call); the pass is a refuser only when nothing is left
        o.put("refuser", count(Choice.REFUSED) > 0 && count(Choice.COLLUDE) + count(Choice.COMPETE) == 0);
        // always competitive whatever the payment: b-hat below the lowest offered payment (censor LOW); it enters the
        // estimate at that payment (PREDICTIONS revision 2026-10-23 (v))
        o.put("alwaysCompetitive", estimate.censor() == SwitchPoint.Censor.LOW);
        if (Double.isNaN(estimate.bHat())) {
            o.putNull("bHat");
        } else {
            o.put("bHat", estimate.bHat());
        }
        o.put("censor", estimate.censor().name());
        if (Double.isNaN(estimateRefusalsCompete.bHat())) {
            o.putNull("bHatRefCompete");
        } else {
            o.put("bHatRefCompete", estimateRefusalsCompete.bHat());
        }
        o.put("censorRefCompete", estimateRefusalsCompete.censor().name());
        if (Double.isNaN(estimateRefusalsCollude.bHat())) {
            o.putNull("bHatRefCollude");
        } else {
            o.put("bHatRefCollude", estimateRefusalsCollude.bHat());
        }
        o.put("censorRefCollude", estimateRefusalsCollude.censor().name());
        Map<Double, int[]> byLevel = new TreeMap<>();
        for (Row r : rows) {
            int[] c = byLevel.computeIfAbsent(r.bOverG(), k -> new int[3]);
            if (r.choice() == Choice.COLLUDE) {
                c[0]++;
            } else if (r.choice() == Choice.COMPETE) {
                c[1]++;
            } else {
                c[2]++;
            }
        }
        ArrayNode lv = o.putArray("levels");
        for (var e : byLevel.entrySet()) {
            ObjectNode l = lv.addObject();
            l.put("bOverG", e.getKey());
            l.put("collude", e.getValue()[0]);
            l.put("compete", e.getValue()[1]);
            l.put("other", e.getValue()[2]);
        }
        long tin = 0;
        long tout = 0;
        int cached = 0;
        for (Row r : rows) {
            tin += r.tokensIn();
            tout += r.tokensOut();
            cached += r.cached() ? 1 : 0;
        }
        o.put("tokensIn", tin);
        o.put("tokensOut", tout);
        o.put("cachedCalls", cached);
        o.put("replayDigest", replayDigest());
        return o;
    }
}
