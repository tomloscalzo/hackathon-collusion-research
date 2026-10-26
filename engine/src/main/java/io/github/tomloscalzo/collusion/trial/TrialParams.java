package io.github.tomloscalzo.collusion.trial;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.llm.ModelIdentity;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * The params.json of one Track M trial (scope 4.6): every experimental parameter, written once, as sorted-key JSON. A pure
 * value: nothing here is read by the game, the prompts, the cache keys or the replay digests, so logging cannot change them.
 *
 * <p>Contract with tools/trial/derive.py: the file always has {@code competitive_price} and {@code collusive_price}
 * (build() refuses without them) and has {@code high_threshold} only when set (derive.py defaults it to 0.8).
 */
public final class TrialParams {
    private final ObjectNode json;

    private TrialParams(ObjectNode json) {
        this.json = json;
    }

    public static Builder builder(String trial, String arm) {
        return new Builder(trial, arm);
    }

    public ObjectNode toJson() {
        return json.deepCopy();
    }

    public void write(Path file) throws IOException {
        Files.writeString(file, Canonical.text(json) + "\n", StandardCharsets.UTF_8);
    }

    /** SHA-256 of a prompt or scenario file with LF line ends (the same rule as ParaphraseFile). */
    public static String fileFingerprint(Path file) throws IOException {
        return Canonical.sha256(Files.readString(file, StandardCharsets.UTF_8).replace("\r\n", "\n"));
    }

    public static final class Builder {
        private final ObjectNode n = Canonical.MAPPER.createObjectNode();
        private final ArrayNode seats = n.putArray("seats");
        private boolean prices;

        private Builder(String trial, String arm) {
            n.put("trial", trial).put("arm", arm);
        }

        public Builder condition(String condition) { n.put("condition", condition); return this; }
        public Builder penaltyPoint(int point) { n.put("expected_penalty_point", point); return this; }
        public Builder wording(int index) { n.put("wording_index", index); return this; }
        public Builder seed(long seed) { n.put("seed", seed); return this; }
        public Builder codeCommit(String commit) { n.put("code_commit", commit); return this; }
        public Builder scenarioFingerprint(String sha) { n.put("scenario_fingerprint", sha); return this; }

        /** The full market settings (demand, levels, fine, screen, detection, horizon, cap), as given. */
        public Builder market(Map<String, ?> settings) {
            n.set("market", Canonical.MAPPER.valueToTree(new TreeMap<>(settings)));
            return this;
        }

        /** Competitive and collusive quote levels: the scale of derive.py's collusion level. */
        public Builder prices(double competitive, double collusive) {
            if (!(competitive < collusive)) {
                throw new IllegalArgumentException("competitive_price must be below collusive_price");
            }
            n.put("competitive_price", competitive).put("collusive_price", collusive);
            prices = true;
            return this;
        }

        public Builder highThreshold(double t) { n.put("high_threshold", t); return this; }

        /** kind "llm" (servedName parsed into model identity) or "scripted" (rule names the scripted rule). */
        public Builder seat(String seat, String kind, String rule, String servedName) {
            if (!"llm".equals(kind) && !"scripted".equals(kind)) {
                throw new IllegalArgumentException("seat kind must be llm or scripted: " + kind);
            }
            for (JsonNode e : seats) {
                if (e.path("seat").asText().equals(seat)) {
                    throw new IllegalArgumentException("duplicate seat " + seat);
                }
            }
            ObjectNode s = seats.addObject().put("seat", seat).put("kind", kind);
            if (rule != null) {
                s.put("rule", rule);
            }
            if (servedName != null) {
                ModelIdentity id = ModelIdentity.parse(servedName);
                ObjectNode m = s.putObject("model").put("served_name", id.servedName());
                m.put("model_id", id.modelId()).put("revision", id.revision()).put("variant", id.variant());
            }
            return this;
        }

        public Builder drawKeys(List<String> keys) {
            ArrayNode a = n.putArray("draw_keys");
            keys.forEach(a::add);
            return this;
        }

        public Builder talkLimits(int maxMessages, int maxWords) {
            n.putObject("talk").put("max_messages", maxMessages).put("max_words", maxWords);
            return this;
        }

        /** A condition text and the seats it applies to. */
        public Builder conditionText(String name, String slot, String text, List<String> forSeats) {
            ArrayNode a = n.has("condition_texts") ? (ArrayNode) n.get("condition_texts") : n.putArray("condition_texts");
            ObjectNode t = a.addObject().put("name", name).put("slot", slot).put("text", text);
            ArrayNode s = t.putArray("seats");
            forSeats.forEach(s::add);
            return this;
        }

        public Builder sampling(double temperature, int maxTokens, boolean thinking) {
            n.putObject("sampling").put("temperature", temperature).put("max_tokens", maxTokens);
            n.put("thinking", thinking);
            return this;
        }

        public Builder promptFingerprint(String file, String sha) {
            JsonNode f = n.has("prompt_fingerprints") ? n.get("prompt_fingerprints") : n.putObject("prompt_fingerprints");
            ((ObjectNode) f).put(file, sha);
            return this;
        }

        public TrialParams build() {
            if (!prices) {
                throw new IllegalStateException("competitive_price and collusive_price are required (derive.py)");
            }
            if (seats.isEmpty()) {
                throw new IllegalStateException("at least one seat is required");
            }
            ObjectNode out = n.deepCopy();
            out.put("n_firms", seats.size());
            if (out.has("prompt_fingerprints")) {
                // collect.py (C9.2) compares one string per trial and arm: the hash of the prompt-file fingerprints only.
                // The scenario stays out (C4.3 review): an arm spans several scenario files, one per penalty point, and
                // scenario_fingerprint is kept as its own key.
                ObjectNode prompts = Canonical.MAPPER.createObjectNode();
                prompts.set("prompts", out.path("prompt_fingerprints"));
                out.put("prompt_fingerprint", Canonical.digestOf(prompts));
            }
            return new TrialParams(out);
        }
    }
}
