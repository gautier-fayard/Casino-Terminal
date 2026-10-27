"""Machine à sous : moteur, affichage, bonus, auto-spin, objectifs.
Fichier à garder à côté de pp.py, pp_plus.py et pp_poker.py.
"""
import random
import sys
import time

NEEDED = ['fmt', 'debloquer', 'compter', 'Quitter', 'demander_mise', 'ajouter_objectifs', 'JEUX_EXTRA',
          'NOMS_JEUX', 'CUMULS', 'NOMS_CUMULS', 'PAUSE', 'OBJECTIFS', 'LIBELLES', 'lire_montant']
pp_plus = None  # renseigné par installer


# ------------------------------------------------------------------ symboles et gains
# Lisibles : 777, BAR (barre), DIA (diamant), CLO (cloche), CER (cerise), CIT (citron),
# PRU (prune), WLD (wild, remplace les autres), BNS (bonus, déclenche les tours gratuits).
SYMBOLES = {'777': 1, 'BAR': 2, 'DIA': 3, 'CLO': 5, 'CER': 7, 'CIT': 9, 'PRU': 10, 'WLD': 3, 'BNS': 1}
NOMS_SYMBOLES = {'777': 'sept', 'BAR': 'barre', 'DIA': 'diamant', 'CLO': 'cloche', 'CER': 'cerise',
                 'CIT': 'citron', 'PRU': 'prune', 'WLD': 'wild', 'BNS': 'bonus'}
POOL = [s for s, n in SYMBOLES.items() for _ in range(n)]
# Dans les tours gratuits les WLD sont plus rares (ils restent collés et s'étendent)
POIDS_WLD_BONUS = 1
POOL_BONUS = [s for s, n in SYMBOLES.items() for _ in range(POIDS_WLD_BONUS if s == 'WLD' else n)]

# Gains par ligne en multiple de (mise / 5), pour 3 / 4 / 5 symboles alignés depuis la gauche
GAINS = {
    '777': {3: 16.5, 4: 100, 5: 660}, 'BAR': {3: 10, 4: 38.5, 5: 192}, 'DIA': {3: 6.6, 4: 26.4, 5: 132},
    'CLO': {3: 3.9, 4: 16.5, 5: 66}, 'CER': {3: 2.8, 4: 10, 5: 38.5}, 'CIT': {3: 1.7, 4: 5.5, 5: 22},
    'PRU': {3: 1.7, 4: 5.5, 5: 19.8},
}
GAINS_BONUS_SYMBOLE = {3: 2, 4: 10, 5: 50}  # x la mise totale, 3 / 4 / 5 BNS
LIGNES = [(0, 0, 0, 0, 0), (1, 1, 1, 1, 1), (2, 2, 2, 2, 2), (0, 1, 2, 1, 0), (2, 1, 0, 1, 2)]
NOMS_LIGNES = ['haut', 'milieu', 'bas', 'V', 'V inversé']

# Cascades : après un gain, les symboles gagnants disparaissent et on rejoue avec un multiplicateur
ECHELLE_CASCADE = [1, 2, 3, 5]

# Tours gratuits
TOURS_GRATUITS = 8
TOURS_MAX = 40
RELANCE_TOURS = {3: 5, 4: 8, 5: 12}
MULT_BASE_BONUS = 1.5         # multiplicateur des tours gratuits si le coffre multiplicateur n'est pas ouvert
EXPANSION_ROULEAUX = (1, 2, 3)  # un WLD qui tombe sur ces rouleaux remplit tout le rouleau (bonus)
COFFRES_PAR_BNS = {3: 2, 4: 3, 5: 4}
MULT_COFFRE = [(2, 30), (3, 25), (4, 20), (5, 12), (8, 8), (10, 5)]
GAINS_FIXES_COFFRE = [(1, 30), (2, 30), (3, 20), (5, 12), (8, 8)]  # x la mise
PRIX_BONUS = 33
PLAFOND_BONUS = 2000  # gain maximal d'un bonus, en multiple de la mise


# ------------------------------------------------------------------ moteur (sans affichage)

def tourner():
    return [[random.choice(POOL) for _ in range(3)] for _ in range(5)]


def detail_ligne(cases):
    """(multiplicateur, nombre de cases gagnantes depuis la gauche)."""
    premier = next((s for s in cases if s != 'WLD'), None)
    meilleur = (0, 0)
    prefixe = 0
    for s in cases:
        if s != 'WLD':
            break
        prefixe += 1
    if prefixe >= 3:
        meilleur = (GAINS['777'].get(prefixe, 0), prefixe)
    if premier in GAINS:
        run = 0
        for s in cases:
            if s == premier or s == 'WLD':
                run += 1
            else:
                break
        if run >= 3 and GAINS[premier][run] > meilleur[0]:
            meilleur = (GAINS[premier][run], run)
    return meilleur


