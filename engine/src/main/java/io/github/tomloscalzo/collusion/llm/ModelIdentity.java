package io.github.tomloscalzo.collusion.llm;

import java.util.regex.Pattern;

/**
 * The model identity carried by a served model name (INTERFACES.md f.1). The deploy recipe ({@code deploy/modal_vllm.py})
 * serves the Hugging Face weights {@code org/name} at commit {@code rev} as {@code org--name--rev+vllm<version>} (the
 * variant may carry a further tag). Hugging Face ids never contain "--", so such a name parses back unambiguously:
 * {@link #parse} returns modelId {@code org/name}, the 40-hex revision and the variant ({@code vllm0.8.5}; null when the
 * name has no {@code +} part, as a hand-named backend's may not). A name that does not follow the
 * convention (the mock's {@code mock-model-1}, a hosted API's model id) parses to modelId, revision and variant null.
 *
 * <p>The identity used everywhere (cache key, run lines, analysis grouping) is the provider label together with the full
 * served name; modelId, revision and variant are parsed from it for the manifest only, so they can never disagree with it.
 */
public record ModelIdentity(String servedName, String modelId, String revision, String variant) {
    private static final Pattern REVISION = Pattern.compile("[0-9a-f]{40}");
    /** One part of a Hugging Face id: no leading or trailing '-' or '.'; same rule as served_name() in the recipe. */
    private static final Pattern ID_PART = Pattern.compile("[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?");
    private static final Pattern VARIANT = Pattern.compile("[A-Za-z0-9._-]+");

    /** Parses a served model name; never throws (a name outside the convention gives nulls). */
    public static ModelIdentity parse(String servedName) {
        ModelIdentity none = new ModelIdentity(servedName, null, null, null);
        if (servedName == null) {
            return none;
        }
        String base = servedName;
        String variant = null;
        int plus = servedName.lastIndexOf('+');
        if (plus >= 0) {
            variant = servedName.substring(plus + 1);
            base = servedName.substring(0, plus);
            if (!VARIANT.matcher(variant).matches()) {
                return none;
            }
        }
        int sep = base.lastIndexOf("--");
        if (sep <= 0) {
            return none;
        }
        String revision = base.substring(sep + 2);
        String[] parts = base.substring(0, sep).split("--", -1);
        if (!REVISION.matcher(revision).matches() || parts.length > 2) {
            return none;
        }
        for (String p : parts) {
            if (!ID_PART.matcher(p).matches() || p.contains("..")) {
                return none;
            }
        }
        return new ModelIdentity(servedName, String.join("/", parts), revision, variant);
    }

    /** True when the served name names a pinned commit of known weights (the recipe convention). */
    public boolean pinned() {
        return revision != null;
    }
}
