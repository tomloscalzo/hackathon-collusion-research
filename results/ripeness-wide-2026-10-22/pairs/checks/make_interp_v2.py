import json, re, os, shutil
D = r"<local>\hackathon\work_scratch\wide\pairs_out"

# Directions claimed in v1 are reused unchanged (exec the v1 text section only; it writes nothing).
_src = open(D + r"\make_interp.py", encoding="utf8").read().split("# ---------------- checks")[0]
_ns = {}
exec(_src, _ns)
C = _ns["C"]
T_OLD = _ns["T"]

# Glosses (Term name first, then a plain gloss)
TH = "collusion intensity (how far the chosen spread sits between the competitive and the monopoly level)"
PAT = "patience (the chance the market continues another round)"
NMM = "number of market makers (competing firms)"
PHI = "preferenced volume share (the share of orders split evenly between firms whatever their price)"
TICK = "tick size (the minimum price step)"
SLOPE = "regulator screen slope (how strongly the regulator's screen, its rule for opening investigations, reacts to wide spreads)"
SCR = "the regulator's screen (its rule for opening investigations when spreads are wide)"
TIP = "tip probability (the chance each round that an investigation starts from a tip, whatever the price)"
TIPS = "tips (investigations that start at random, whatever the price)"
EV = "P(evidence | investigation) (the chance an investigation produces a guilty finding)"
FINE = "fine ratio (the fine as a multiple of a firm's full-collusion profit for a round)"
ROOM = 'reservation spread ratio (the room between cost and the spread at which customers stop trading; "room" below)'
ART = "a modelling simplification in markets with a minimum price step (an investigation that finds nothing is treated as worse for firms than a conviction)"
ART_S = "a modelling simplification for such markets (an investigation that finds nothing is treated as worse for firms than a conviction)"

T = {}
def put(k, m, text):
    T.setdefault(k, {})[m] = " ".join(text.split())

# ---------------- delta pairs ----------------
put("delta__N", "share", f"""It appears that the share of scenarios where collusion is chosen rises with {PAT}, peaks at fairly high but not the highest patience, and then eases off, while it falls steadily as the {NMM} grows. These inputs interact strongly: impatient firms in markets with many market makers almost never collude, most likely because each firm gets only a small slice of cartel profit while undercutting wins most of the market for a round. Among very patient firms the number of market makers hardly matters, because the threat of losing future profits holds even large cartels together. The dip at the most patient end appears to come from {ART}: patient firms weigh heavily the ordinary earnings that such an investigation wipes out.""")
put("delta__N", "theta", f"""It appears that {TH} rises with {PAT} up to fairly high levels and then falls, and that it is lower the larger the {NMM}. The peak shifts towards more patient values as the number of market makers grows, most likely because larger cartels need more patience before they can hold any raised price at all. Past the peak, very patient cartels appear to moderate their prices to avoid drawing the regulator's attention, since they have more future profit to lose, with {ART} adding to that fall. At the most patient end the number of market makers barely changes how hard the cartel pushes prices.""")

put("delta__phi", "share", f"""It appears that collusion becomes more common as the {PHI} grows, and that it rises with {PAT} before easing off at the most patient end. Volume that is split evenly whatever the price cannot be won by undercutting, so it most likely shrinks the reward for cheating on the cartel. That help matters most among impatient firms and almost disappears once firms are patient enough to hold the cartel together anyway. At the very highest patience the preferenced volume share even has a slightly reversed effect, which seems to come from small markets with a minimum price step and from {ART_S}.""")
put("delta__phi", "theta", f"""It appears that {TH} rises with the {PHI} and follows a rise-then-fall pattern in {PAT}. The preferenced volume share makes the biggest difference among impatient firms, most likely because fewer of their cartels are forced to keep prices below what they would like in order to stop members cheating. Once firms are patient, the lines for different preferenced volume shares come together, because the temptation to cheat no longer limits the price. The fall at high patience appears to reflect patient cartels choosing caution to protect their future profits, plus {ART}.""")

put("delta__tick", "share", f"""It appears that a larger {TICK} generally lowers the share of colluding scenarios, while {PAT} raises it up to fairly high levels before it eases off. The tick size cuts both ways: among impatient firms a moderate price step actually helps the cartel, most likely because undercutting by a whole step is a big cut when margins are thin, and the price war drops below what firms earn in normal competition with a price step. Among very patient firms the markets with a price step fall away while markets without a price step keep rising. That late fall appears to be {ART}, not a real effect of patience: it disappears when every investigation ends in a conviction.""")
put("delta__tick", "theta", f"""It appears that {TH} rises then falls with {PAT}, and that a larger {TICK} lowers it at most patience levels. Without a price step, intensity keeps rising until very high patience and then eases only a little, which seems to be genuine caution by cartels protecting their future profits. With a large price step it peaks earlier and drops much more, which appears to be mostly {ART}. A price step also most likely forces the cartel to move in whole steps, so it cannot fine-tune a modest, less conspicuous price.""")