def evaluer(grille):
    """([(ligne, mult, nb, cases)], nombre de BNS)."""
    gains = []
    for i, ligne in enumerate(LIGNES):
        cases = [grille[r][ligne[r]] for r in range(5)]
        m, nb = detail_ligne(cases)
        if m:
            gains.append((i, m, nb, cases))
    bns = sum(1 for r in range(5) for c in grille[r] if c == 'BNS')
    return gains, bns


def valeur_lignes(gains, mise, mult=1.0):
    return sum(mise / len(LIGNES) * m for _, m, _, _ in gains) * mult


def cascade(grille, gains):
    """Retire les cases gagnantes, fait tomber les autres et remplit par le haut."""
    gagnantes = set()
    for i, _, nb, _ in gains:
        for r in range(nb):
            gagnantes.add((r, LIGNES[i][r]))
    nouvelle = []
    for r in range(5):
        reste = [grille[r][row] for row in range(3) if (r, row) not in gagnantes]
        manque = 3 - len(reste)
        nouvelle.append([random.choice(POOL) for _ in range(manque)] + reste)
    return nouvelle


def tour_base(mise):
    """Un tour normal avec cascades. Retourne un dict décrivant toutes les étapes."""
    grille = tourner()
    etapes = []
    total = 0.0
    declenche = 0   # nombre de BNS au moment du déclenchement (0 = pas de bonus)
    prime_bns = 0.0
    n = 0
    while True:
        gains, bns = evaluer(grille)
        mult = ECHELLE_CASCADE[min(n, len(ECHELLE_CASCADE) - 1)]
        valeur = valeur_lignes(gains, mise, mult)
        etape = {'grille': grille, 'gains': gains, 'mult': mult, 'valeur': valeur, 'bns': bns}
        if bns >= 3 and not declenche:
            declenche = min(bns, 5)
            prime_bns = mise * GAINS_BONUS_SYMBOLE[declenche]
            etape['prime_bns'] = prime_bns
        etapes.append(etape)
        total += valeur
        if not gains:
            break
        grille = cascade(grille, gains)
        n += 1
    total += prime_bns
    return {'etapes': etapes, 'total': total, 'declenche': declenche, 'cascades': len(etapes) - 1,
            'bns_initial': etapes[0]['bns']}


def tirer_pondere(liste):
    total = sum(p for _, p in liste)
    x = random.uniform(0, total)
    for v, p in liste:
        x -= p
        if x <= 0:
            return v
    return liste[-1][0]


def preparer_coffres():
    """5 coffres : un multiplicateur, trois gains fixes, un vide (ordre mélangé)."""
    contenu = [('mult', tirer_pondere(MULT_COFFRE))]
    contenu += [('fixe', tirer_pondere(GAINS_FIXES_COFFRE)) for _ in range(3)]
    contenu.append(('vide', 0))
    random.shuffle(contenu)
    return contenu


def tours_bonus(mise, mult, depart=TOURS_GRATUITS):
    """Générateur : un dict par tour gratuit. WLD collants (restent jusqu'à la fin) et étendus."""
    collants = set()
    restants = depart
    prevu = depart
    k = 0
    relances = 0
    cumul = 0.0
    plafond = False
    while restants > 0:
        restants -= 1
        k += 1
        g = [[random.choice(POOL_BONUS) for _ in range(3)] for _ in range(5)]
        nouveaux = []
        for r in range(5):
            for row in range(3):
                if g[r][row] == 'WLD' and (r, row) not in collants:
                    nouveaux.append((r, row))
        etendus = sorted({r for r, _ in nouveaux if r in EXPANSION_ROULEAUX})
        for r in etendus:
            g[r] = ['WLD'] * 3
        for r, row in collants:
            g[r][row] = 'WLD'
        collants |= set(nouveaux)
        gains, bns = evaluer(g)
        valeur = valeur_lignes(gains, mise, mult)
        if cumul + valeur >= PLAFOND_BONUS * mise:
            valeur = PLAFOND_BONUS * mise - cumul
            plafond = True
        cumul += valeur
        plus = 0
        if plafond:
            restants = 0
        elif bns >= 3 and prevu < TOURS_MAX:
            plus = min(RELANCE_TOURS[min(bns, 5)], TOURS_MAX - prevu)
            restants += plus
            prevu += plus
            relances += 1
        yield {'k': k, 'prevu': prevu, 'grille': g, 'gains': gains, 'valeur': valeur, 'plus': plus,
               'bns': bns, 'collants': set(collants), 'etendus': etendus, 'nouveaux': nouveaux,
               'relances': relances, 'plafond': plafond, 'cumul': cumul}


