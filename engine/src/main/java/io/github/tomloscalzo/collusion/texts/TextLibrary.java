package io.github.tomloscalzo.collusion.texts;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * The named seat texts of one or more text data files (C11.1; format in CONTRACTS.md, checked by tools/trial/lint_m.py):
 * {@code {"version":1,"texts":[{name, slot, text, placebo_for?, about_rule?, true_statement?}]}}. A "questions" list is read like "texts", as lint_m.py does. Loading is strict: an
 * unknown field, an unknown slot, a duplicate name (also across files), a blank name, a non-boolean flag, a
 * {@code true_statement: false} outside TALK_NOTICE, SEAT_NOTES and REPLY_FIELD or on a second TALK_NOTICE text, or a {@code placebo_for} name that no loaded file
 * defines is an error naming the text. Pure; nothing here calls a model. Immutable once built.
 */
public final class TextLibrary {
    private static final Set<String> KEYS = Set.of("name", "slot", "text", "placebo_for", "about_rule", "true_statement", "role_play",
            "owner_text_exempt_loaded", "owner_approved_idle_notice");

    private final Map<String, SeatText> byName;

    private TextLibrary(Map<String, SeatText> byName) {
        this.byName = byName;
    }

    /** Parses and merges several documents (JSON text), each in the data-file format. */
    public static TextLibrary parse(String... documents) {
        Map<String, SeatText> out = new LinkedHashMap<>();
        for (String doc : documents) {
            JsonNode root = read(doc);
            if (!root.isObject()) {
                throw new IllegalArgumentException("text file: the top level must be an object");
            }
            if (root.has("version") && root.get("version").asInt(-1) != 1) {
                throw new IllegalArgumentException("text file: version must be 1");
            }
            if (!root.has("texts") && !root.has("questions")) {
                throw new IllegalArgumentException("text file: no \"texts\" list");
            }
            for (String key : new String[] {"texts", "questions"}) {
                if (root.has(key) && !root.get(key).isArray()) {
                    throw new IllegalArgumentException("text file: \"" + key + "\" must be a list");
                }
                for (JsonNode n : root.path(key)) {
                    SeatText t = entry(n);
                    if (out.put(t.name(), t) != null) {
                        throw new IllegalArgumentException("text '" + t.name() + "' is defined twice");
                    }
                }
            }
        }
        java.util.Map<Slot, String> untrue = new java.util.EnumMap<>(Slot.class);
        for (SeatText t : out.values()) {
            for (String p : t.placeboFor()) {
                if (!out.containsKey(p)) {
                    throw new IllegalArgumentException("text '" + t.name() + "': placebo_for names unknown text '" + p + "'");
                }
            }
            if (!t.trueStatement()) {
                if (t.slot() != Slot.TALK_NOTICE && t.slot() != Slot.SEAT_NOTES && t.slot() != Slot.REPLY_FIELD
                        && !(t.slot() == Slot.QUESTION && t.ownerApprovedIdleNotice())) { // U8: the idle reasoning-monitor threat
                    throw new IllegalArgumentException("text '" + t.name()
                            + "': true_statement false is only for TALK_NOTICE, SEAT_NOTES and REPLY_FIELD");
                }
                if (t.slot() == Slot.TALK_NOTICE && untrue.containsKey(t.slot())) {
                    throw new IllegalArgumentException("two untrue " + t.slot() + " texts: '" + untrue.get(t.slot()) + "' and '"
                            + t.name() + "'");
                }
                untrue.put(t.slot(), t.name());
            }
        }
        return new TextLibrary(Collections.unmodifiableMap(out));
    }

    public static TextLibrary load(Path... files) {
        String[] docs = new String[files.length];
        for (int i = 0; i < files.length; i++) {
            try {
                docs[i] = Files.readString(files[i], StandardCharsets.UTF_8);
            } catch (IOException e) {
                throw new IllegalArgumentException("cannot read " + files[i].getFileName(), e);
            }
        }
        return parse(docs);
    }

