## Verdict

**What the numbers are.** Every number in this section is a paired difference in the **price index**, (market price - 1) / 2 averaged over rounds, where 0 is competitive and 1 is monopoly. Each comes with its 95% bootstrap CI over (wording, seed) pairs and its Holm-adjusted p. The other four metrics are in the tables below. Qwen = Qwen3-32B with thinking on; gpt-oss = gpt-oss-20b at medium effort. Everything here is **exploratory**. The prime-B, prime-A and placebo controls come from the earlier runs, except in family E.

### 1. No single clause reaches prime B's effect

**Qwen.** Each clause alone does part of what the full prime does. Against the garden placebo:

| Clause alone | Effect | Share of prime B's effect on the same pairs |
|---|---|---|
| Values | {VAL_PL_q} | about {RATIO_VAL_q} |
| Law | {LAW_PL_q} | about {RATIO_LAW_q} |
| Market words | {MKT_PL_q} | about {RATIO_MKT_q} (not Holm-significant) |

On the values arm's pairs, prime B itself gives {PBSAME_VAL_q}. Against prime B directly (family B), only the market-words clause (and the neutral persona) leave prices higher by a Holm-significant margin. Values and law are at p_Holm about 0.07.

**gpt-oss.** No single clause is detectable:

| Clause alone | Effect |
|---|---|
| Values | {VAL_PL_o} |
| Law | {LAW_PL_o} |
| Market words | {MKT_PL_o} |

Prime B on the same pairs gives {PBSAME_VAL_o}. Against prime B, the values clause (and the neutral persona) leave prices Holm-significantly higher.

**There is no two-clause arm.** So whether the clauses *combine*, or are simply each weak, is not tested directly. On Qwen, the three single-clause effects sum to more than prime B's.

### 2. A task-relevant persona without values, law or competition words shows no effect

The length-matched neutral market-maker persona uses the same sentence template.

| Model | Neutral persona against the placebo |
|---|---|
| Qwen | {NMM_PL_q} |
| gpt-oss | {NMM_PL_o} |

On gpt-oss the CI cannot rule out a drop of about half of prime B's effect.

Within the new run, measured against this neutral persona (family E, no between-run drift), Qwen prices are lower under all three clauses:

| Clause (Qwen) | Against the neutral persona |
|---|---|
| Values | {VAL_NMM_q} |
| Law | {LAW_NMM_q} |
| Market words | {MKT_NMM_q} |

On gpt-oss, none of the family E clause contrasts is Holm-significant.

So on Qwen the persona *frame* does nothing by itself, and each kind of content lowers prices somewhat.

### 3. Persona against rule against both

**The rule alone.** The explicit rule ("do not coordinate prices ... set your quotes independently") leaves the price nearly unchanged:

| Model | Rule against the placebo |
|---|---|
| Qwen | {RULE_PL_q} |
| gpt-oss | {RULE_PL_o} |

On Qwen it does raise the competitive share ({RULE_PL_q_cs}) and cut the matching share ({RULE_PL_q_ms}).

**The persona beats the rule on price.** Prime B minus the rule is {PB_RULE_q} (Qwen) and {PB_RULE_o} (gpt-oss).

**Both together.** Prime B plus the rule against the placebo is {BRULE_PL_q} (Qwen, Holm-significant) and {BRULE_PL_o} (gpt-oss, not Holm-significant). Against prime B alone it is {BRULE_PB_q} (Qwen) and {BRULE_PB_o} (gpt-oss). The rule does not add to the persona; these data bound any added price effect at about the lower CI ends shown. The interaction (the rule's effect with the persona minus its effect without) is {INT_q} on Qwen: a non-significant estimate, not a demonstrated sub-additivity.

On Qwen, prime B plus the rule shows the strongest coordination-breaking signature of any arm: competitive share {BRULE_PL_q_cs}, matching share {BRULE_PL_q_ms}.

**Reading.** The persona moves the agreed price. The rule mainly moves the pattern of quotes (less exact matching) on Qwen, not the price.

### 4. Dose: one primed firm moves the market part of the way

**Qwen.** Priming one firm (the other gets the placebo) gives {BONE_PL_q}. Priming the second firm as well adds {PB_BONE_q}. That is about halfway.

**gpt-oss.** The estimates point the same way but are not Holm-significant: {BONE_PL_o} and {PB_BONE_o}.

**Within the one-firm games**, the primed firm and its unprimed rival quote nearly the same on average: {SEAT_q_quote} (Qwen) and {SEAT_o_quote} (gpt-oss) in half-spread units. So the rival's quotes move with the primed firm's. The channel (the chat, or simply seeing the quotes) was not tested.

On gpt-oss the primed firm earns less than its rival, {SEAT_o_profit} per round, because it quotes *above* the rival more often than below. Over all rounds it was above in {SEAT_o_above} rounds, below in {SEAT_o_below} and equal in {SEAT_o_equal}. The firm with the lower quote takes most of the customers.

### 5. How far to trust this

- **Reduced n.** There are {NQ} pairs per new arm on Qwen and {NO} on gpt-oss.
- **Missing wordings on gpt-oss.** Wordings 3 and 4 are mostly missing, so its results rest mainly on 3 of the 5 paraphrases.
- **Historical controls** outside family E.
- **One fixed sentence per condition.** Read the results as a decomposition of these specific texts, not as general claims about "values" or "law".