put("delta__slope", "share", f"""It appears that a steeper {SLOPE} sharply reduces collusion at every level of {PAT}, making it the main deterrent in this chart. Patience raises the share up to fairly high levels, because the threat of a price war then holds the cartel together, and the curve for each screen slope peaks there. The drop at the most patient end seems to come from {ART}, which matters because patient firms value highly the ordinary earnings such an investigation destroys; without a price step the share simply levels off.""")
put("delta__slope", "theta", f"""It appears that {TH} drops steeply as the {SLOPE} rises, and that it rises then falls with {PAT}. With no screen, colluding firms most likely go all the way to the full-collusion price, because a higher price carries no extra risk of investigation. With any screen, every extra bit of price raises the chance of an investigation that would end the cartel, and very patient cartels, having the most future profit at stake, appear to hold prices down further. Even a gentle screen slope seems to bite hard on how far prices are pushed.""")

put("delta__rhoTip", "share", f"""It appears that a higher {TIP} reduces collusion, while {PAT} raises it up to fairly high levels before it eases off. Because a tip can start an investigation at any price, the cartel cannot avoid it by pricing modestly; it most likely shortens the cartel's expected life and so weakens the hold of future profits. Patience partly offsets this, since in markets with no minimum price step the share keeps rising with patience even when tips are possible. The fall at the most patient end appears to be {ART}, which makes a tip-started investigation that finds nothing especially costly.""")
put("delta__rhoTip", "theta", f"""It appears that average {TH} falls as the {TIP} rises, and rises then falls with {PAT}. The fall with tips seems to come mainly from fewer cartels forming: among cartels that do form, tips actually push prices higher, most likely because staying inconspicuous helps little when a whistleblower may expose the cartel anyway. That price-raising effect appears strongest among the most patient firms, which would otherwise be the most cautious.""")

put("delta__pEvidence", "share", f"""It appears that collusion becomes less common as {EV} rises, because the expected fine rises, and that {PAT} raises collusion up to fairly high levels. Among the most patient firms the pattern dips and then recovers as a guilty finding becomes certain. That recovery appears to come from {ART}, so a higher chance of a guilty finding looks less bad to firms. In markets with no minimum price step, a higher chance of a guilty finding lowers collusion steadily.""")
put("delta__pEvidence", "theta", f"""It appears that {TH} falls as {EV} rises, most likely because each extra bit of price then carries a larger expected fine; the effect looks strongest at moderate {PAT}. Intensity rises then falls with patience. Among the most patient firms intensity dips and then rises again as a guilty finding becomes certain, which appears to be {ART} rather than real economics.""")

put("delta__fineRatio", "share", f"""It appears that a higher {FINE} steadily reduces collusion at every level of {PAT}, as long as {SCR} or {TIPS} can start an investigation. Patience raises the share at every fine ratio up to fairly high values, most likely because the threat of a price war holds patient cartels together. When the fine ratio is small, the share drops again among the most patient firms, which appears to be {ART} rather than an effect of patience itself.""")
put("delta__fineRatio", "theta", f"""It appears that {TH} falls as the {FINE} rises at every level of {PAT}, most likely because each extra bit of price raises the chance of an investigation and therefore the expected fine. Intensity rises then falls with patience at every fine ratio. Under very high fine ratios the patience levels converge on low intensity, suggesting that once fines are severe, patience makes little difference to how far prices are pushed.""")

put("delta__sBarRatio", "share", f"""It appears that collusion peaks at middle values of the {ROOM}, and rises then falls with {PAT}. This seems to be the sum of opposing effects. In markets with no minimum price step, more room means the same degree of collusion produces a wider spread that {SCR} notices more, so collusion falls; in markets with a minimum price step, a narrow room leaves few or no price steps above normal competition, so collusion rises with room. Patience lifts collusion at every reservation spread ratio, and the dip at the most patient end appears to be {ART}.""")
put("delta__sBarRatio", "theta", f"""It appears that {TH} peaks at a fairly low, but not the lowest, {ROOM}, and rises then falls with {PAT}. In markets with no minimum price step, intensity falls steadily as the room widens, most likely because the same degree of collusion is a wider spread that {SCR} notices more. The narrowest room is pulled down by markets with a minimum price step, where a large step leaves no space to collude and a smaller step offers only an all-or-nothing jump to the full-collusion price.""")

