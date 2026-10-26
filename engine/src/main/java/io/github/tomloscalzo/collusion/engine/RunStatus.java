package io.github.tomloscalzo.collusion.engine;

/**
 * How a run ended. HORIZON: random or known horizon reached; MAX_ROUNDS: the undisclosed cap truncated it;
 * TRIGGER_ONLY: detection trigger without evidence (rents end, no fine, pi_post is the terminal value, T30);
 * EVIDENCE: trigger plus evidence (fine F charged to members, static-Nash terminal value).
 */
public enum RunStatus { HORIZON, MAX_ROUNDS, TRIGGER_ONLY, EVIDENCE }