def jouer_coffres_auto(mise, nb):
    """Choix aléatoire (simulation). Retourne (multiplicateur, gains fixes)."""
    coffres = preparer_coffres()
    choix = random.sample(range(5), nb)
    mult = MULT_BASE_BONUS
    fixes = 0.0
    for i in choix:
        t, v = coffres[i]
        if t == 'mult':
            mult = v
        elif t == 'fixe':
            fixes += v * mise
    return mult, fixes


def simuler_bonus(mise, bns=3, achat=False):
    mult, fixes = jouer_coffres_auto(mise, COFFRES_PAR_BNS[bns])
    total = fixes
    for t in tours_bonus(mise, mult):
        total += t['valeur']
    return total


# ------------------------------------------------------------------ affichage

_ANSI = None


def ansi_ok(force=None):
    """Vrai si le terminal sait remonter le curseur (animation sur 3 rangées)."""
    global _ANSI
    if force is not None:
        _ANSI = force
    if _ANSI is None:
        _ANSI = False
        try:
            if sys.stdout.isatty():
                if sys.platform == 'win32':
                    import ctypes
                    k = ctypes.windll.kernel32
                    h = k.GetStdHandle(-11)
                    mode = ctypes.c_uint32()
                    if k.GetConsoleMode(h, ctypes.byref(mode)):
                        _ANSI = bool(k.SetConsoleMode(h, mode.value | 0x0004))
                else:
                    _ANSI = True
        except Exception:
            _ANSI = False
    return _ANSI


def cases_gagnantes(gains):
    return {(r, LIGNES[i][r]) for i, _, nb, _ in gains for r in range(nb)}


def afficher_grille(grille, gagnantes=(), prefixe="   "):
    """Les symboles gagnants sont écrits en minuscules."""
    for row in range(3):
        cases = []
        for r in range(5):
            s = grille[r][row]
            cases.append(s.lower() if (r, row) in gagnantes else s)
        print(prefixe + " | ".join(cases))


def _bloc(vue):
    return ["   " + " | ".join(vue[r][row] for r in range(5)) for row in range(3)]


def _dessiner(vue, premiere):
    if not premiere:
        sys.stdout.write("\033[3A")
    for ligne in _bloc(vue):
        sys.stdout.write(ligne + "\033[K\n")
    sys.stdout.flush()


def _effacer_bloc():
    sys.stdout.write("\033[3A\033[J")
    sys.stdout.flush()


RALENTI = [0.05, 0.06, 0.08, 0.10, 0.14, 0.20, 0.28, 0.40, 0.55]


def animer(grille, passable=True):
    """Rouleaux qui s'arrêtent un par un. Avec 2 BNS déjà sortis, les rouleaux restants ralentissent.
    Entrée pendant l'animation affiche le résultat tout de suite (sauf si ce n'est pas passable).
    Retourne True si l'animation a été sautée."""
    if passable:
        attente = pp_plus.dormir_ou_passer
    else:
        pp_plus.vider_clavier()

        def attente(t):
            pp_plus.dormir(t)
            return False
    ansi = ansi_ok()
    arret = []
    saute = False
    premiere = True
    for stade in range(5):
        bns_visibles = sum(1 for r in arret for c in r if c == 'BNS')
        restants = 5 - stade
        ralenti = bns_visibles >= 2
        delais = [0.07] * 4
        if ralenti:
            delais = RALENTI if restants == 1 else [d * 0.6 for d in RALENTI[3:]]
        for d in delais:
            vue = arret + [[random.choice(POOL) for _ in range(3)] for _ in range(restants)]
            if ansi:
                _dessiner(vue, premiere)
                premiere = False
            else:
                print("\r   " + " | ".join(v[1] for v in vue) + "   ", end="", flush=True)
            if attente(d):
                saute = True
                break
        if saute:
            break
        arret.append(grille[stade])
        vue = arret + [[' . ' for _ in range(3)] for _ in range(restants - 1)]
        if ansi:
            _dessiner(vue, premiere)
            premiere = False
        else:
            print("\r   " + " | ".join([v[1] for v in arret] + ["   "] * (restants - 1)) + "   ", end="", flush=True)
        pause = 0.7 if (ralenti and restants == 1) else PAUSE * 0.4
        if attente(pause):
            saute = True
            break
    if ansi and not premiere:
        _effacer_bloc()
    elif not ansi:
        print("\r" + " " * 40 + "\r", end="")
    if not passable:
        pp_plus.vider_clavier()
    return saute


