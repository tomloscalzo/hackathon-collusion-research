package io.github.tomloscalzo.collusion.agents.llm;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * A frozen paraphrase file under src/main/resources/prompts/ (JSON: template, items[{id, tone, order?, text}]). Items
 * are hand-written; placeholders are {{NAME}}. sha256 is the SHA-256 of the file text with LF line ends and goes into
 * every manifest (spec 5.3). tone is explore / cautious / plain: the Fish-P1/P2 wording control (T56) compares the explore
 * and cautious paraphrases.
 */
public record ParaphraseFile(String template, String resource, String sha256, List<Item> items) {
    public static final String GAME_SYSTEM = "game_system";
    public static final String GAME_TURN = "game_turn";
    public static final String VIGNETTE = "vignette";
    public static final List<String> TEMPLATES = List.of(GAME_SYSTEM, GAME_TURN, VIGNETTE);
    /** The Track M system prompt (proposal A1, C3.4), neutral about the number of firms; used with multiSeat on. */
    public static final String GAME_SYSTEM_M = "game_system_m";
    /** Track M quote turn of tacit arms (C5.5): gt01..gt05 with gt03 neutral about the number of firms. */
    public static final String GAME_TURN_M_TACIT = "game_turn_m_tacit";
    /** Track M chat arms (C5.3, wired in C5.5): the quote turn with the conversation, the talk turn, the talk rules. */
    public static final String GAME_TURN_M = "game_turn_m";
    public static final String GAME_TALK = "game_talk";
    public static final String TALK_RULES = "talk_rules";
    /** Track M template files: not part of the frozen set above, but hashed into every manifest beside it (C3.5, C5.5). */
    public static final List<String> TRACK_M_TEMPLATES = List.of(GAME_SYSTEM_M, GAME_TURN_M_TACIT, GAME_TURN_M, GAME_TALK,
            TALK_RULES);

    /** order is "CF" / "FC" (vignette: collusive option first or second), else null. */
    public record Item(String id, String tone, String order, String text) {}

    public ParaphraseFile {
        items = List.copyOf(items);
    }

    public int size() {
        return items.size();
    }

    public Item item(int index) {
        if (index < 0 || index >= items.size()) {
            throw new IllegalArgumentException("paraphrase index " + index + " out of range 0.." + (items.size() - 1)
                    + " for " + template);
        }
        return items.get(index);
    }

    public long distinctTexts() {
        Set<String> s = new HashSet<>();
        for (Item i : items) {
            s.add(i.text());
        }
        return s.size();
    }

    public static ParaphraseFile load(String template) {
        String res = "prompts/" + template + ".json";
        try (InputStream in = ParaphraseFile.class.getClassLoader().getResourceAsStream(res)) {
            if (in == null) {
                throw new IllegalArgumentException("paraphrase file not found: " + res);
            }
            String text = new String(in.readAllBytes(), StandardCharsets.UTF_8).replace("\r\n", "\n");
            JsonNode root = Canonical.MAPPER.readTree(text);
            if (!template.equals(root.path("template").asText())) {
                throw new IllegalArgumentException(res + ": template field must be '" + template + "'");
            }
            List<Item> items = new ArrayList<>();
            Set<String> ids = new HashSet<>();
            for (JsonNode n : root.path("items")) {
                String id = n.path("id").asText();
                if (id.isEmpty() || !ids.add(id) || !n.hasNonNull("text")) {
                    throw new IllegalArgumentException(res + ": every item needs a unique id and a text");
                }
                items.add(new Item(id, n.path("tone").asText("plain"), n.hasNonNull("order") ? n.get("order").asText() : null,
                        n.get("text").asText()));
            }
            return new ParaphraseFile(template, res, Canonical.sha256(text), items);
        } catch (IOException e) {
            throw new IllegalArgumentException("cannot read " + res, e);
        }
    }

    /** SHA-256 of every template file, frozen and Track M, for the manifest. */
    public static Map<String, String> allHashes() {
        Map<String, String> m = new TreeMap<>();
        for (String t : TEMPLATES) {
            m.put(t, load(t).sha256());
        }
        for (String t : TRACK_M_TEMPLATES) {
            m.put(t, load(t).sha256());
        }
        return m;
    }

    /** SHA-256 of each individual paraphrase text, keyed template:id. */
    public static Map<String, String> itemHashes() {
        Map<String, String> m = new TreeMap<>();
        for (String t : TEMPLATES) {
            for (Item i : load(t).items()) {
                m.put(t + ":" + i.id(), Canonical.sha256(i.text()));
            }
        }
        return m;
    }
}
