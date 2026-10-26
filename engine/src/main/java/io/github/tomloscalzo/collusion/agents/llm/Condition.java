package io.github.tomloscalzo.collusion.agents.llm;

import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * The prompt condition axes (spec 4.2, 4.3): elicitation (spontaneous / E1 / E2 / competitive / strict competitive / myopic instruction), label
 * (neutral / legal), guardrail and notice (off / on), and the vignette stakes multiplier (x1, x10).
 */
public record Condition(Elicitation elicitation, Label label, boolean guardrail, boolean notice, int stakes) {
    /**
     * COMPETITIVE_STRICT and COMPETITIVE_MYOPIC: the owner's declared post-hoc Track S P2 controls (arms competitive-strict
     * and competitive-myopic).
     */
    public enum Elicitation { SPONTANEOUS, E1, E2, COMPETITIVE, COMPETITIVE_STRICT, COMPETITIVE_MYOPIC }

    /** Label on the collusive option (T12: the classifier output is named CoordinationLabel, not Label). */
    public enum Label { NEUTRAL, LEGAL }

    public Condition {
        if (stakes < 1) {
            throw new IllegalArgumentException("stakes multiplier must be >= 1");
        }
    }

    public static Condition neutral() {
        return new Condition(Elicitation.SPONTANEOUS, Label.NEUTRAL, false, false, 1);
    }

    public Condition withElicitation(Elicitation v) { return new Condition(v, label, guardrail, notice, stakes); }
    public Condition withLabel(Label v) { return new Condition(elicitation, v, guardrail, notice, stakes); }
    public Condition withGuardrail(boolean v) { return new Condition(elicitation, label, v, notice, stakes); }
    public Condition withNotice(boolean v) { return new Condition(elicitation, label, guardrail, v, stakes); }
    public Condition withStakes(int v) { return new Condition(elicitation, label, guardrail, notice, v); }

    /** Parses "elicitation=E2,label=legal,guardrail=on,notice=off,stakes=10"; unknown keys or values are errors. */
    public static Condition parse(String spec) {
        Condition c = neutral();
        if (spec == null || spec.isBlank()) {
            return c;
        }
        Set<String> seen = new java.util.HashSet<>();
        for (String kv : spec.split("[,;]")) {
            String[] f = kv.trim().split("=", 2);
            if (f.length != 2 || !seen.add(f[0].trim())) {
                throw new IllegalArgumentException("bad condition item '" + kv + "' (use key=value, each key once)");
            }
            String k = f[0].trim().toLowerCase(Locale.ROOT);
            String v = f[1].trim().toUpperCase(Locale.ROOT);
            switch (k) {
                case "elicitation" -> c = c.withElicitation(Elicitation.valueOf(v));
                case "label" -> c = c.withLabel(Label.valueOf(v));
                case "guardrail" -> c = c.withGuardrail(onOff(k, v));
                case "notice" -> c = c.withNotice(onOff(k, v));
                case "stakes" -> c = c.withStakes(Integer.parseInt(v));
                default -> throw new IllegalArgumentException("unknown condition key '" + k + "'");
            }
        }
        return c;
    }

    private static boolean onOff(String k, String v) {
        return switch (v) {
            case "ON", "TRUE", "1" -> true;
            case "OFF", "FALSE", "0" -> false;
            default -> throw new IllegalArgumentException("condition " + k + " must be on or off");
        };
    }

    /** Stable text form, parseable by parse(). */
    public String canonical() {
        Map<String, String> m = new TreeMap<>();
        m.put("elicitation", elicitation.name());
        m.put("guardrail", guardrail ? "on" : "off");
        m.put("label", label.name());
        m.put("notice", notice ? "on" : "off");
        m.put("stakes", Integer.toString(stakes));
        StringBuilder sb = new StringBuilder();
        for (var e : m.entrySet()) {
            if (sb.length() > 0) {
                sb.append(',');
            }
            sb.append(e.getKey()).append('=').append(e.getValue());
        }
        return sb.toString();
    }
}