_rapide = False


def pause_s(t):
    """Pause des tours normaux : Entrée la saute, et saute aussi les pauses suivantes du tour."""
    global _rapide
    if _rapide:
        return
    if pp_plus.dormir_ou_passer(t):
        _rapide = True


def pause_b(t):
    """Pause des bonus : jamais sautée."""
    pp_plus.dormir(t)


def fmt_x(m):
    return fmt(round(m / len(LIGNES), 2))


def lignes_aide():
    out = [" Machine à sous : 5 rouleaux x 3 rangées, 5 lignes (haut, milieu, bas, V, V inversé).",
           " Symboles : 777 (sept), BAR (barre), DIA (diamant), CLO (cloche), CER (cerise), CIT (citron),",
           "            PRU (prune), WLD (wild : remplace les autres), BNS (bonus : tours gratuits).",
           " Gains en x la mise totale pour 3 / 4 / 5 symboles alignés depuis la gauche :"]
    for sym, t in GAINS.items():
        out.append(f"   {sym} : {fmt_x(t[3])} / {fmt_x(t[4])} / {fmt_x(t[5])}")
    out.append(f" 3 / 4 / 5 BNS : {GAINS_BONUS_SYMBOLE[3]}x / {GAINS_BONUS_SYMBOLE[4]}x / {GAINS_BONUS_SYMBOLE[5]}x"
               f" la mise + {TOURS_GRATUITS} tours gratuits.")
    out.append(" Cascades : les symboles gagnants (écrits en minuscules) disparaissent, d'autres tombent,")
    out.append(f"   et chaque gain suivant est multiplié (x{', x'.join(str(m) for m in ECHELLE_CASCADE[1:])}).")
    out.append(" Bonus : d'abord les coffres (multiplicateur, gains fixes, un vide), puis les tours gratuits.")
    out.append(f"   Dans le bonus : WLD collés jusqu'à la fin, WLD qui s'étendent sur les rouleaux 2 à 4,")
    out.append(f"   3 / 4 / 5 BNS = +{RELANCE_TOURS[3]} / +{RELANCE_TOURS[4]} / +{RELANCE_TOURS[5]} tours (max {TOURS_MAX}).")
    out.append(f" Commandes : ab = acheter le bonus ({PRIX_BONUS}x la mise), auto = tours automatiques,")
    out.append("   gains = rappeler cette aide. Entrée pendant un tirage = fast spin (pas dans les bonus).")
    return out


# ------------------------------------------------------------------ session, objectifs, événements

def stats_session(etat):
    return etat.setdefault('sl', {'bonus': 0, 'near': 0})


def debloque_gain(etat, total, mise):
    if total >= 20 * mise:
        debloquer(etat, 'sl_x20')
    if total >= 50 * mise:
        debloquer(etat, 'sl_x50')
    if total >= 100 * mise:
        debloquer(etat, 'slots_x100')
    if total >= 200 * mise:
        debloquer(etat, 'sl_x200')


def evenements_tour(etat, mise, t):
    """Objectifs liés à un tour normal (lignes, cascades, near-miss)."""
    s = stats_session(etat)
    if t['total'] > 0:
        debloquer(etat, 'sl_gagne')
    if t['cascades'] >= 1:
        debloquer(etat, 'sl_casc')
    if t['cascades'] >= 2:
        debloquer(etat, 'sl_casc3')
    if t['cascades'] >= 4:
        debloquer(etat, 'sl_casc4')
    for e in t['etapes']:
        for i, m, nb, cases in e['gains']:
            if i in (3, 4):
                debloquer(etat, 'sl_v')
            premier = next((c for c in cases if c != 'WLD'), None)
            if premier == 'DIA':
                debloquer(etat, 'sl_dia')
            if 'WLD' in cases[:nb]:
                debloquer(etat, 'sl_wild_ligne')
            if nb == 5:
                debloquer(etat, 'sl_5ligne')
            if nb == 5 and premier == '777':
                debloquer(etat, 'slots_777')
        if e['bns'] >= 5:
            debloquer(etat, 'sl_5bns')
    if t['bns_initial'] == 2 and not t['declenche']:
        s['near'] += 1
        compter(etat, 'sl_near')


