import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
o = load('oss'); DRIFT = 0.1044  # pooled replicate-minus-headline price index (99 pairs)
DRIFT_PGI = 0.1098
HC1, HC3, HC5, HT1, HT5 = ('headline-chat', 1), ('headline-chat', 3), ('headline-chat', 5), ('headline-tacit', 1), ('headline-tacit', 5)
C = []  # (label, family, arm, p, control arm, control p)
for a in ['d-conflict', 'd-conflict-ethics', 'd-cot-monitor-a', 'd-placebo', 'd-temptation-a', 'd-temptation-b', 'r2f-confidant', 'r2s-confidant', 'r3f-public', 'r3s-public', 'r4-announced',
          'moral-prime', 'moral-prime-b', 'moral-placebo', 'wd-ask-noreport', 'wd-noncomp', 'wd-notice-only']:
    C.append((a, 'vs headline-chat p1', a, 1, *HC1))
for a in ['m-asym', 'm-inc-joint', 'm-inc-target', 'n3-cheater', 'n3-ethics', 'n3-group', 'start-5tick', 'ctl-32b-compete', 'ctl-32b-joint']:
    C.append((a, 'vs headline-chat p3', a, 3, *HC3))
C += [('headline-chat p1 - tacit p1 (chat)', 'headline contrasts', *HC1, *HT1), ('headline-chat p5 - tacit p5 (chat)', 'headline contrasts', *HC5, *HT5),
      ('headline-chat p5 - p1 (penalty)', 'headline contrasts', *HC5, *HC1), ('headline-chat p3 - p1 (penalty)', 'headline contrasts', *HC3, *HC1),
      ('headline-tacit p5 - p1 (penalty)', 'headline contrasts', *HT5, *HT1)]
for a, p, h in [('fx-chat-p1', 1, HC1), ('nx-chat-p1', 1, HC1), ('fx-tacit-p1', 1, HT1), ('nx-tacit-p1', 1, HT1), ('fx-chat-p5', 5, HC5)]:
    C.append((a, 'formula/no-numbers vs headline (other run root)', a, p, *h))
C += [('fx-chat-p1 - nx-chat-p1 (formula minus no-numbers)', 'formula/no-numbers vs headline (other run root)', 'fx-chat-p1', 1, 'nx-chat-p1', 1),
      ('fx-ctl-joint - ctl-32b-joint', 'formula/no-numbers vs headline (other run root)', 'fx-ctl-joint', 3, 'ctl-32b-joint', 3)]
rows = []
for lab, fam, a, pa, b, pb in C:
    A = sel(o, a, pa); B = sel(o, b, pb)
    ra = set(A.source_root); rb = set(B.source_root); wa = set(A.wave); wb = set(B.wave)
    # waves are matched by wave number mod 100 (1xx = second batch of the same pair blocks)
    r1 = contrast(A, B, 'price_index'); r2 = contrast(A, B, 'profit_gain_index')
    sh = lambda lo, hi, dr: (lo > dr or hi < -dr) if True else None
    eff = r1['diff']; same_root = ra == rb
    same_batch = (min(wa) >= 100) == (min(wb) >= 100)
    # robust to drift: CI of |effect| after moving it DRIFT toward zero still excludes 0
    s = np.sign(eff); lo, hi = (r1['ci_lo'], r1['ci_hi'])
    shifted_lo, shifted_hi = lo - s * DRIFT, hi - s * DRIFT
    excl0 = (lo > 0) or (hi < 0)
    robust = (shifted_lo > 0) if s > 0 else (shifted_hi < 0)
    rows.append(dict(contrast=lab, family=fam, arm=a, control=f'{b} p{pb}', n_pairs=r1['n_pairs'], price_diff=eff, price_lo=lo, price_hi=hi, price_p=r1['p_signflip'],
                     pgi_diff=r2['diff'], pgi_lo=r2['ci_lo'], pgi_hi=r2['ci_hi'], pgi_p=r2['p_signflip'],
                     same_run_root=same_root, same_wave_batch=same_batch, arm_waves=sorted(wa), control_waves=sorted(wb),
                     abs_price_effect_le_drift=abs(eff) <= DRIFT, ci_excludes0=excl0, still_excludes0_after_drift=bool(excl0 and robust)))
L = pd.DataFrame(rows)
L['p_holm_all'] = holm(L.price_p.values)
L.to_csv(OUT + '/g_repro_lever_effects.csv', index=False, float_format='%.5g')
pd.set_option('display.width', 300); pd.set_option('display.max_rows', 200)
print(L[['contrast', 'n_pairs', 'price_diff', 'price_lo', 'price_hi', 'price_p', 'pgi_diff', 'same_run_root', 'same_wave_batch', 'abs_price_effect_le_drift', 'ci_excludes0', 'still_excludes0_after_drift']].round(3).to_string())
print('n contrasts', len(L), '| |price effect| <= drift:', int(L.abs_price_effect_le_drift.sum()), '| CI excl 0:', int(L.ci_excludes0.sum()), '| still excl 0 after drift:', int(L.still_excludes0_after_drift.sum()))
for t in [0.05, 0.10, 0.15, 0.20, 0.30]:
    print(t, int((L.price_diff.abs() <= t).sum()), int((L.pgi_diff.abs() <= t).sum()))
print('cross-root', int((~L.same_run_root).sum()), 'cross-batch', int((~L.same_wave_batch).sum()))
