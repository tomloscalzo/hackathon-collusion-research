# Replicates PayoffFunctions.nashTickMultiple: j* and span (sM - s^N) per (tick, N, phi, sBar), s0 = 1.
def vol(s, sb): return max(0.0, 1 - s / sb)
def jstar(t, n, phi, sb):
    c = (1 - phi) + phi / n
    best = 1; j = 2
    while True:
        sj = 1 + j * t
        if sj >= sb: break
        if (j - 1) * c * vol(1 + (j - 1) * t, sb) <= j * vol(sj, sb) / n + 1e-12: best = j
        j += 1
    return best
for t in (0.25, 0.5):
    print('tick', t, ' rows N,phi; cols sBar 2,3,5,8,12 ; entries j*/steps-of-collusion (span/tick)')
    for n in (2, 3, 4, 6, 10):
        for phi in (0.0, 0.3, 0.6):
            out = []
            for sb in (2, 3, 5, 8, 12):
                j = jstar(t, n, phi, sb)
                span = max(0.0, (1 + sb) / 2 - (1 + j * t))
                out.append('%d/%d' % (j, int(span / t + 1e-9)))
            print('  N=%-2d phi=%.1f  ' % (n, phi), ' '.join('%6s' % x for x in out))