    /** Loads classpath resources such as {@code prompts/seat_texts.json}. */
    public static TextLibrary loadResources(String... resources) {
        String[] docs = new String[resources.length];
        for (int i = 0; i < resources.length; i++) {
            try (InputStream in = TextLibrary.class.getClassLoader().getResourceAsStream(resources[i])) {
                if (in == null) {
                    throw new IllegalArgumentException("text file not found: " + resources[i]);
                }
                docs[i] = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            } catch (IOException e) {
                throw new IllegalArgumentException("cannot read " + resources[i], e);
            }
        }
        return parse(docs);
    }

    private static JsonNode read(String doc) {
        try {
            String s = doc.startsWith("﻿") ? doc.substring(1) : doc;
            JsonNode n = Canonical.MAPPER.readTree(s);
            if (n == null || n.isMissingNode()) {
                throw new IllegalArgumentException("text file is empty");
            }
            return n;
        } catch (IOException e) {
            throw new IllegalArgumentException("text file is not valid JSON: " + e.getMessage(), e);
        }
    }

    private static SeatText entry(JsonNode n) {
        if (!n.isObject()) {
            throw new IllegalArgumentException("a text entry is not an object");
        }
        n.fieldNames().forEachRemaining(k -> {
            if (!KEYS.contains(k)) {
                throw new IllegalArgumentException("text entry has unknown field '" + k + "'");
            }
        });
        String name = n.path("name").isTextual() ? n.get("name").asText() : "";
        if (name.isBlank()) {
            throw new IllegalArgumentException("a text entry lacks a name");
        }
        if (!n.path("text").isTextual()) {
            throw new IllegalArgumentException("text '" + name + "' lacks a text");
        }
        Slot slot;
        try {
            slot = Slot.valueOf(n.path("slot").asText(""));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("text '" + name + "': unknown slot '" + n.path("slot").asText("") + "'");
        }
        List<String> placebo = new ArrayList<>();
        JsonNode pf = n.get("placebo_for");
        if (pf != null && !pf.isNull()) {
            if (pf.isTextual()) {
                placebo.add(pf.asText());
            } else if (pf.isArray()) {
                for (JsonNode p : pf) {
                    if (!p.isTextual()) {
                        throw new IllegalArgumentException("text '" + name + "': placebo_for must hold names");
                    }
                    placebo.add(p.asText());
                }
            } else {
                throw new IllegalArgumentException("text '" + name + "': placebo_for must be a name or a list of names");
            }
        }
        flag(n, "owner_text_exempt_loaded", name, false); // lint-only flag (lint_m.py); validated as a boolean, not carried
        return new SeatText(name, slot, n.get("text").asText(), placebo, flag(n, "about_rule", name, false),
                flag(n, "true_statement", name, true), flag(n, "role_play", name, false),
                flag(n, "owner_approved_idle_notice", name, false));
    }

    private static boolean flag(JsonNode n, String key, String name, boolean dflt) {
        JsonNode v = n.get(key);
        if (v == null || v.isNull()) {
            return dflt;
        }
        if (!v.isBoolean()) {
            throw new IllegalArgumentException("text '" + name + "': " + key + " must be true or false");
        }
        return v.asBoolean();
    }

    public boolean has(String name) { return byName.containsKey(name); }

    public SeatText get(String name) {
        SeatText t = byName.get(name);
        if (t == null) {
            throw new IllegalArgumentException("unknown text '" + name + "'");
        }
        return t;
    }

    public Collection<SeatText> all() { return byName.values(); }

    /** The one TALK_NOTICE text with true_statement false (the not-monitored notice), or null when no loaded file has it. */
    public SeatText untrue() {
        return byName.values().stream().filter(t -> !t.trueStatement() && t.slot() == Slot.TALK_NOTICE).findFirst().orElse(null);
    }

    /** Every text with true_statement false: at most one TALK_NOTICE, any number of SEAT_NOTES (the idle reasoning-monitor threat, variants A and B, U8) and REPLY_FIELD (U8). */
    public java.util.List<SeatText> untrueAll() {
        return byName.values().stream().filter(t -> !t.trueStatement()).toList();
    }
}