def evenements_bonus(etat, mise, res):
    s = stats_session(etat)
    s['bonus'] += 1
    compter(etat, 'slots_bonus')
    debloquer(etat, 'slots_free')
    if s['bonus'] >= 3:
        debloquer(etat, 'sl_bonus3')
    if s['bonus'] >= 5:
        debloquer(etat, 'sl_session5')
    if res['relances'] >= 1:
        debloquer(etat, 'sl_relance')
    if res['relances'] >= 3:
        debloquer(etat, 'sl_relance3')
    if res['max_collants'] >= 3:
        debloquer(etat, 'sl_collants3')
    if res['max_collants'] >= 8:
        debloquer(etat, 'sl_collants8')
    if res['etendus']:
        debloquer(etat, 'sl_etendu')
    if res['mult_coffre'] >= 5:
        debloquer(etat, 'sl_mult5')
    if res['mult_coffre'] >= 10:
        debloquer(etat, 'sl_mult10')
    x = res['total'] / mise
    if x >= 30:
        debloquer(etat, 'sl_bonus_x30')
    if x >= 100:
        debloquer(etat, 'sl_bonus_x100')
    if res['plafond']:
        debloquer(etat, 'sl_plafond')
    cumul = etat.get('cumul')
    if cumul is not None and not etat.get('tournoi'):
        ancien = cumul.get('sl_record_bonus', 0)
        if x > ancien:
            cumul['sl_record_bonus'] = round(x, 1)
            if ancien > 0 and cumul.get('slots_bonus', 0) >= 5:
                debloquer(etat, 'sl_record')


# ------------------------------------------------------------------ coffres et bonus

def jouer_coffres(etat, mise, nb):
    """Pick-me : ouvre nb coffres sur 5. Retourne (multiplicateur, gains fixes, valeur du coffre mult ou 0)."""
    coffres = preparer_coffres()
    ouverts = {}
    mult = MULT_BASE_BONUS
    mult_coffre = 0
    fixes = 0.0

    def montrer():
        cases = []
        for i in range(5):
            if i in ouverts:
                t, v = coffres[i]
                cases.append(f"[{i + 1}: " + ("x" + str(v) if t == 'mult' else "+" + fmt(v * mise) if t == 'fixe' else "vide") + "]")
            else:
                cases.append(f"[{i + 1}]")
        print("   " + " ".join(cases))

    print(f"\n Coffres : ouvre {nb} coffres sur 5. Un contient un multiplicateur (x2 à x10) pour les tours gratuits,")
    print(f" trois contiennent des gains fixes, un est vide. Sans multiplicateur, les tours gratuits sont à x{fmt(MULT_BASE_BONUS)}.")
    for essai in range(1, nb + 1):
        montrer()
        libres = [i for i in range(5) if i not in ouverts]
        try:
            s = input(f" Coffre {essai}/{nb} (1-5, Entrée = au hasard) > ").strip()
        except Quitter:
            s = ''
        choix = None
        if s.isdigit() and 1 <= int(s) <= 5 and (int(s) - 1) in libres:
            choix = int(s) - 1
        if choix is None:
            choix = random.choice(libres)
        ouverts[choix] = True
        pause_b(0.6)
        t, v = coffres[choix]
        debloquer(etat, 'sl_coffre')
        if t == 'mult':
            mult = v
            mult_coffre = v
            print(f" Coffre {choix + 1} : multiplicateur x{v} sur les tours gratuits !")
        elif t == 'fixe':
            gain = v * mise
            fixes += gain
            etat['jetons'] += gain
            print(f" Coffre {choix + 1} : +{fmt(gain)} ({v}x la mise)")
        else:
            debloquer(etat, 'sl_vide')
            print(f" Coffre {choix + 1} : vide.")
    for i in range(5):
        if i not in ouverts:
            ouverts[i] = True
    montrer()
    pause_b(0.8)
    return mult, fixes, mult_coffre


