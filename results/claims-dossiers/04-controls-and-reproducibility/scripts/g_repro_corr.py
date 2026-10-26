import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
o = load('oss')
HEADMAP = {'hrep-fx-chat-p1': ('headline-chat', 1), 'hrep-nx-chat-p1': ('headline-chat', 1), 'hrep-fx-tacit-p1': ('headline-tacit', 1),
           'hrep-nx-tacit-p1': ('headline-tacit', 1), 'hrep-fx-chat-p5': ('headline-chat', 5)}
rows = []
for m in MCOLS:
    H = []; Rp = []; grp = {}
    for arm, (h, p) in HEADMAP.items():
        ix, a, b = pairdiff(sel(o, arm), sel(o, h, p), m)
        H += list(b); Rp += list(a); grp[arm] = (b, a)
    H = np.array(H); Rp = np.array(Rp)
    sp = np.corrcoef(pd.Series(H).rank(), pd.Series(Rp).rank())[0, 1]; pe = np.corrcoef(H, Rp)[0, 1]
    # within-cell centred (remove cell level) so that cell differences do not inflate the correlation
    Hc = []; Rc = []
    for arm, (b, a) in grp.items():
        Hc += list(b - b.mean()); Rc += list(a - a.mean())
    Hc = np.array(Hc); Rc = np.array(Rc)
    rows.append(dict(metric=MNAME[m], n_pairs=len(H), pearson=pe, spearman=sp, pearson_cell_centred=np.corrcoef(Hc, Rc)[0, 1],
                     spearman_cell_centred=np.corrcoef(pd.Series(Hc).rank(), pd.Series(Rc).rank())[0, 1], sd_headline=H.std(ddof=1), sd_replicate=Rp.std(ddof=1)))
R = pd.DataFrame(rows); R.to_csv(OUT + '/g_repro_correlations.csv', index=False, float_format='%.4f'); print(R.round(3).to_string())
