package io.github.tomloscalzo.collusion.core.model;

import java.util.Map;
import java.util.TreeMap;

/** One roster entry (ticket T15: carries its category). config holds kind-specific numbers; k &lt; 0 means infinite. */
public record AgentSpec(String id, AgentCategory category, AgentKind kind, Map<String, Object> config) {
    public AgentSpec {
        config = config == null ? Map.of() : java.util.Collections.unmodifiableMap(new TreeMap<>(config));
    }

    public AgentSpec(String id, AgentCategory category, AgentKind kind) {
        this(id, category, kind, Map.of());
    }

    public AgentSpec with(String key, Object value) {
        Map<String, Object> c = new TreeMap<>(config);
        c.put(key, value);
        return new AgentSpec(id, category, kind, c);
    }
}
