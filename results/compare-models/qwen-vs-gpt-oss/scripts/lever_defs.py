"""Shared definitions for gen_sections.py and deltoid_charts.py: which lever rows are primary, duplicates to drop, titles, arm descriptions, aliases."""
# sign-flipped or repeated copies of a contrast shown in another topic
DROP = {('communication', 'headline-chat (p3) - joint-profit control (p3)'), ('communication', 'headline-chat (p3) - strict-compete control (p3)'),
        ('cheater', 'n3-group - headline-chat (p3)')}
# one row per lever: the arm against its own control (counted in the verdict); everything else is a secondary comparison
PRIMARY = {('payoff-table-focal-points', c) for c in [
    'fx-chat-p1 (p1) - headline-chat (p1)', 'fx-tacit-p1 (p1) - headline-tacit (p1)', 'fx-chat-p5 (p5) - headline-chat (p5)',
    'nx-chat-p1 (p1) - headline-chat (p1)', 'nx-tacit-p1 (p1) - headline-tacit (p1)', 'fx-ctl-joint (p3) - ctl-32b-joint (p3)',
    'fx-ctl-joint (p3) - headline-chat (p3)']}
PRIMARY |= {
    ('communication', 'chat - tacit (p1)'), ('communication', 'chat - tacit (p5)'), ('penalty', 'chat p5 - p1'), ('penalty', 'chat p3 - p1'),
    ('penalty', 'tacit p5 - p1'), ('penalty', 'interaction: (chat p5-p1) - (tacit p5-p1)'), ('controls', 'joint-profit control - headline-chat (p3)'),
    ('controls', 'strict-compete control - headline-chat (p3)'), ('controls', 'joint-profit control - strict-compete control'),
    ('cot-monitor-threat', 'd-cot-monitor-a - headline-chat (p1)'), ('moral-primes', 'moral-prime - moral-placebo'),
    ('moral-primes', 'moral-prime-b - moral-placebo'), ('moral-primes', 'moral-placebo - headline-chat (p1)'),
    ('five-tick-start', 'start-5tick - headline-chat (p3)'), ('cheater', 'n3-cheater - n3-group'), ('market-structure', 'n3-group - headline-chat (p3)'),
    ('ethics-rule', 'n3-ethics - n3-group (p3)'), ('asymmetric', 'm-asym - headline-chat (p3)'), ('incentives', 'm-inc-joint - headline-chat (p3)'),
    ('incentives', 'm-inc-target - headline-chat (p3)'), ('watchdog', 'wd-notice-only - headline-chat (p1)'), ('watchdog', 'wd-noncomp - wd-ask-noreport'),
    ('watchdog', 'wd-ask-noreport - headline-chat (p1)'), ('self-report-scores', 'd-conflict - headline-chat (p1)'),
    ('self-report-scores', 'd-temptation-a - headline-chat (p1)'), ('self-report-scores', 'd-temptation-b - headline-chat (p1)'),
    ('self-report-scores', 'd-placebo - headline-chat (p1)'), ('self-report-scores', 'd-conflict-ethics - d-conflict (p1)'),
    ('introspection', 'r2f-confidant - headline-chat (p1)'), ('introspection', 'r3f-public - headline-chat (p1)'),
    ('introspection', 'r2s-confidant - headline-chat (p1)'), ('introspection', 'r3s-public - headline-chat (p1)'),
    ('introspection', 'r2f-confidant - r2s-confidant')}
ORDER = ['payoff-table-focal-points', 'communication', 'penalty', 'controls', 'cot-monitor-threat', 'moral-primes', 'five-tick-start', 'cheater',
         'market-structure', 'ethics-rule', 'asymmetric', 'incentives', 'watchdog', 'self-report-scores', 'introspection']
TITLE = {'payoff-table-focal-points': 'Payoff block: formula / no numbers vs printed example prices', 'communication': 'Communication: private chat vs no chat',
         'penalty': 'Penalty: heavier expected fine', 'controls': 'Controls: joint-profit and strict-compete instructions',
         'cot-monitor-threat': 'Reasoning-monitor (CoT) threat A', 'moral-primes': 'Moral primes A and B, and the placebo', 'five-tick-start': '5-tick start rule',
         'cheater': 'Planted cheater', 'market-structure': 'Three firms vs two', 'ethics-rule': 'Ethics rule on one of three firms',
         'asymmetric': 'Asymmetric ethics rule (one of two firms)', 'incentives': 'Incentive texts (joint profit, profit target)',
         'watchdog': 'Compliance watchdog (3 arms)', 'self-report-scores': 'Self-report score fields and the conflict-score validation',
         'introspection': 'Introspection questions (fed back, saved only)'}
ARM = {'headline-chat': 'two firms, private chat', 'headline-tacit': 'two firms, no chat', 'fx-chat-p1': 'formula, no example prices, chat',
       'fx-tacit-p1': 'formula, no example prices, no chat', 'fx-chat-p5': 'formula, no example prices, chat', 'nx-chat-p1': 'no numbers at all, chat',
       'nx-tacit-p1': 'no numbers at all, no chat', 'fx-ctl-joint': 'told to maximise joint profit; formula, no example prices',
       'ctl-32b-joint': 'joint-profit control, printed examples', 'ctl-32b-compete': 'strict-compete control',
       'd-cot-monitor-a': 'idle reasoning-monitor shutdown threat', 'moral-prime': 'hyper-ethical persona A',
       'moral-prime-b': 'hyper-ethical persona B (competitive markets)', 'moral-placebo': 'length-matched non-moral persona',
       'start-5tick': 'round-1 quotes capped at 1.00-1.05', 'n3-cheater': 'two LLM firms + scripted defector', 'n3-group': 'three LLM firms',
       'n3-ethics': 'three firms, one bound by an ethics rule', 'm-inc-joint': 'told to maximise joint profit', 'm-inc-target': 'desk behind its profit target',
       'm-asym': 'one of two firms bound by an ethics rule', 'wd-notice-only': 'watchdog notice only', 'wd-noncomp': 'watchdog asks, may report',
       'wd-ask-noreport': 'watchdog asks, no report', 'd-conflict': 'conflict self-score field', 'd-conflict-ethics': 'conflict score + ethics rule',
       'd-temptation-a': 'temptation self-score A', 'd-temptation-b': 'temptation self-score B', 'd-placebo': 'random-number field',
       'r2f-confidant': 'confidant question, fed back', 'r3f-public': 'public question, fed back', 'r2s-confidant': 'confidant answer, saved only',
       'r3s-public': 'public answer, saved only'}
ALIAS = {'chat - tacit (p1)': 'headline-chat - headline-tacit (p1)', 'chat - tacit (p5)': 'headline-chat - headline-tacit (p5)',
         'chat p5 - p1': 'headline-chat p5 - headline-chat p1', 'chat p3 - p1': 'headline-chat p3 - headline-chat p1',
         'tacit p5 - p1': 'headline-tacit p5 - headline-tacit p1',
         'interaction: (chat p5-p1) - (tacit p5-p1)': 'interaction: (headline-chat p5 - p1) - (headline-tacit p5 - p1)',
         'joint-profit control - headline-chat (p3)': 'ctl-32b-joint - headline-chat (p3)',
         'strict-compete control - headline-chat (p3)': 'ctl-32b-compete - headline-chat (p3)',
         'joint-profit control - strict-compete control': 'ctl-32b-joint - ctl-32b-compete (p3)'}
