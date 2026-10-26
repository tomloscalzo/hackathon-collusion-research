package io.github.tomloscalzo.collusion.results;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;

/** Canonical sorted-key JSON text and its SHA-256. */
public final class Canonical {
    public static final ObjectMapper MAPPER = new ObjectMapper();

    private Canonical() {}

    public static String text(JsonNode n) {
        StringBuilder sb = new StringBuilder();
        write(n, sb);
        return sb.toString();
    }

    private static void write(JsonNode n, StringBuilder sb) {
        if (n.isObject()) {
            List<String> names = new ArrayList<>();
            Iterator<String> it = n.fieldNames();
            while (it.hasNext()) {
                names.add(it.next());
            }
            Collections.sort(names);
            sb.append('{');
            boolean first = true;
            for (String f : names) {
                if (!first) {
                    sb.append(',');
                }
                first = false;
                sb.append(new com.fasterxml.jackson.databind.node.TextNode(f).toString()).append(':');
                write(n.get(f), sb);
            }
            sb.append('}');
        } else if (n.isArray()) {
            sb.append('[');
            for (int i = 0; i < n.size(); i++) {
                if (i > 0) {
                    sb.append(',');
                }
                write(n.get(i), sb);
            }
            sb.append(']');
        } else {
            sb.append(n.toString());
        }
    }

    public static String sha256(String s) {
        try {
            byte[] h = MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : h) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    public static String digestOf(JsonNode n) {
        return sha256(text(n));
    }
}