# ---------------- N pairs ----------------
put("N__phi", "share", f"""It appears that collusion falls as the {NMM} grows and rises with the {PHI}. The preferenced volume share helps most when there are many market makers, where the temptation to undercut is greatest, because evenly split volume cannot be won by cheating. With very few market makers it makes almost no difference, or even hurts slightly, most likely because in small markets with a minimum price step a higher preferenced volume share raises ordinary competitive earnings, leaving less space to collude and more exposure to {ART_S}.""")
put("N__phi", "theta", f"""It appears that {TH} falls with the {NMM} and rises with the {PHI}, and the lines fan out: the preferenced volume share barely matters with very few market makers but makes a large difference when there are many. This is most likely because it eases the temptation to cheat, so fewer large cartels are forced to hold prices below the level they would prefer.""")

put("N__tick", "share", f"""It appears that collusion falls as the {NMM} and the {TICK} grow, but a larger price step hurts much less when there are many market makers. A price step seems to bring an offsetting benefit there: undercutting by a whole step is a big cut when each firm's margin is thin, and the price war falls below normal earnings in markets with a price step, so more large cartels can hold together. With very few market makers only the costs show: fewer prices to choose from, a minimum markup that {SCR} can always see, and {ART}.""")
put("N__tick", "theta", f"""It appears that {TH} falls as the {NMM} grows and as the {TICK} grows, with the price step cutting intensity by a similar proportion at every number of market makers, slightly less when there are many. The fall with tick size most likely reflects having to move prices in whole steps, {SCR} always seeing at least a full step of markup, and {ART}. The slightly smaller cut with many market makers is consistent with the price step making cheating less tempting there.""")

put("N__slope", "share", f"""It appears that collusion falls both as the {NMM} grows and as the {SLOPE} rises, and these effects roughly multiply because they act through different channels: more firms make cheating more tempting, while the screen raises the risk of an investigation. The smallest numbers of market makers look almost identical, most likely because small cartels hold together easily. The penalty for having many market makers grows under steeper screens, apparently because the risk of investigation makes the future less certain, which weakens what keeps large cartels together.""")
put("N__slope", "theta", f"""It appears that {TH} falls steeply as the {SLOPE} rises at every {NMM}, and is lower with more firms. With no screen, colluding firms most likely push straight to the full-collusion price. Under steep screens, cartels with many market makers cut intensity much more, apparently because high prices raise the risk of investigation, which in turn makes cheating more tempting, so large cartels must keep prices down to stay together.""")

put("N__rhoTip", "share", f"""It appears that collusion falls as the {TIP} rises and as the {NMM} grows. Tips seem to hit markets with many market makers proportionally harder, most likely because a tip shortens the cartel's expected life and so weakens the hold of future profits, which matters most where the temptation to cheat is already high. In small cartels, which hold together easily, tips mainly work through expected fines and a shorter life.""")
put("N__rhoTip", "theta", f"""It appears that {TH} falls as the {TIP} and the {NMM} rise, and that the proportional fall from tips is larger when there are many market makers. This seems mainly to be because fewer cartels form, especially large ones; among cartels that do form, tips tend to push prices higher, since hiding helps less when a whistleblower may strike anyway.""")

put("N__pEvidence", "share", f"""It appears that collusion falls as the {NMM} grows and as {EV} rises, and these act almost independently. This is most likely because a higher chance of a guilty finding raises the expected fine but does not change the temptation to cheat, which is how the number of market makers acts. The smallest numbers of market makers look almost identical, and the curve flattens as a guilty finding becomes certain, which appears to be {ART}.""")
put("N__pEvidence", "theta", f"""It appears that {TH} falls as {EV} rises at every {NMM}, and is lower with more firms. The proportional fall is smaller when there are many market makers, most likely because fewer large cartels collude at all, leaving less for deterrence to remove. The near-flat stretch at the highest chances of a guilty finding in markets with many market makers appears to be {ART} offsetting the extra deterrence.""")

put("N__fineRatio", "share", f"""It appears that collusion falls steeply as the {FINE} rises and also falls as the {NMM} grows, with these acting nearly independently. This seems to be because the fine is measured against each firm's own full-collusion profit, so adding firms does not make a given fine ratio heavier per firm. The number of market makers therefore acts mainly through the temptation to cheat, while the fine ratio acts on whether colluding is worth the risk at all.""")
put("N__fineRatio", "theta", f"""It appears that {TH} falls as the {FINE} rises at every {NMM} and is lower with more firms, but the gap between small and large cartels narrows sharply under high fine ratios. This is most likely because heavy fines push surviving cartels to low prices, where the risk of investigation and the strain on the cartel are small, or leave only scenarios where no investigation can ever start, so the number of market makers has less to act on.""")

