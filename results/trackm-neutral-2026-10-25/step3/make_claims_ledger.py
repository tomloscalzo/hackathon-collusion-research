"""Step 3, Step A: the claims ledger, built from Step 2's tables/candidates.csv plus the Step 3 columns (research question, criterion, novelty, paper-ready, examples).
usage: make_claims_ledger.py CANDIDATES_CSV OUT_CSV"""
import csv, sys
EXTRA = {
 1: ('1.1, 2.1', 'Impact Potential & Innovation; Execution Quality', 'known', 'yes', 'headline-chat__p1__w0__s42__t1'),
 2: ('evaluation design (AUD-EVAL); 1.1', 'Execution Quality; Impact Potential & Innovation', 'new angle', 'yes, with caveat: the declared rounds 1 to 20 window is nearly empty, use the all-rounds view and say so', 'headline-chat__p3__w0__s42__t1'),
 3: ('3.4, 1.5, 2.3', 'Impact Potential & Innovation', 'new', 'with caveat: idle threat, text only, keyword-rule agreement flag, hand-label accuracy differs by run', 'd-cot-monitor-a__p1__w0__s118__t1'),
 4: ('2.3; alignment (AUD-ALN)', 'Impact Potential & Innovation', 'new angle', 'with caveat: the question may invite a 1; placebo constant', 'd-conflict__p1__w0__s42__t1'),
 5: ('3.4, 1.5', 'Impact Potential & Innovation; Execution Quality', 'new angle', 'yes, as an inconclusive result with its width', 'headline-monitored__p1__w0__s42__t1'),
 6: ('1.1', 'Execution Quality', 'known', 'with caveat: mode-dependent', 'headline-tacit__p5__w0__s42__t1'),
 7: ('evaluation design (AUD-EVAL)', 'Execution Quality', 'known', 'yes', 'ctl-32b-compete__p3__w0__s42__t1'),
 8: ('1.5', 'Impact Potential & Innovation', 'new angle', 'with caveat: changes the opening, not conduct', 'start-5tick__p3__w0__s42__t1'),
 9: ('1.3, 2.2, 2.3', 'Execution Quality; Impact Potential & Innovation', 'new angle', 'with caveat: no hand-labelled ground truth', 'ctl-32b-compete__p3__w0__s42__t1'),
 10: ('2.2', 'Execution Quality', 'new angle', 'not yet: a blind hand-labelled sample of agreement and undercut rounds', 'headline-chat__p1__w0__s42__t1'),
 11: ('2.1, 2.3', 'Execution Quality', 'known', 'not yet: validation of the intent rules', 'headline-chat__p1__w0__s42__t1'),
 12: ('1.1 (design)', 'Execution Quality', 'n/a', 'yes, as a stated limitation', ''),
 13: ('3.4', 'Impact Potential & Innovation', 'new angle', 'not yet: a blind check of the explicit-agreement flag', ''),
 14: ('evaluation design (AUD-EVAL)', 'Execution Quality', 'known', 'not yet', ''),
 15: ('2.3', 'Execution Quality', 'known', 'no', ''),
 16: ('1.2, 3.2', 'Execution Quality', 'known', 'with caveat: a response to a scripted defection, not a lever', 'n3-cheater__p3__w3__s115__t1'),
 17: ('evaluation design (AUD-EVAL)', 'Execution Quality', 'known', 'not yet', ''),
 18: ('3.4', 'Execution Quality', 'n/a', 'no: retract', ''),
}
rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8')))
H = ['rank', 'claim (one plain sentence)', 'evidence (X of Y or effect with 95% CI, n pairs, source)', 'strength', 'robustness checks passed/failed (both runs, both thinking modes, originals vs reruns, family correction)',
     'main caveat', 'declared/exploratory', 'research question(s)', 'judging criterion served', 'novelty (known / new angle / new)', 'paper-ready (yes / with caveat / not yet: what is missing)', 'example trial ids', 'source table']
with open(sys.argv[2], 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f, lineterminator='\n'); w.writerow(H)
    for r in rows:
        k = int(r['rank']); e = EXTRA[k]
        rob = 'both runs: %s; both thinking modes: %s; family correction: %s' % (r['holds_in_both_runs'], r['holds_in_both_thinking_modes'], r['survives_family_correction'])
        w.writerow([k, r['candidate'], r['evidence (n = 20 (wording, seed) pairs unless stated)'], r['strength'], rob, r['main_caveat'], r['declared_or_exploratory'], e[0], e[1], e[2], e[3], e[4], r['source_table']])