def jouer_bonus(etat, mise, bns, achat=False):
    """Déroule le bonus complet (non passable). Retourne un dict de résultat."""
    pp_plus.vider_clavier()
    print()
    pause_b(0.5)
    if achat:
        print(f" ACHAT DE BONUS : tours gratuits lancés pour {fmt(PRIX_BONUS * mise)}.")
    else:
        print(f" BONUS ! {bns} BNS : {TOURS_GRATUITS} tours gratuits.")
    pause_b(0.9)
    mult, fixes, mult_coffre = jouer_coffres(etat, mise, COFFRES_PAR_BNS[min(bns, 5)])
    print(f"\n {TOURS_GRATUITS} tours gratuits à x{fmt(mult)}. WLD collés et étendus (rouleaux 2 à 4).\n")
    pause_b(0.8)
    total = 0.0
    max_collants = 0
    etendus = False
    relances = 0
    plafond = False
    dernier = None
    for tr in tours_bonus(mise, mult):
        pause_b(0.55)
        gagnantes = cases_gagnantes(tr['gains'])
        print(f" Tour gratuit {tr['k']}/{tr['prevu']}  (WLD collés : {len(tr['collants'])})")
        afficher_grille(tr['grille'], gagnantes)
        if tr['etendus']:
            etendus = True
            print(" WLD étendu sur le rouleau " + ", ".join(str(r + 1) for r in tr['etendus']) + ".")
        for i, m, nb, cases in tr['gains']:
            print(f" Ligne {i + 1} ({NOMS_LIGNES[i]}) : {' '.join(cases)} = +{fmt(mise / 5 * m * mult)}")
        total += tr['valeur']
        etat['jetons'] += tr['valeur']
        max_collants = max(max_collants, len(tr['collants']))
        relances = tr['relances']
        plafond = plafond or tr['plafond']
        if tr['plus']:
            pause_b(0.5)
            print(f" {tr['bns']} BNS : +{tr['plus']} tours gratuits !")
        print(f" Tour gratuit : {'+' + fmt(tr['valeur']) if tr['valeur'] else 'rien'}\n")
        dernier = tr
    if plafond:
        print(f" Plafond de gain du bonus atteint ({PLAFOND_BONUS}x la mise).")
    total_bonus = total + fixes
    print(f" Bonus terminé : +{fmt(round(total_bonus, 2))} ({fmt(round(total_bonus / mise, 1))}x la mise,"
          f" dont {fmt(fixes)} de coffres), {dernier['k'] if dernier else 0} tours.\n")
    pause_b(0.6)
    pp_plus.vider_clavier()
    res = {'total': total_bonus, 'relances': relances, 'max_collants': max_collants, 'etendus': etendus,
           'mult_coffre': mult_coffre, 'plafond': plafond}
    evenements_bonus(etat, mise, res)
    return res


# ------------------------------------------------------------------ un tour, achat, auto-spin

def afficher_etapes(etat, mise, t):
    global _rapide
    for n, e in enumerate(t['etapes']):
        if n > 0:
            pause_s(0.55)
            print(f"\n Cascade x{e['mult']}")
        afficher_grille(e['grille'], cases_gagnantes(e['gains']))
        for i, m, nb, cases in e['gains']:
            print(f" Ligne {i + 1} ({NOMS_LIGNES[i]}) : {' '.join(cases)} = +{fmt(round(mise / 5 * m * e['mult'], 2))}")
        if e.get('prime_bns'):
            print(f" {e['bns']} BNS : +{fmt(e['prime_bns'])}")


def jouer_un_tour(etat, mise, animation=True):
    """Un tour complet. Retourne (gain total du tour, bonus ou None)."""
    global _rapide
    etat['jetons'] -= mise
    t = tour_base(mise)
    _rapide = False
    if animation:
        print()
        sauter = animer(t['etapes'][0]['grille'], passable=(t['bns_initial'] < 3))
        _rapide = sauter
        afficher_etapes(etat, mise, t)
    etat['jetons'] += t['total']
    if animation:
        if t['total']:
            print(f" Gagné +{fmt(round(t['total'], 2))}")
        else:
            print(f" Perdu -{fmt(mise)}")
        if t['bns_initial'] == 2 and not t['declenche']:
            print(" Presque : 2 BNS.")
    evenements_tour(etat, mise, t)
    total = t['total']
    bonus = None
    if t['declenche']:
        bonus = jouer_bonus(etat, mise, t['declenche'])
        total += bonus['total']
    debloque_gain(etat, total, mise)
    return total, bonus, t


def jouer_slots(etat, mise):
    auto = etat.pop('_auto', None)
    achat = etat.pop('_achat', False)
    if auto and not achat:
        return jouer_auto(etat, mise, auto)
    if achat:
        cout = PRIX_BONUS * mise
        etat['jetons'] -= cout
        debloquer(etat, 'sl_achat')
        compter(etat, 'sl_achat')
        res = jouer_bonus(etat, mise, 3, achat=True)
        debloque_gain(etat, res['total'], cout)
        etat['jetons'] = round(etat['jetons'], 2)
        net = res['total'] - cout
        print(f" Achat de bonus : {'+' if net >= 0 else ''}{fmt(round(net, 2))} net. Jetons : {fmt(etat['jetons'])}\n")
        return cout
    print()
    total, bonus, t = jouer_un_tour(etat, mise)
    etat['jetons'] = round(etat['jetons'], 2)
    print(f" Jetons : {fmt(etat['jetons'])}\n")
    return mise


def demander_slots(etat):
    while True:
        mise = demander_mise(etat)
        if mise is None:
            return None
        if etat.get('_achat') and PRIX_BONUS * mise > etat['jetons']:
            print(f" Achat de bonus : il faut {fmt(PRIX_BONUS * mise)} jetons pour cette mise. Achat annulé.")
            etat['_achat'] = False
            continue
        return mise