put("N__sBarRatio", "share", f"""It appears that collusion peaks at middle values of the {ROOM} for every {NMM}, and falls as firms are added. The middle peak seems to blend opposing forces: in markets with no minimum price step, more room makes collusion more visible to {SCR}, while in markets with a minimum price step a narrow room leaves little space above normal competition. More market makers appear to scale the whole curve down by a similar proportion, as expected when the number of market makers acts only through the temptation to cheat.""")
put("N__sBarRatio", "theta", f"""It appears that {TH} peaks at a fairly low, but not the lowest, {ROOM} for every {NMM}, and falls as firms are added. Beyond that peak, intensity most likely falls because the same degree of collusion is a wider spread that {SCR} notices more. The narrowest room is pulled down by markets with a minimum price step, where a large step leaves no price at all to collude on.""")

# ---------------- phi pairs ----------------
put("phi__tick", "share", f"""It appears that collusion rises with the {PHI} and falls with the {TICK}. The preferenced volume share helps at every tick size but less when there is a price step, most likely because the step already eases the temptation to cheat, leaving less for the preferenced volume share to do. In very small markets with a price step, a higher preferenced volume share also raises ordinary competitive earnings, which seems to shrink the space for a cartel and can even lower collusion.""")
put("phi__tick", "theta", f"""It appears that {TH} rises with the {PHI} and falls with the {TICK}, with these effects adding up almost independently. In markets with no price step, the preferenced volume share does not change prices, {SCR} or the fine, so its effect most likely comes entirely from easing the temptation to cheat, letting more cartels form and fewer hold prices down to stay together. The price step appears to lower intensity by forcing whole steps that the screen can see.""")

put("phi__slope", "share", f"""It appears that collusion falls sharply as the {SLOPE} rises, and rises with the {PHI}, which lifts the whole curve by a broadly similar proportion. This seems to be because they do different jobs: the preferenced volume share decides whether a cartel can be held together, while the screen decides whether colluding is worth the risk of investigation. Moving up the chart therefore shows easier cartel discipline, and moving across shows enforcement.""")
put("phi__slope", "theta", f"""It appears that {TH} falls steeply as the {SLOPE} rises, and rises with the {PHI} at every screen slope. The proportional boost from the preferenced volume share seems larger under steep screens, most likely because a steep screen makes high prices risky, which in turn makes cheating more tempting, and evenly split volume relieves exactly that temptation.""")

put("phi__rhoTip", "share", f"""It appears that collusion falls sharply as the {TIP} rises and rises with the {PHI}, by a similar amount at every tip probability. Tips seem to work by shortening the cartel's expected life, which also makes cheating more tempting, and the preferenced volume share acts as a counterweight by making undercutting less rewarding. Their effects therefore look nearly additive.""")
put("phi__rhoTip", "theta", f"""It appears that {TH} falls as the {TIP} rises at every {PHI}, and that the preferenced volume share adds a similar amount at every tip probability. The fall with tips most likely comes from fewer cartels forming, even though the cartels that do form tend to price higher when a whistleblower might expose them anyway.""")

put("phi__pEvidence", "share", f"""It appears that collusion falls as {EV} rises and rises with the {PHI}, with these acting almost independently. A higher chance of a guilty finding raises the expected fine, while the preferenced volume share makes the cartel easier to hold together, so they most likely work on different decisions. The preferenced volume share helps a bit less where a guilty finding is likely, and the flattening between the highest chances of a guilty finding appears to be {ART}.""")
put("phi__pEvidence", "theta", f"""It appears that {TH} falls as {EV} rises, and rises with the {PHI} at every chance of a guilty finding. The boost from the preferenced volume share looks larger where a guilty finding is unlikely, most likely because more cartels form there, so the easing of the temptation to cheat applies to more of them.""")

put("phi__fineRatio", "share", f"""It appears that collusion falls steeply as the {FINE} rises and rises with the {PHI}, by a broadly similar proportion at every fine ratio. The fine seems to decide whether colluding is worth the risk, while the preferenced volume share decides whether the cartel can be held together. With no fine, the chart mostly shows whether firms can keep the cartel from breaking apart, which is where the preferenced volume share matters most visibly.""")
put("phi__fineRatio", "theta", f"""It appears that {TH} falls as the {FINE} rises at every {PHI}, and that the advantage from the preferenced volume share shrinks to almost nothing under high fine ratios. This is most likely because heavy fines leave few cartels, mostly in scenarios where {SCR} is switched off and {TIPS} never happen, where the preferenced volume share has little left to change.""")

