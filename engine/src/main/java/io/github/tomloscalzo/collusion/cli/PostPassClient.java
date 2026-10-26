package io.github.tomloscalzo.collusion.cli;

import io.github.tomloscalzo.collusion.agents.llm.QuestionKeys;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmException;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.llm.LlmResponse;

/**
 * The client of the post-game pass (C13.4, proposal F2): a post-game question call ({@code question|<name>|post|...})
 * goes to the live client (through the trial's cache, so a rerun replays it too); every other call (quote, talk, probe,
 * an in-game question) must be served by the replay of the trial's own cache, and a miss fails the pass at once, with
 * nothing sent to the server: the pass makes zero game-call misses by construction.
 */
final class PostPassClient implements LlmClient {
    private final LlmClient replay;
    private final LlmClient live;
    private long game;
    private long post;

    PostPassClient(LlmClient replay, LlmClient live) {
        this.replay = replay;
        this.live = live;
    }

    static boolean isPost(String drawKey) {
        return QuestionKeys.isQuestionKey(drawKey) && QuestionKeys.parse(drawKey).mode() == QuestionKeys.Mode.POST;
    }

    @Override
    public LlmResponse complete(LlmRequest request) {
        if (isPost(request.drawKey())) {
            post++;
            return live.complete(request);
        }
        game++;
        try {
            return replay.complete(request);
        } catch (LlmException.CacheMiss e) {
            throw new IllegalStateException("post-game pass: a game call is not in the trial's cache (draw "
                    + request.drawKey() + "); the pass needs the finished game's own cache, unchanged", e);
        }
    }

    long gameCalls() {
        return game;
    }

    long postCalls() {
        return post;
    }
}