def commande(etat, saisie):
    """Commandes propres à la machine à sous, appelées depuis la saisie de mise. Vrai si traitée."""
    if saisie in ('gains', 'aide', 'help'):
        for l in lignes_aide():
            print(l)
        return True
    if saisie in ('ab', 'achat'):
        if etat.get('_achat'):
            etat['_achat'] = False
            print(" Achat de bonus annulé.")
        else:
            etat['_achat'] = True
            print(f" Achat de bonus : ta prochaine mise sera multipliée par {PRIX_BONUS} et lance directement le bonus")
            print(" (coffres puis tours gratuits). Entre la mise, ou ab pour annuler.")
        return True
    if saisie == 'auto':
        if etat.get('tournoi'):
            print(" Auto-spin indisponible en tournoi.")
            return True
        configurer_auto(etat)
        return True
    return False


def _lire_nombre(invite, defaut, valides=None):
    while True:
        try:
            s = input(invite).strip().lower()
        except Quitter:
            return None
        if s in ('q', 'quit', 'exit', 'x'):
            return None
        if s == '':
            return defaut
        try:
            v = float(s.replace(',', '.'))
        except ValueError:
            print(" Un nombre.")
            continue
        if valides and v not in valides:
            print(" Choix possibles : " + ", ".join(str(x) for x in valides))
            continue
        return v


def configurer_auto(etat):
    n = _lire_nombre("Auto-spin : nombre de tours (10, 25 ou 50, Entrée = 10, q = annuler) > ", 10, (10, 25, 50))
    if n is None:
        print(" Annulé.")
        return
    g = _lire_nombre("Arrêt si un tour rapporte au moins (x la mise, Entrée = 20) > ", 20)
    if g is None:
        print(" Annulé.")
        return
    p = _lire_nombre("Arrêt si tu perds au total (x la mise, Entrée = 30) > ", 30)
    if p is None:
        print(" Annulé.")
        return
    etat['_auto'] = {'n': int(n), 'gain_x': g, 'perte_x': p}
    print(f" Auto-spin prêt : {int(n)} tours, arrêt sur gain >= {fmt(g)}x ou perte >= {fmt(p)}x la mise,"
          " ou sur un bonus/jackpot. Appuie sur Entrée pendant les tours pour arrêter.")
    print(" Entre ta mise pour lancer.")


def jouer_auto(etat, mise, auto):
    n = auto['n']
    depart = etat['jetons']
    mis = 0.0
    gagne = 0.0
    fait = 0
    raison = "terminé"
    print(f"\n Auto-spin : {n} tours de {fmt(mise)}.")
    pp_plus.vider_clavier()
    for i in range(1, n + 1):
        if etat['jetons'] < mise:
            raison = "plus assez de jetons"
            break
        if i > 1 and pp_plus.entree_pressee():
            raison = "arrêté (Entrée)"
            break
        total, bonus, t = jouer_un_tour(etat, mise, animation=False)
        fait += 1
        mis += mise
        gagne += total
        tag = ""
        if t['cascades']:
            tag += f" cascade x{t['cascades']}"
        if t['bns_initial'] == 2 and not t['declenche']:
            tag += " presque (2 BNS)"
        net = total - mise
        print(f" {i:>2}/{n} : {'+' + fmt(round(total, 2)) if total else 'rien':>8}{tag}   Jetons {fmt(round(etat['jetons'], 2))}")
        if bonus:
            raison = "bonus déclenché"
            break
        if pp_plus.jackpot(etat, mise):
            raison = "jackpot !"
            break
        if total >= auto['gain_x'] * mise:
            raison = f"gros gain ({fmt(round(total / mise, 1))}x la mise)"
            break
        if depart - etat['jetons'] >= auto['perte_x'] * mise:
            raison = "limite de perte atteinte"
            break
        pp_plus.dormir(0.15)
    etat['jetons'] = round(etat['jetons'], 2)
    net = gagne - mis
    print(f" Auto-spin terminé ({raison}) : {fait} tours, {'+' if net >= 0 else ''}{fmt(round(net, 2))} net."
          f" Jetons : {fmt(etat['jetons'])}\n")
    if fait >= 10:
        debloquer(etat, 'sl_auto10')
    if fait >= 50 and raison == "terminé":
        debloquer(etat, 'sl_auto50')
        if net > 0:
            debloquer(etat, 'sl_auto_profit')
    if fait > 1:
        compter(etat, 'slots', fait - 1)
        etat['compte_session']['slots'] = etat['compte_session'].get('slots', 0) + fait - 1
    etat['_auto_fait'] = True
    return max(mis, mise)