put("phi__sBarRatio", "share", f"""It appears that collusion peaks at middle values of the {ROOM}, and that the {PHI} raises it by a similar amount at every level of room. This fits the preferenced volume share acting only on the temptation to cheat, while the room acts on how visible collusion is to {SCR} and, in markets with a minimum price step, on how many price levels fit above normal competition. In markets with no minimum price step, collusion most likely falls steadily with room; the rise from the narrowest room comes from markets with a price step needing space above normal competitive prices.""")
put("phi__sBarRatio", "theta", f"""It appears that {TH} peaks at a fairly low, but not the lowest, {ROOM} for every {PHI}, and that the preferenced volume share adds a similar amount throughout. The decline at wider room seems to be because the same degree of collusion becomes a wider spread that {SCR} notices, while the low value at the narrowest room most likely reflects markets with a minimum price step that leave little or no space to raise prices.""")

# ---------------- tick pairs ----------------
put("tick__slope", "share", f"""It appears that collusion falls with both the {TICK} and the {SLOPE}, and that they reinforce each other. With no screen a small price step makes little difference, but as the screen steepens the markets with a price step fall much faster. Without a price step, a cartel can most likely choose a tiny markup that the screen barely notices; with a step, the smallest markup is a full step that the screen always sees. This gap survives when every investigation is made to end in a conviction, so it appears to be mainly genuine, with {ART} adding to it.""")
put("tick__slope", "theta", f"""It appears that {TH} falls with both the {TICK} and the {SLOPE}. For a small price step, most of the shortfall compared with no step seems to be {ART}, because it vanishes when every investigation ends in a conviction. For a large price step, intensity stays lower even then, most likely because whole steps stop the cartel from choosing a modest price that would escape the screen.""")

put("tick__rhoTip", "share", f"""It appears that collusion falls as the {TIP} rises and as the {TICK} grows, and that tips hurt proportionally more in markets with a price step. In markets with no price step, a tip costs expected fines and a shorter cartel life. In markets with a price step there is an extra cost from {ART_S}, since a tip-started investigation that finds nothing most likely also wipes out ordinary competitive earnings; when every investigation ends in a conviction, tips hurt about equally with or without a price step.""")
put("tick__rhoTip", "theta", f"""It appears that {TH} falls with both the {TIP} and the {TICK}. Markets with no price step are least affected by tips, most likely because there the cartels that still form respond to tips by pricing higher, since hiding helps little when a whistleblower may expose them anyway, which partly offsets the cartels lost.""")

put("tick__pEvidence", "share", f"""It appears that collusion falls with the {TICK} and, on average, as {EV} rises. In markets with no price step, a higher chance of a guilty finding acts as pure deterrence, because it raises the expected fine, so collusion falls steadily. In markets with a price step the curve flattens and even turns up when a guilty finding is certain, which appears to be {ART_S}: an investigation that finds nothing ends ordinary earnings for good, while a conviction only costs the fine, so a higher chance of a guilty finding looks less bad.""")
put("tick__pEvidence", "theta", f"""It appears that {TH} falls as the {TICK} grows and as {EV} rises. In markets with no price step, intensity falls steadily as a guilty finding becomes more likely, most likely because only the expected fine, the chance of conviction combined with the fine, matters. With a large price step it bottoms out and rises slightly when a guilty finding is certain, which seems to be {ART}.""")

put("tick__fineRatio", "share", f"""It appears that collusion falls steeply as the {FINE} rises and as the {TICK} grows, and that fines bite much harder in markets with a price step. With no fine, a small price step makes little difference. In markets with no price step, a cartel can most likely pick a markup so small that the expected fine stays below its extra profit; with a price step, the smallest markup is a full step, so the fine cannot be watered down that way.""")
put("tick__fineRatio", "theta", f"""It appears that {TH} falls as the {FINE} rises at every {TICK}, and falls faster in markets with a price step at low and middle fine ratios. Under very high fine ratios the tick sizes converge, most likely because the cartels that remain are mostly in scenarios where no investigation can ever start, which never face a fine and so are unaffected by the limits a price step imposes.""")

