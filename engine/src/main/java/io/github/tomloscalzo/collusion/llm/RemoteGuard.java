package io.github.tomloscalzo.collusion.llm;

import java.net.URI;
import java.util.Locale;
import java.util.function.Function;

/**
 * Enforces the owner's rule that no paid or remote call is made unless explicitly allowed: a base URL whose host is not
 * localhost / 127.0.0.1 / ::1 is refused unless the environment variable COLLUSION_ALLOW_REMOTE is "1". A refusal is
 * logged (System.Logger, WARNING; the default handler writes it to stderr) and raised as LlmException.RemoteNotAllowed.
 */
public final class RemoteGuard {
    public static final String ALLOW_ENV = "COLLUSION_ALLOW_REMOTE";
    private static final System.Logger LOG = System.getLogger("collusion.llm.guard");

    private RemoteGuard() {}

    public static boolean isLocalHost(String host) {
        if (host == null) {
            return false;
        }
        String h = host.toLowerCase(Locale.ROOT);
        return h.equals("localhost") || h.equals("127.0.0.1") || h.equals("::1") || h.equals("[::1]");
    }

    public static void check(String baseUrl) {
        check(baseUrl, System::getenv);
    }

    public static void check(String baseUrl, Function<String, String> env) {
        URI u;
        try {
            u = URI.create(baseUrl.trim());
        } catch (RuntimeException e) {
            throw refuse("invalid base URL '" + baseUrl + "'");
        }
        String scheme = u.getScheme() == null ? "" : u.getScheme().toLowerCase(Locale.ROOT);
        if (!scheme.equals("http") && !scheme.equals("https")) {
            throw refuse("base URL '" + baseUrl + "' must be http or https");
        }
        if (isLocalHost(u.getHost())) {
            return;
        }
        if ("1".equals(env.apply(ALLOW_ENV))) {
            return;
        }
        throw refuse("remote host '" + u.getHost() + "' refused: set " + ALLOW_ENV
                + "=1 only after the owner has approved paid calls");
    }

    private static LlmException.RemoteNotAllowed refuse(String why) {
        String msg = "LLM base URL refused: " + why;
        LOG.log(System.Logger.Level.WARNING, msg);
        return new LlmException.RemoteNotAllowed(msg);
    }
}
