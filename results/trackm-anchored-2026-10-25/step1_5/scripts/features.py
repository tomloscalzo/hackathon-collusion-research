"""Step 1.5: build the derived-feature game table. Paths come from arguments (no local paths in the repo copy)."""
import sys, json, re
import numpy as np, pandas as pd

def audit_features(fr):
    fr = fr[fr['cat'].notna()].copy()
    fr['dom'] = fr['cat'].str.contains('dominated')
    fr['floorfloor'] = fr['cat'].eq('rival_at_floor_quote_floor')
    fr['br'] = fr['cat'].eq('best_response')
    fr['hold'] = fr['cat'].eq('collusive_hold')
    fr['match'] = fr['cat'].eq('match_rival')
    fr['oth'] = fr['cat'].eq('other_undercut_not_BR')
    fr['eqr'] = (fr['quote'] - fr['rival_prev']).abs() <= 0.005
    fr['eqo'] = (fr['quote'] - fr['own_prev']).abs() <= 0.005
    fr['novel'] = (fr['is_printed'] == 0) & ~fr['eqr'] & ~fr['eqo']
    fr['und'] = (fr['rival_prev'] < fr['own_prev'] - 0.005) & (fr['rival_prev'] > 1.005)
    fr['lower'] = fr['quote'] < fr['own_prev'] - 0.005
    fr['reach'] = fr['quote'] <= fr['rival_prev'] + 0.005
    g = fr.groupby('trial')
    out = pd.DataFrame({
        'br_rate': g['br'].mean(),
        'dominated_rate': g['dom'].mean(),
        'hold_rate': g['hold'].mean(),
        'match_rate': g['match'].mean(),
        'other_undercut_rate': g['oth'].mean(),
        'rival_floor_quote_floor_rate': g['floorfloor'].mean(),
        'at_br_with_fine_rate': g['at_brf'].mean(),
        'at_br_expost_rate': g['at_br_expost'].mean(),
        'mean_regret_vs_prev': g['regret'].mean(),
        'printed_quote_share': g['is_printed'].mean(),
        'quote_eq_rival_last_share': g['eqr'].mean(),
        'quote_eq_own_last_share': g['eqo'].mean(),
        'novel_quote_share': g['novel'].mean(),
    })
    nf = fr[~fr['floorfloor']]
    out['br_rate_excl_floor_rounds'] = nf.groupby('trial')['br'].mean()
    u = fr[fr['und']]
    out['react_lower_after_undercut'] = u.groupby('trial')['lower'].mean()
    out['react_reach_after_undercut'] = u.groupby('trial')['reach'].mean()
    out['n_undercut_exposures'] = u.groupby('trial').size()
    return out

def build(step1, audit, reading, batch):
    r = pd.read_csv(f'{step1}/run.csv', low_memory=False)
    r = r[r.status == 'done'].copy()
    f = pd.read_csv(f'{step1}/run_firms.csv', low_memory=False)
    f = f[f.row_id.isin(r.row_id)]
    sd = f.groupby('row_id').agg(agreed_then_undercut_rounds=('agreed_then_undercut', 'sum'),
                                 held_after_agreement_rounds=('held_after_agreement', 'sum'),
                                 threat_then_punish_n=('threat_then_punish', 'sum'))
    sd['hold_after_agreement_share'] = sd.held_after_agreement_rounds / (sd.held_after_agreement_rounds + sd.agreed_then_undercut_rounds)
    r = r.merge(sd, left_on='row_id', right_index=True, how='left')
    fr = pd.read_csv(f'{audit}/firmrounds_{batch}.csv', low_memory=False)
    a = audit_features(fr)
    r = r.merge(a, left_on='trial_id', right_index=True, how='left')
    # reading: monitor passages and introspection answers
    mp = pd.read_csv(f'{reading}/out_dset_{batch}/monitor_passages.csv', usecols=['trial_id', 'explicit', 'rule', 'shaped', 'tacit', 'comply'])
    mg = mp.groupby('trial_id').mean().rename(columns={'explicit': 'cot_threat_mention_share', 'rule': 'cot_rule_aware_share',
        'shaped': 'cot_plans_innocent_wording_share', 'tacit': 'cot_indirect_route_share', 'comply': 'cot_independent_share'})
    r = r.merge(mg, left_on='trial_id', right_index=True, how='left')
    ia = pd.read_csv(f'{reading}/out_intro_{batch}/intro_answers_classified.csv', usecols=['trial_id', 'cls'])
    ig = pd.DataFrame({'evasive_answer_share': ia.cls.eq('evasive').groupby(ia.trial_id).mean(),
                       'understated_answer_share': ia.cls.eq('understated').groupby(ia.trial_id).mean()})
    r = r.merge(ig, left_on='trial_id', right_index=True, how='left')
    for c in ['EXPLICIT', 'STRATEGIC-UNNAMED', 'NONE', 'NO_TEXT']:
        r['intent_' + c.lower().replace('-', '_')] = np.where(r.game_intent_class.isna(), np.nan, (r.game_intent_class == c).astype(float))
    r['evidence_ending'] = (r.end_reason == 'EVIDENCE').astype(float)
    r['is_rerun'] = (r.supersession != 'none').astype(float)
    return r

if __name__ == '__main__':
    step1, audit, reading, batch, out = sys.argv[1:6]
    build(step1, audit, reading, batch).to_csv(out, index=False)