put("tick__sBarRatio", "share", f"""It appears that collusion falls with the {TICK} and peaks at middle values of the {ROOM}. In markets with no price step, collusion falls as the room widens, most likely because the same degree of collusion becomes a wider spread that {SCR} notices. With a large price step and the narrowest room, collusion is impossible, because normal competition with that step already reaches the spread at which customers stop trading. As the room widens the price step becomes small relative to it and the tick sizes converge.""")
put("tick__sBarRatio", "theta", f"""It appears that {TH} falls with the {TICK} and peaks at a fairly low, but not the lowest, {ROOM}. In markets with no price step, intensity falls steadily as the room widens, apparently because {SCR} sees the wider spread. With a large price step and the narrowest room there is no collusion at all, and with a smaller step the only option there is a jump straight to the full-collusion price.""")

# ---------------- slope pairs ----------------
put("slope__rhoTip", "share", f"""It appears that collusion falls as the {SLOPE} and the {TIP} rise, but these act as substitutes. Tips do most damage where there is no screen and little where a steep screen already dominates, most likely because either is enough to start an investigation that ends the cartel. With no screen and no tips nothing can start an investigation, so the chart there shows simply where the cartel can be held together.""")
put("slope__rhoTip", "theta", f"""It appears that average {TH} falls with both the {SLOPE} and the {TIP}. Where there is a screen, tips seem to push the cartels that still form towards higher prices, because hiding from the screen helps little when a whistleblower may expose them anyway; the average still falls because fewer cartels form. With no screen, colluding firms most likely go straight to the full-collusion price, so tips lower intensity only by reducing how many cartels form.""")

put("slope__pEvidence", "share", f"""It appears that collusion falls as the {SLOPE} and {EV} rise, and that these reinforce each other: a higher chance of a guilty finding matters much more under a steeper screen. This is most likely because the screen creates investigations while the chance of a guilty finding decides how costly each investigation is. The small upturn when a guilty finding is certain under steep screens appears to be {ART}; in markets with no price step, collusion falls steadily.""")
put("slope__pEvidence", "theta", f"""It appears that {TH} falls with the {SLOPE} and with {EV}, at every level of each. A higher chance of a guilty finding most likely raises the expected fine attached to each extra bit of price. The slight upturns when a guilty finding is certain under steep screens appear to be {ART} rather than a real effect.""")

put("slope__fineRatio", "share", f"""It appears that collusion falls as the {SLOPE} and the {FINE} rise, and this is the strongest interaction in the model. What seems to matter is the screen and the fine together: a gentle screen with a heavy fine deters about as much as a steep screen with a moderate fine. With no screen the fine works only through {TIPS}, so many cartels survive even heavy fines, but a steep screen combined with a heavy fine makes collusion all but disappear.""")
put("slope__fineRatio", "theta", f"""It appears that {TH} falls with both the {SLOPE} and the {FINE}. Without a screen, even a very high fine ratio leaves noticeable intensity, most likely because the surviving cartels there face no risk of investigation and push prices to the full-collusion level. Even with no fine, a screen alone lowers intensity, apparently because an investigation ends the cartel's future profits, so cartels trade some margin for a longer life.""")

put("slope__sBarRatio", "share", f"""It appears that collusion falls as the {SLOPE} rises and, on average, peaks at middle values of the {ROOM}. These inputs interact: with no screen, collusion rises with room, most likely only because markets with a minimum price step need space above normal competitive prices, but with a screen, a wider room hurts because the same degree of collusion becomes a wider spread the screen notices. In effect, a wide room seems to act like a steeper screen.""")
put("slope__sBarRatio", "theta", f"""It appears that {TH} falls with the {SLOPE} and, on average, peaks at a fairly low, but not the lowest, {ROOM}. With no screen, intensity rises as the room widens, apparently only from the extra price levels a wider room offers in markets with a minimum price step. Under a steep screen it falls as the room widens, most likely because a wider room makes the same degree of collusion more visible, so a screen in a wide market behaves like a steeper screen in a narrow market.""")

# ---------------- rhoTip pairs ----------------
put("rhoTip__pEvidence", "share", f"""It appears that collusion falls as the {TIP} and {EV} rise, and that these compound: a higher chance of a guilty finding deters more when tips are common. This is most likely because a tip can start an investigation at any price, so the risk of conviction applies whatever the cartel does, not only at high prices. The fall at the highest chances of a guilty finding is weaker than it would otherwise be, which appears to be {ART}.""")
put("rhoTip__pEvidence", "theta", f"""It appears that {TH} falls with both the {TIP} and {EV}. A higher chance of a guilty finding most likely lowers intensity directly, since it raises the expected fine attached to each extra bit of price. Tips seem to lower intensity on average only because fewer cartels form, even though the cartels that remain tend to price higher.""")