# ------------------------------------------------------------------ installation

OBJ_DEBUTANT = [
    ('sl_gagne', "Machine à sous : gagner un tour", 100),
    ('sl_casc', "Machine à sous : déclencher une cascade", 150),
    ('sl_v', "Machine à sous : gagner sur la ligne en V", 150),
    ('sl_dia', "Machine à sous : aligner 3 DIA ou plus", 200),
    ('sl_wild_ligne', "Machine à sous : gagner avec un WLD dans la ligne", 150),
    ('sl_coffre', "Machine à sous : ouvrir un coffre du bonus", 200),
    ('sl_vide', "Machine à sous : tomber sur le coffre vide", 100),
    ('sl_auto10', "Machine à sous : lancer un auto-spin d'au moins 10 tours", 200),
]
OBJ_CONFIRME = [
    ('sl_casc3', "Machine à sous : enchaîner 3 gains avec les cascades", 400),
    ('sl_5ligne', "Machine à sous : 5 symboles identiques sur une ligne", 500),
    ('sl_relance', "Machine à sous : relancer les tours gratuits", 500),
    ('sl_collants3', "Machine à sous : avoir 3 WLD collés en même temps", 500),
    ('sl_etendu', "Machine à sous : voir un WLD s'étendre dans le bonus", 300),
    ('sl_bonus3', "Machine à sous : 3 bonus dans la même session", 600),
    ('sl_achat', "Machine à sous : acheter un bonus", 400),
    ('sl_mult5', "Machine à sous : coffre multiplicateur x5 ou plus", 500),
    ('sl_x20', "Machine à sous : gagner 20x la mise sur un tour", 400),
    ('sl_x50', "Machine à sous : gagner 50x la mise sur un tour", 800),
    ('sl_bonus_x30', "Machine à sous : un bonus qui rapporte 30x la mise", 600),
    ('sl_near5', "Machine à sous : 5 presque-bonus (2 BNS) au total", 300),
    ('sl_auto50', "Machine à sous : finir un auto-spin de 50 tours", 500),
    ('slots_bonus10', "Machine à sous : déclencher 10 bonus (au total)", 800),
]
OBJ_EXPERT = [
    ('sl_casc4', "Machine à sous : 4 cascades dans un même tour", 2500),
    ('sl_relance3', "Machine à sous : relancer 3 fois dans un même bonus", 2000),
    ('sl_collants8', "Machine à sous : 8 WLD collés en même temps", 2500),
    ('sl_session5', "Machine à sous : 5 bonus dans la même session", 2000),
    ('sl_mult10', "Machine à sous : coffre multiplicateur x10", 3000),
    ('sl_bonus_x100', "Machine à sous : un bonus qui rapporte 100x la mise", 3000),
    ('sl_record', "Machine à sous : battre ton record de bonus (après 5 bonus)", 600),
    ('sl_5bns', "Machine à sous : aligner 5 BNS", 3000),
    ('sl_x200', "Machine à sous : gagner 200x la mise sur un tour", 5000),
    ('sl_auto_profit', "Machine à sous : finir un auto-spin de 50 tours en bénéfice", 1500),
    ('sl_achat5', "Machine à sous : acheter 5 bonus (au total)", 1500),
    ('slots_bonus25', "Machine à sous : déclencher 25 bonus (au total)", 3000),
]
OBJ_LEGENDE = [
    ('sl_plafond', "Machine à sous : atteindre le plafond de gain d'un bonus", 10000),
]


def installer(ns):
    global pp_plus, PAUSE
    g = globals()
    for k in NEEDED:
        g[k] = ns[k]
    import pp_plus as _p
    pp_plus = _p
    JEUX_EXTRA['slots'] = {
        'nom': 'Machine à sous', 'demander': demander_slots, 'jouer': jouer_slots, 'compteur': 'slots',
        'aide': lignes_aide(), 'commande': commande}
    CUMULS['sl_near'] = [(5, 'sl_near5')]
    CUMULS['slots_bonus'] = [(10, 'slots_bonus10'), (25, 'slots_bonus25')]
    CUMULS['sl_achat'] = [(5, 'sl_achat5')]
    NOMS_CUMULS['sl_near'] = "Presque-bonus (2 BNS)"
    NOMS_CUMULS['slots_bonus'] = "Bonus de machine à sous"
    NOMS_CUMULS['sl_achat'] = "Bonus achetés"
    ajouter_objectifs('Débutant', OBJ_DEBUTANT)
    ajouter_objectifs('Confirmé', OBJ_CONFIRME)
    ajouter_objectifs('Expert', OBJ_EXPERT)
    ajouter_objectifs('Légende', OBJ_LEGENDE)
