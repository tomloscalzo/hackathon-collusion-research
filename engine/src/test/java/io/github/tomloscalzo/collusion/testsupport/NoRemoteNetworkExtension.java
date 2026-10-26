package io.github.tomloscalzo.collusion.testsupport;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Proxy;
import java.net.ProxySelector;
import java.net.SocketAddress;
import java.net.URI;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.junit.jupiter.api.extension.AfterEachCallback;
import org.junit.jupiter.api.extension.BeforeAllCallback;
import org.junit.jupiter.api.extension.ExtensionContext;

/**
 * Test-only network guard, registered for every test class by JUnit's extension auto-detection
 * (src/test/resources/junit-platform.properties and META-INF/services). Two rules:
 *
 * <ol>
 *   <li>The test JVM must not see {@code COLLUSION_ALLOW_REMOTE=1}. Surefire removes the variable from the forked JVM
 *       (pom.xml, excludedEnvironmentVariables); this check catches IDE runs and other launchers that do not.</li>
 *   <li>No test may open a connection to a non-loopback host. The JVM-wide default {@link ProxySelector}, which
 *       java.net.http.HttpClient, HttpURLConnection and plain java.net.Socket consult before connecting, is replaced by
 *       one that routes every non-loopback URI to a dead loopback port (an HTTP proxy for http/https, a SOCKS proxy for
 *       socket:// so that raw sockets do not connect directly) and records it; the test that caused it then fails.</li>
 * </ol>
 *
 * Limits: DNS lookups are not intercepted, a socket created with {@code new Socket(Proxy.NO_PROXY)} bypasses any
 * selector, and a violation from a background thread is reported against the test that is running when it is noticed.
 *
 * The engine's own RemoteGuard is the production rule; this is the independent check that the tests themselves never
 * reach the network, whatever the environment.
 */
public final class NoRemoteNetworkExtension implements BeforeAllCallback, AfterEachCallback {
    /** Port 9 (discard) on loopback: nothing listens there, so a routed connection fails at once. */
    static final Proxy DEAD_END = new Proxy(Proxy.Type.HTTP, new InetSocketAddress("127.0.0.1", 9));
    /** The same for raw sockets (socket:// URIs): an HTTP-type proxy would make SocksSocketImpl connect directly. */
    static final Proxy DEAD_END_SOCKS = new Proxy(Proxy.Type.SOCKS, new InetSocketAddress("127.0.0.1", 9));
    private static final List<String> VIOLATIONS = new ArrayList<>();
    private static final ProxySelector GUARD = new ProxySelector() {
        @Override
        public List<Proxy> select(URI uri) {
            String host = uri.getHost();
            if (isLoopback(host)) {
                return List.of(Proxy.NO_PROXY);
            }
            synchronized (VIOLATIONS) {
                VIOLATIONS.add(String.valueOf(uri));
            }
            return List.of("socket".equalsIgnoreCase(uri.getScheme()) ? DEAD_END_SOCKS : DEAD_END);
        }

        @Override
        public void connectFailed(URI uri, SocketAddress sa, IOException ioe) {
            // expected for routed (blocked) connections
        }
    };

    static {
        ProxySelector.setDefault(GUARD);
    }

    public static boolean isLoopback(String host) {
        if (host == null) {
            return false;
        }
        String h = host.toLowerCase(Locale.ROOT);
        if (h.startsWith("[") && h.endsWith("]")) {
            h = h.substring(1, h.length() - 1);
        }
        return h.equals("localhost") || h.equals("::1") || h.equals("0:0:0:0:0:0:0:1") || h.startsWith("127.");
    }

    /** The blocked URIs recorded so far and cleared (for the guard's own test). */
    public static List<String> drainViolations() {
        synchronized (VIOLATIONS) {
            List<String> out = new ArrayList<>(VIOLATIONS);
            VIOLATIONS.clear();
            return out;
        }
    }

    @Override
    public void beforeAll(ExtensionContext context) {
        if ("1".equals(System.getenv("COLLUSION_ALLOW_REMOTE"))) {
            throw new IllegalStateException("COLLUSION_ALLOW_REMOTE=1 is visible to the test JVM. Tests must run without it "
                    + "(Maven's surefire removes it; unset it in the IDE or shell that launched the tests).");
        }
        if (ProxySelector.getDefault() != GUARD) {
            ProxySelector.setDefault(GUARD);
        }
    }

    @Override
    public void afterEach(ExtensionContext context) {
        List<String> v = drainViolations();
        if (!v.isEmpty()) {
            throw new AssertionError("test " + context.getDisplayName() + " tried to reach a non-loopback host (blocked): " + v);
        }
    }
}