put("rhoTip__fineRatio", "share", f"""It appears that collusion falls with both the {TIP} and the {FINE}, and that together they can end collusion entirely. A tip creates a minimum expected fine that no pricing choice can avoid, so once tips are common and fines are heavy, the expected fine most likely exceeds even the best profit a cartel could earn. Without tips, some collusion survives heavy fines, apparently in scenarios where {SCR} is switched off, so nothing ever starts an investigation.""")
put("rhoTip__fineRatio", "theta", f"""It appears that {TH} falls with the {FINE} and with the {TIP}, disappearing entirely when tips are common and fines are heavy. With no fine, tips barely change intensity, most likely because a tip then only shortens the cartel's life: some cartels no longer form, but those that remain price higher, and these roughly cancel.""")

put("rhoTip__sBarRatio", "share", f"""It appears that a higher {TIP} lowers collusion at every {ROOM}, proportionally more when the room is narrow, and that collusion peaks at middle values of room. Tips most likely matter more when the room is narrow because {SCR} sees only a small spread there, so a tip becomes the main way an investigation starts. The middle peak seems to blend a falling pattern in markets with no minimum price step, where a wider room is more visible to the screen, with markets that have a price step needing space above normal prices.""")
put("rhoTip__sBarRatio", "theta", f"""It appears that {TH} peaks at a fairly low, but not the lowest, {ROOM} at every {TIP}, and that tips lower it throughout. Beyond the peak, a wider room most likely makes collusion more visible to {SCR}, while tips seem to lower the average mainly by reducing how many cartels form.""")

# ---------------- pEvidence pairs ----------------
put("pEvidence__fineRatio", "share", f"""It appears that collusion falls with both {EV} and the {FINE}, because together they set the expected cost of each investigation; in markets with no minimum price step, a low chance of a guilty finding with a heavy fine deters about as much as a certain guilty finding with a lighter fine. With no fine, however, collusion rises with the chance of a guilty finding even though nothing is ever fined, which appears to be {ART}. Under heavy fines a small remnant of collusion remains, most likely in scenarios where no investigation can ever start.""")
put("pEvidence__fineRatio", "theta", f"""It appears that {TH} falls with the {FINE} and, on average, with {EV}, which together set the expected cost of an investigation. Once the fine ratio is meaningful, a higher chance of a guilty finding lowers intensity sharply. With no fine, intensity instead rises with that chance, which seems to be {ART} rather than real behaviour.""")

put("pEvidence__sBarRatio", "share", f"""It appears that collusion falls as {EV} rises at every {ROOM}, and peaks at middle values of room; the peak shifts slightly towards narrower room when a guilty finding is certain. In markets with no minimum price step collusion most likely falls steadily as the room widens, because a wider room means a spread more visible to {SCR} and a heavier fine relative to the profit from a small markup. The rise from the narrowest room appears to come from markets with a price step needing space above normal prices.""")
put("pEvidence__sBarRatio", "theta", f"""It appears that {TH} peaks at a fairly low, but not the lowest, {ROOM} at every level of {EV}, and falls as that chance rises. In markets with no minimum price step, intensity seems to fall steadily in both directions: a higher chance of a guilty finding raises the expected fine, and a wider room makes the same collusion more visible to {SCR}.""")

# ---------------- fineRatio pairs ----------------
put("fineRatio__sBarRatio", "share", f"""It appears that collusion falls steeply as the {FINE} rises and, on average, peaks at middle values of the {ROOM}. With no fine, collusion rises with room, most likely only because markets with a minimum price step need space above normal prices. With a fine, a wider room becomes less attractive, apparently because the fine is measured against full-collusion profit, which grows with the room faster than the profit from a small, inconspicuous markup. Under the highest fine ratios collusion is low at every level of room.""")
put("fineRatio__sBarRatio", "theta", f"""It appears that {TH} falls as the {FINE} rises and peaks at a fairly low, but not the lowest, {ROOM} at every fine ratio. In markets with no minimum price step, intensity seems to fall steadily as the room widens even with no fine, most likely because {SCR} judges the absolute spread, so the same degree of collusion looks more suspicious in a wide market. Under high fine ratios the different values of room converge on low intensity.""")

# ---------------- checks ----------------
a = json.load(open(D + r"\analysis.json", encoding="utf8"))
t = json.load(open(D + r"\tables.json", encoding="utf8"))
assert set(a) == set(T), (set(a) ^ set(T))
errs = []
numwords = re.compile(r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|twenty|hundred|thousand|half|halves|double|doubles|triple|quarter|third|single|percent|dozen|first|second)\b", re.I)
TERM = {"delta": "patience", "N": "number of market makers", "phi": "preferenced volume share",
        "tick": "tick size", "slope": "regulator screen slope", "rhoTip": "tip probability",
        "pEvidence": "p(evidence | investigation)", "fineRatio": "fine ratio", "sBarRatio": "reservation spread ratio"}
