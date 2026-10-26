package io.github.tomloscalzo.collusion.llm;

/** Any failure of the LLM layer (transport, guard, budget, cache miss in replay). */
public class LlmException extends RuntimeException {
    public LlmException(String message) {
        super(message);
    }

    public LlmException(String message, Throwable cause) {
        super(message, cause);
    }

    /**
     * A 200 reply with no choices[0].message.content, no reasoning field and a finish_reason other than "length" (the gpt-oss
     * empty talk reply). Still an LlmException (it is thrown exactly where it always was), but it carries what the server sent,
     * so a caller that has opted in (option empty_talk_as_done, talk calls only) can read it as an empty reply.
     */
    public static final class EmptyContent extends LlmException {
        private final transient LlmResponse response;

        public EmptyContent(String message, LlmResponse response) {
            super(message);
            this.response = response;
        }

        /** The reply as the server sent it: empty text, its tokens and finish_reason. */
        public LlmResponse response() {
            return response;
        }
    }

    /** The remote-host guard refused a base URL. */
    public static final class RemoteNotAllowed extends LlmException {
        public RemoteNotAllowed(String message) {
            super(message);
        }
    }

    /** ReplayLlmClient found no cache entry for the request. */
    public static final class CacheMiss extends LlmException {
        public CacheMiss(String message) {
            super(message);
        }
    }

    /** A run-level budget reservation would be exceeded. */
    public static final class BudgetExceeded extends LlmException {
        public BudgetExceeded(String message) {
            super(message);
        }
    }
}