# shorthand pattern -> strings, any of which must start at or before the shorthand's first use
SHORT = [
    (r"\broom\b", ["reservation spread ratio"]),
    (r"\bgrids?\b", ["tick size", "minimum price step"]),
    (r"\bsteps?\b", ["tick size", "minimum price step"]),
    (r"\bscreens?\b", ["regulator screen slope", "regulator's screen ("]),
    (r"\btips?\b", ["tip probability", "tips ("]),
    (r"\bevidence\b", ["p(evidence | investigation)"]),
    (r"preferenc\w*|protected volume", ["preferenced volume share"]),
    (r"\bcrowded\b", ["number of market makers"]),
    (r"number of firms|firm counts?", ["number of market makers"]),
    (r"\bquirk\b|\bartifact\b", []),
    (r"\bsimplification\b", ["modelling simplification in markets with a minimum price step (an investigation that finds nothing",
                              "modelling simplification for such markets (an investigation that finds nothing"]),
    (r"\bintensity\b", ["collusion intensity (how far"]),
]
FINE_SHORT = (r"\bfines?\b", ["fine ratio"])
for k in a:
    for m in ("share", "theta"):
        s = T[k][m]
        low = s.lower()
        if re.search(r"\d", s):
            errs.append(f"DIGIT {k} {m}")
        if numwords.search(s):
            errs.append(f"NUMWORD {k} {m}: {numwords.search(s).group(0)}")
        n = len(re.findall(r"[.!?](\s|$)", s))
        if not (2 <= n <= 5):
            errs.append(f"SENTENCES {k} {m}: {n}")
        for bad in ("IC ", "constraint", "corner", "π", "θ", "Nash", "regime", "participation", "pi_post"):
            if bad in s:
                errs.append(f"JARGON {k} {m}: {bad}")
        if not re.search(r"\b(appears?|most likely|seems?|apparently|suggesting)\b", s):
            errs.append(f"CAUTION {k} {m}")
        for var in k.split("__"):
            if TERM[var] not in low:
                errs.append(f"TERMNAME {k} {m}: {TERM[var]}")
        rules = SHORT + ([FINE_SHORT] if "fineRatio" in k else [])
        for pat, defs in rules:
            mt = re.search(pat, low)
            if not mt:
                continue
            pos = [low.find(d) for d in defs if low.find(d) >= 0]
            if not pos or min(pos) > mt.start():
                errs.append(f"SHORTHAND {k} {m}: '{mt.group(0)}' undefined")
        e = t[m + "__" + k]
        v = e["values"]
        rm = [sum(r) / len(r) for r in v]
        cm = [sum(v[i][j] for i in range(len(v))) / len(v) for j in range(len(v[0]))]
        for var, means in ((e["rows_var"], rm), (e["cols_var"], cm)):
            cl = C[k][m][var]
            d = [b - a_ for a_, b in zip(means, means[1:])]
            if cl == "dec":
                ok = means[-1] < means[0] and all(x <= 0.005 for x in d)
            elif cl == "inc":
                ok = means[-1] > means[0] and all(x >= -0.005 for x in d)
            else:
                i = max(range(len(means)), key=lambda j: means[j])
                ok = 0 < i < len(means) - 1
            if not ok:
                errs.append(f"DIRECTION {k} {m} {var} claimed {cl}: {[round(x,3) for x in means]}")

# Same shorthand check applied to v1, for the notes
v1_flags = 0
for k in T_OLD:
    for m in T_OLD[k]:
        low = T_OLD[k][m].lower()
        for pat, defs in SHORT + ([FINE_SHORT] if "fineRatio" in k else []):
            if pat == r"\bintensity\b":
                continue
            mt = re.search(pat, low)
            if mt:
                pos = [low.find(d) for d in defs if low.find(d) >= 0]
                if not pos or min(pos) > mt.start():
                    v1_flags += 1
changed = sum(1 for k in T for m in T[k] if T[k][m] != T_OLD[k][m])
print("texts:", sum(len(x) for x in T.values()), "changed:", changed, "v1 shorthand flags:", v1_flags)
print("errors:", len(errs))
for x in errs:
    print(x)
if errs:
    raise SystemExit(1)
if not os.path.exists(D + r"\interp_v1.json"):
    shutil.copyfile(D + r"\interp.json", D + r"\interp_v1.json")
json.dump(T, open(D + r"\interp.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
print("wrote interp.json (v1 saved as interp_v1.json)")
