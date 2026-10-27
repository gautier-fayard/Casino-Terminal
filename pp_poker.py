"""Poker pour pp.py : Ultimate Texas Hold'em (decisions corrigees) et entrainement poker.

Ce module est charge par pp.py (installer). Il ne se lance pas tout seul.
"""
import random
from itertools import combinations

NEEDED = ['fmt', 'pause', 'corriger', 'fin', 'debloquer', 'compter', 'Quitter', 'demander_mise',
          'RANGS', 'COULEURS', 'nouveau_sabot', 'ajouter_objectifs', 'JEUX_EXTRA', 'NOMS_JEUX',
          'CUMULS', 'NOMS_CUMULS']

NOMS_MAIN = ['carte haute', 'paire', 'double paire', 'brelan', 'suite', 'couleur', 'full', 'carré',
             'quinte flush']
BLIND = {4: 1, 5: 1.5, 6: 3, 7: 10, 8: 50}  # gains du blind (suite ou mieux)


def installer(ns):
    g = globals()
    for k in NEEDED:
        g[k] = ns[k]
    NOMS_JEUX['holdem'] = "Hold'em"
    JEUX_EXTRA['holdem'] = {
        'nom': "Hold'em", 'demander': demander_holdem, 'jouer': jouer_holdem,
        'compteur': 'holdem',
        'aide': [" Ultimate Texas Hold'em. Ante + Blind (2 mises), tu joues contre la banque.",
                 " Préflop : relance 4x (ou 3x) ou check. Flop : relance 2x ou check.",
                 " River : relance 1x ou fold (fold = tu perds Ante + Blind). Chaque décision est corrigée.",
                 " Ante : la banque doit avoir une paire ou mieux, sinon l'Ante est rendu.",
                 " Blind : paie seulement avec une suite ou mieux (suite 1:1, couleur 3:2, full 3:1,",
                 " carré 10:1, quinte flush 50:1, royale 500:1), sinon rendu. Mise max = solde / 6."]}
    CUMULS['holdem'] = [(50, 'uth50'), (500, 'uth500')]
    NOMS_CUMULS['holdem'] = "Mains de Hold'em"
    ajouter_objectifs('Débutant', [
        ('uth_gagne', "Hold'em : gagner une main", 100),
        ('uth_4x', "Hold'em : gagner une main relancée 4x au préflop", 200),
    ])
    ajouter_objectifs('Confirmé', [
        ('uth_blind', "Hold'em : toucher un bonus de Blind (suite ou mieux)", 500),
        ('uth_river', "Hold'em : gagner une main relancée sur le river", 400),
        ('uth50', "Jouer 50 mains de Hold'em (au total)", 300),
    ])
    ajouter_objectifs('Expert', [
        ('uth_couleur', "Hold'em : toucher un Blind avec une couleur ou mieux", 2000),
        ('uth500', "Jouer 500 mains de Hold'em (au total)", 3000),
    ])


# ---------------------------------------------------------------- évaluation

def rang_5(cartes):
    rangs = sorted((c[2] + 2 for c in cartes), reverse=True)
    meme = len({c[3] for c in cartes}) == 1
    compte = {}
    for x in rangs:
        compte[x] = compte.get(x, 0) + 1
    groupes = sorted(compte.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    ordre = [r for r, _ in groupes]
    freq = [n for _, n in groupes]
    uniques = sorted(compte, reverse=True)
    suite = 0
    if len(uniques) == 5:
        if uniques[0] - uniques[4] == 4:
            suite = uniques[0]
        elif uniques == [14, 5, 4, 3, 2]:
            suite = 5
    if suite and meme:
        return (8, suite)
    if freq[0] == 4:
        return (7, ordre[0], ordre[1])
    if freq[:2] == [3, 2]:
        return (6, ordre[0], ordre[1])
    if meme:
        return (5,) + tuple(uniques)
    if suite:
        return (4, suite)
    if freq[0] == 3:
        return (3,) + tuple(ordre)
    if freq[:2] == [2, 2]:
        return (2,) + tuple(ordre)
    if freq[0] == 2:
        return (1,) + tuple(ordre)
    return (0,) + tuple(uniques)


def evaluer_7(cartes):
    return max(rang_5(s) for s in combinations(cartes, 5))


def nom_main(r):
    if r[0] == 8 and r[1] == 14:
        return "quinte flush royale"
    return NOMS_MAIN[r[0]]


def gain_blind(r):
    if r[0] == 8 and r[1] == 14:
        return 500
    return BLIND.get(r[0], 0)


def paquet_complet():
    return [(v, r + s, i, s) for i, (r, v) in enumerate(RANGS) for s in COULEURS]


def montrer(cartes):
    return "  ".join(c[1] for c in cartes)


NOM_RANG = {14: 'As', 13: 'Roi', 12: 'Dame', 11: 'Valet', 10: '10'}


def nom_rang(v):
    return NOM_RANG.get(v, str(v))


# ---------------------------------------------------------------- stratégie UTH

def decision_preflop(h):
    """(bonne, raison, acceptables) - table de base simplifiée."""
    a, b = sorted((h[0][2] + 2, h[1][2] + 2), reverse=True)
    suited = h[0][3] == h[1][3]
    if a == b:
        if a == 2:
            return '4X', "Paire de 2 : cas limite, relancer ou checker se valent presque.", {'CHECK'}
        return '4X', "Toute paire de 3 ou plus se relance 4x : l'avance est nette.", set()
    if a == 14:
        return '4X', "Tout As se relance 4x : la carte haute domine la banque.", set()
    if a == 13:
        if (suited and b >= 5) or (not suited and b >= 8):
            return '4X', "Roi avec ce kicker : assez fort pour relancer 4x.", set()
        return 'CHECK', "Roi trop faible ici (il faut Roi-5 assorti ou Roi-8 dépareillé) : on check.", set()
    if a == 12:
        if (suited and b >= 6) or (not suited and b >= 8):
            return '4X', "Dame avec ce kicker : relance 4x.", set()
        return 'CHECK', "Dame trop faible ici (il faut Dame-6 assortie ou Dame-8 dépareillée) : on check.", set()
    if a == 11:
        if (suited and b >= 8) or (not suited and b == 10):
            return '4X', "Valet avec ce kicker : relance 4x.", set()
        return 'CHECK', "Valet trop faible ici (il faut Valet-8 assorti ou Valet-10) : on check.", set()
    return 'CHECK', "Main trop faible pour relancer : on check et on voit le flop gratuitement.", set()


def decision_flop(h, board):
    cartes = h + board
    r = rang_5(cartes)
    if r[0] >= 2:
        return '2X', f"{nom_main(r).capitalize()} dès le flop : relance 2x."
    if r[0] == 1:
        paire = r[1]
        if any(c[2] + 2 == paire for c in h):
            return '2X', "Paire avec au moins une de tes cartes (paire cachée) : relance 2x."
    for s in COULEURS:
        du_s = [c for c in cartes if c[3] == s]
        if len(du_s) == 4 and any(c[3] == s and c[2] + 2 >= 10 for c in h):
            return '2X', "Tirage couleur avec une carte de 10 ou plus : relance 2x."
    return 'CHECK', "Pas de paire avec tes cartes ni de tirage couleur solide : on check, le river décidera."


def ev_river(h, board):
    """EV exacte (en mises) de la relance 1x sur le river, face aux 990 mains de la banque."""
    joueur = evaluer_7(h + board)
    vus = {c[1] for c in h + board}
    reste = [c for c in paquet_complet() if c[1] not in vus]
    bg = gain_blind(joueur)
    total = gagne = perd = n = 0
    for d in combinations(reste, 2):
        banque = evaluer_7(list(d) + board)
        qualifie = banque[0] >= 1
        n += 1
        if joueur > banque:
            gagne += 1
            total += 1 + (1 if qualifie else 0) + bg
        elif joueur < banque:
            perd += 1
            total -= 2 + (1 if qualifie else 0)
    return total / n, gagne / n, perd / n


def decision_river(h, board):
    ev, p_gagne, p_perd = ev_river(h, board)
    if ev >= -2:
        return '1X', (f"Relancer coûte moins cher que se coucher : EV {ev:+.2f} mise contre -2.00 "
                      f"(tu gagnes {p_gagne * 100:.0f} % du temps).")
    return 'FOLD', (f"Trop de mains te battent : relancer vaut {ev:+.2f} mise, se coucher -2.00. "
                    f"(tu perds {p_perd * 100:.0f} % du temps).")


# ---------------------------------------------------------------- jeu UTH

def lire_choix(invite, valides):
    while True:
        s = input(invite).strip().lower()
        if s in ('q', 'quit', 'exit'):
            raise Quitter
        if s in valides:
            return valides[s]
        print(" Choix possibles : " + ", ".join(valides))


def demander_holdem(etat):
    while True:
        mise = demander_mise(etat)
        if mise is None:
            return None
        if mise * 6 > etat['jetons']:
            print(f" Mise max {fmt(etat['jetons'] // 6)} (Ante + Blind + relance 4x).")
            continue
        return mise


def table(board, n):
    return "  ".join([c[1] for c in board[:n]] + ["--"] * (5 - n))


def jouer_holdem(etat, mise):
    paquet = nouveau_sabot(1)
    h = [paquet.pop(), paquet.pop()]
    banque = [paquet.pop(), paquet.pop()]
    board = [paquet.pop() for _ in range(5)]
    engage = 2 * mise
    etat['jetons'] -= engage
    try:
        play = _tour_holdem(etat, mise, h, banque, board)
        if play is None:
            etat['jetons'] = round(etat['jetons'], 2)
            return 2 * mise
        return engage + play * mise
    except Quitter:
        etat['jetons'] += engage
        raise


def _tour_holdem(etat, mise, h, banque, board):
    """Retourne le multiple de mise joué (4, 3, 2, 1) ou None si fold."""
    print(f" Ante {fmt(mise)} + Blind {fmt(mise)}")
    print(f" Ta main : {montrer(h)}")
    print(f" Table   : {table(board, 0)}")

    bonne, raison, ok = decision_preflop(h)
    choix = lire_choix("Préflop ? (4 = relance 4x, 3 = relance 3x, c = check) > ",
                       {'4': '4X', '3': '3X', 'c': 'CHECK', 'x': 'CHECK'})
    eff = choix
    if choix == '3X' and bonne == '4X':
        eff = '4X'
        print(" Proche : 3x passe, mais 4x est optimal avec cette main.")
    elif choix in ok:
        eff = bonne
    corriger(etat, eff, bonne, raison, f"Hold'em préflop : {montrer(h)}")
    play = 0
    if choix in ('4X', '3X'):
        play = int(choix[0])
        etat['jetons'] -= play * mise
        pause()
        print(f" Table   : {table(board, 5)}")
    else:
        pause()
        print(f" Table   : {table(board, 3)}")
        bonne, raison = decision_flop(h, board[:3])
        choix = lire_choix("Flop ? (2 = relance 2x, c = check) > ", {'2': '2X', 'c': 'CHECK', 'x': 'CHECK'})
        corriger(etat, choix, bonne, raison, f"Hold'em flop : {montrer(h)} | {montrer(board[:3])}")
        if choix == '2X':
            play = 2
            etat['jetons'] -= play * mise
            pause()
            print(f" Table   : {table(board, 5)}")
        else:
            pause()
            print(f" Table   : {table(board, 5)}")
            bonne, raison = decision_river(h, board)
            choix = lire_choix("River ? (1 = relance 1x, f = fold) > ", {'1': '1X', 'f': 'FOLD'})
            corriger(etat, choix, bonne, raison, f"Hold'em river : {montrer(h)} | {montrer(board)}")
            if choix == 'FOLD':
                print(f" Fold : perdu -{fmt(2 * mise)}")
                print(f" Jetons : {fmt(etat['jetons'])}\n")
                return None
            play = 1
            etat['jetons'] -= play * mise
            etat['_river'] = True

    pause()
    joueur = evaluer_7(h + board)
    adverse = evaluer_7(banque + board)
    qualifie = adverse[0] >= 1
    print(f" Banque  : {montrer(banque)} ({nom_main(adverse)}{'' if qualifie else ', ne qualifie pas'})")
    print(f" Toi     : {nom_main(joueur)}")
    pause()
    bg = gain_blind(joueur)
    if joueur > adverse:
        retour_play = 2 * play * mise
        retour_ante = 2 * mise if qualifie else mise
        retour_blind = mise * (1 + bg)
        resultat = "gagné"
    elif joueur < adverse:
        retour_play = 0
        retour_ante = 0 if qualifie else mise
        retour_blind = 0
        resultat = "perdu"
    else:
        retour_play, retour_ante, retour_blind = play * mise, mise, mise
        resultat = "égalité"
    etat['jetons'] += retour_play + retour_ante + retour_blind
    etat['jetons'] = round(etat['jetons'], 2)
    mise_totale = (2 + play) * mise
    net = retour_play + retour_ante + retour_blind - mise_totale
    if resultat == "gagné":
        print(f" Gagné +{fmt(net)}" + (f" (Blind : {nom_main(joueur)} {bg}:1)" if bg else ""))
        debloquer(etat, 'uth_gagne')
        if play == 4:
            debloquer(etat, 'uth_4x')
        if etat.pop('_river', False):
            debloquer(etat, 'uth_river')
        if bg:
            debloquer(etat, 'uth_blind')
        if joueur[0] >= 5:
            debloquer(etat, 'uth_couleur')
    elif resultat == "perdu":
        print(f" Perdu {fmt(net)}")
    else:
        print(" Égalité : mises rendues")
    etat.pop('_river', None)
    print(f" Jetons : {fmt(etat['jetons'])}\n")
    return play


# ======================================================== entraînement poker

ORDRE = 'AKQJT98765432'
IDX = {'A': 12, 'K': 11, 'Q': 10, 'J': 9, 'T': 8, '9': 7, '8': 6, '7': 5, '6': 4, '5': 3, '4': 2, '3': 1, '2': 0}
POSITIONS = ['UTG', 'HJ', 'CO', 'BTN', 'SB']

# Ranges d'ouverture de référence (6-max, 100 bb, cash, ouverture 2.5x, SB 3x).
# Ce sont des ordres de grandeur courants, à adapter à tes propres tableaux.
RANGES_RFI = {
    'UTG': "55+ A9s+ A5s A4s KTs+ QTs+ JTs T9s 98s ATo+ KQo",
    'HJ': "44+ A8s+ A5s-A2s KTs+ K9s QTs+ Q9s J9s+ T9s 98s 87s ATo+ KJo+ QJo",
    'CO': "22+ A2s+ K8s+ Q9s+ J9s+ T8s+ 98s 87s 76s 65s ATo+ KTo+ QTo+ JTo",
    'BTN': "22+ A2s+ K2s+ Q4s+ J6s+ T6s+ 96s+ 85s+ 75s+ 64s+ 53s+ 43s A2o+ K8o+ Q9o+ J9o+ T8o+ 98o 87o",
    'SB': "22+ A2s+ K4s+ Q8s+ J8s+ T7s+ 97s+ 86s+ 76s 65s 54s A5o+ K9o+ QTo+ JTo",
}

PRESETS_VILAIN = {
    'range d\'ouverture UTG': 'UTG', 'range d\'ouverture CO': 'CO', 'range d\'ouverture BTN': 'BTN',
}


def _etendre(token):
    """'77+', 'A9s+', 'KQo', 'A5s-A2s' -> classes ('77', 'A9s', ...)."""
    out = []
    if '-' in token:
        a, b = token.split('-')
        hi, lo1, lo2 = a[0], IDX[a[1]], IDX[b[1]]
        suf = a[2:]
        for i in range(min(lo1, lo2), max(lo1, lo2) + 1):
            out.append(hi + ORDRE[12 - i] + suf)
        return out
    plus = token.endswith('+')
    token = token.rstrip('+')
    if len(token) == 2:
        i = IDX[token[0]]
        if plus:
            out += [ORDRE[12 - k] * 2 for k in range(i, 13)]
        else:
            out.append(token)
        return out
    hi, lo, suf = token[0], token[1], token[2]
    if plus:
        for k in range(IDX[lo], IDX[hi]):
            out.append(hi + ORDRE[12 - k] + suf)
    else:
        out.append(token)
    return out


def lire_range(texte):
    classes = set()
    for tok in texte.split():
        classes.update(_etendre(tok))
    return classes


RANGE_SET = {p: lire_range(t) for p, t in RANGES_RFI.items()}


def nb_combos(classe):
    if len(classe) == 2:
        return 6
    return 4 if classe[2] == 's' else 12


def pourcentage(classes):
    return sum(nb_combos(c) for c in classes) / 1326 * 100


def toutes_classes():
    out = []
    for i, a in enumerate(ORDRE):
        for j, b in enumerate(ORDRE):
            if i == j:
                out.append(a + b)
            elif i < j:
                out.append(a + b + 's')
            else:
                out.append(b + a + 'o')
    return out


def classe_de(c1, c2):
    a, b = sorted((c1[2], c2[2]), reverse=True)
    ra, rb = ORDRE[12 - a], ORDRE[12 - b]
    if a == b:
        return ra + rb
    return ra + rb + ('s' if c1[3] == c2[3] else 'o')


def combos_de(classe, morts=()):
    """Toutes les mains (paires de cartes) d'une classe, sans les cartes mortes."""
    paquet = {(c[2], c[3]): c for c in paquet_complet() if c[1] not in morts}
    a, b = IDX[classe[0]], IDX[classe[1]]
    out = []
    if a == b:
        for s1, s2 in combinations(COULEURS, 2):
            if (a, s1) in paquet and (a, s2) in paquet:
                out.append((paquet[(a, s1)], paquet[(a, s2)]))
    elif classe[2] == 's':
        for s in COULEURS:
            if (a, s) in paquet and (b, s) in paquet:
                out.append((paquet[(a, s)], paquet[(b, s)]))
    else:
        for s1 in COULEURS:
            for s2 in COULEURS:
                if s1 != s2 and (a, s1) in paquet and (b, s2) in paquet:
                    out.append((paquet[(a, s1)], paquet[(b, s2)]))
    return out


def carte_poker(c):
    r = {'10': 'T', 'V': 'J', 'D': 'Q', 'R': 'K'}.get(c[1][:-1], c[1][:-1])
    s = {'p': 's', 'c': 'h', 'k': 'd', 't': 'c'}[c[3]]
    return r + s


def cartes_poker(cartes):
    return " ".join(carte_poker(c) for c in cartes)


def cartes_pour_classe(classe):
    return random.choice(combos_de(classe))


def tirer_classe(pos):
    classes = toutes_classes()
    if random.random() < 0.5:
        return random.choices(classes, weights=[nb_combos(c) for c in classes])[0]
    voisins = {'UTG': ['HJ'], 'HJ': ['UTG', 'CO'], 'CO': ['HJ', 'BTN'], 'BTN': ['CO'], 'SB': ['CO', 'BTN']}
    autre = random.choice(voisins[pos])
    frontiere = sorted(RANGE_SET[pos] ^ RANGE_SET[autre])
    return random.choice(frontiere or classes)


def lire_ou_quitter(invite):
    s = input(invite).strip().lower()
    if s in ('q', 'quit', 'exit'):
        raise Quitter
    return s


def drill_ouverture(etat):
    pos = random.choice(POSITIONS)
    classe = tirer_classe(pos)
    c1, c2 = cartes_pour_classe(classe)
    print(f" {pos}, tout le monde a foldé devant toi (6-max, 100 bb).")
    print(f" Ta main : {cartes_poker([c1, c2])}")
    while True:
        s = lire_aide("Ouvrir ? (r = raise, f = fold, ? = aide) > ", [
            f"depuis {pos}, on ouvre environ {pourcentage(RANGE_SET[pos]):.0f} % des mains. Plus tu es tôt, plus c'est serré.",
            "paires, As, mains connectées et assorties s'ouvrent plus facilement ; les mains dépareillées et déconnectées non.",
            lambda: afficher_grille(pos)])
        if s in ('r', 'f'):
            break
        print(" r ou f")
    choix = 'RAISE' if s == 'r' else 'FOLD'
    dedans = classe in RANGE_SET[pos]
    bonne = 'RAISE' if dedans else 'FOLD'
    pct = pourcentage(RANGE_SET[pos])
    if dedans:
        raison = f"{classe} fait partie de la range d'ouverture {pos} (~{pct:.0f} % des mains)."
    else:
        premiere = next((p for p in POSITIONS if classe in RANGE_SET[p]), None)
        raison = f"{classe} est hors de la range d'ouverture {pos} (~{pct:.0f} % des mains)."
        if premiere:
            raison += f" Elle s'ouvre à partir de {premiere}."
        else:
            raison += " Elle ne s'ouvre depuis aucune position."
    corriger(etat, choix, bonne, raison, f"Ouverture {pos} : {classe}")


def afficher_grille(pos):
    ens = RANGE_SET[pos]
    print(f"\n {pos} : ~{pourcentage(ens):.0f} % des mains ('#' = ouvrir, '.' = fold)")
    print("     " + " ".join(ORDRE))
    for i, a in enumerate(ORDRE):
        ligne = []
        for j, b in enumerate(ORDRE):
            if i == j:
                cl = a + b
            elif i < j:
                cl = a + b + 's'
            else:
                cl = b + a + 'o'
            ligne.append('#' if cl in ens else '.')
        print(f"   {a} " + " ".join(ligne))
    print("   (au-dessus de la diagonale : assorties, en dessous : dépareillées)\n")


# ---- équité

def _jouer_sims(hero, board, combos, n):
    vus = {c[1] for c in hero + board}
    base = [c for c in paquet_complet() if c[1] not in vus]
    gains = 0.0
    total = 0
    for _ in range(n):
        v = random.choice(combos)
        reste = [c for c in base if c[1] != v[0][1] and c[1] != v[1][1]]
        b = board + random.sample(reste, 5 - len(board))
        a = evaluer_7(hero + b)
        o = evaluer_7(list(v) + b)
        gains += 1 if a > o else 0.5 if a == o else 0
        total += 1
    return gains / total if total else 0.0


def equite(hero, board, classes, n=2500):
    morts = {c[1] for c in hero + board}
    combos = []
    for cl in classes:
        combos += combos_de(cl, morts)
    return _jouer_sims(hero, board, combos, n)


def generer_spot():
    """Spot (hero, board, nom de range, classes) dont l'équité est intéressante."""
    for _ in range(60):
        p = random.sample(paquet_complet(), 2 + 4)
        hero, board = p[:2], p[2:2 + random.choice([3, 4])]
        nom_range = random.choice(["UTG", "CO", "BTN"])
        classes = RANGE_SET[nom_range]
        e = equite(hero, board, classes, 300)
        if 0.18 <= e <= 0.70:
            return hero, board, nom_range, classes
    return hero, board, nom_range, classes



# ---- aide pédagogique

def _cat_part(cartes):
    """Catégorie d'un ensemble de cartes (4 ou 5 cartes) sans les cartes du joueur."""
    if len(cartes) >= 5:
        return evaluer_7(cartes)[0]
    n = {}
    for c in cartes:
        n[c[2]] = n.get(c[2], 0) + 1
    v = sorted(n.values(), reverse=True)
    if v[0] == 4:
        return 7
    if v[0] == 3:
        return 3
    if v[0] == 2 and len(v) > 1 and v[1] == 2:
        return 2
    return 1 if v[0] == 2 else 0


def calcul_outs(hero, board):
    """Cartes qui améliorent la catégorie de la main du joueur (et pas seulement celle du board)."""
    vus = {c[1] for c in hero + board}
    base = evaluer_7(hero + board)[0]
    outs = []
    for c in paquet_complet():
        if c[1] in vus:
            continue
        nouv = evaluer_7(hero + board + [c])
        if nouv[0] > base and nouv[0] > _cat_part(board + [c]):
            outs.append((c, nom_main(nouv)))
    return outs


def texte_outs(hero, board):
    outs = calcul_outs(hero, board)
    if not outs:
        return 0, "aucun out net (ta main ne peut pas vraiment s'améliorer)."
    groupes = {}
    for _, nom in outs:
        groupes[nom] = groupes.get(nom, 0) + 1
    detail = ", ".join(f"{n} pour {nom}" for nom, n in sorted(groupes.items(), key=lambda x: -x[1]))
    return len(outs), f"{len(outs)} outs ({detail})."


def estimation_regle(n_outs, board):
    """Règle du 4 et du 2, avec la correction au-delà de 8 outs."""
    if len(board) == 3:
        return min(100, n_outs * 4 - max(0, n_outs - 8))
    return n_outs * 2


def lire_aide(invite, aides):
    """Lit une réponse ; '?' affiche l'aide suivante."""
    i = 0
    while True:
        s = lire_ou_quitter(invite)
        if s != '?':
            return s
        if i < len(aides):
            a = aides[i]
            if callable(a):
                a()
            else:
                print(" Aide : " + a)
            i += 1
        else:
            print(" Plus d'aide pour ce spot.")


COURS = {
    '1': ("Les cotes du pot", [
        " Quand l'adversaire mise, tu paies M pour gagner ce qu'il y a déjà au milieu.",
        " Exemple : pot 10, il mise 5. Le pot vaut 15, tu paies 5, le pot final sera 20.",
        " Tu risques 5 pour en gagner 20 au total, donc il te faut 5/20 = 25 % de chances de gagner.",
        " Formule : équité nécessaire = mise / (pot + 2 x mise).",
        " À retenir :",
        "   mise 1/3 pot -> 20 %    mise 1/2 pot -> 25 %    mise 2/3 pot -> 29 %",
        "   mise 3/4 pot -> 30 %    mise pot -> 33 %        mise 1,5 pot -> 38 %",
        " Si ton équité est au-dessus : call. En dessous : fold (sauf si tu peux gagner plus plus tard).",
    ]),
    '2': ("Les outs et la règle du 4 et du 2", [
        " Un out est une carte qui améliore ta main au point de devenir probablement gagnante.",
        " Outs classiques :",
        "   tirage couleur : 9      quinte ouverte (8 cartes) : 8      quinte ventrale : 4",
        "   deux surcartes : 6      une paire qui cherche le brelan : 2",
        "   couleur + quinte ouverte : 15 (en enlevant les doublons)",
        " Règle : outs x 4 au flop (il reste 2 cartes), outs x 2 au turn (il reste 1 carte).",
        " Au-dessus de 8 outs au flop, retire (outs - 8) : 15 outs -> 60 - 7 = 53 %, réel 54 %.",
        " Exemple : tirage couleur au flop -> 9 x 4 = 36 %, réel 35 %.",
        " Attention : la règle donne ta chance de toucher. Ton équité réelle dépend aussi de ce que",
        " ta main vaut déjà et de la force de la range en face.",
    ]),
    '3': ("Positions et ranges d'ouverture", [
        " Plus tu parles tôt, plus il reste de joueurs derrière toi qui peuvent avoir une bonne main.",
        " Donc on ouvre peu depuis UTG (~14 %) et beaucoup depuis le bouton (~45 %).",
        " Ordre à 6 : UTG, HJ, CO, BTN, SB, BB. Le bouton parle en dernier après le flop : avantage énorme.",
        " Notation : AKs = As Roi assortis (4 combos), AKo = dépareillés (12 combos), 77 = paire (6 combos).",
        " Une main qui s'ouvre de UTG s'ouvre de partout. Une main qui ne s'ouvre que du BTN est faible.",
        " Astuce pour s'entraîner : tape g dans le menu pour voir la grille, et mémorise-la position par position.",
    ]),
    '4': ("Équité : le concept", [
        " L'équité est ta part du pot si on distribuait toutes les cartes restantes sans autre mise.",
        " Tu ne connais pas la main adverse : tu raisonnes contre une range (un ensemble de mains).",
        " Repères au flop contre une range d'ouverture :",
        "   bonne paire ou mieux : souvent 60 à 80 %",
        "   tirage couleur sans rien d'autre : environ 35 %",
        "   deux surcartes sans paire : environ 25 à 30 %",
        "   rien du tout : 10 à 20 %",
        " Le but du mode Estimer son équité est d'avoir ces repères en tête sans calculer.",
    ]),
    '5': ("Méthode pour décider : call ou fold", [
        " 1. Calcule l'équité nécessaire : mise / (pot + 2 x mise).",
        " 2. Estime ton équité : compte tes outs (x4 ou x2), ajoute ce que ta main vaut déjà.",
        " 3. Compare : équité >= nécessaire -> call, sinon fold.",
        " 4. Si c'est très proche, la position et les gains futurs (implied odds) font pencher la balance.",
    ]),
}


def afficher_cours():
    while True:
        print("\n Cours de poker :")
        for k, (nom, _) in COURS.items():
            print(f"  {k}. {nom}")
        c = input(" Numéro (Entrée pour revenir) > ").strip()
        if c not in COURS:
            return
        print(f"\n {COURS[c][0]}")
        for l in COURS[c][1]:
            print(l)


def drill_cotes(etat):
    hero, board, nom_range, classes = generer_spot()
    e = equite(hero, board, classes)
    pot = random.choice([10, 12, 16, 20, 24, 30, 40, 60])
    taille = random.choice([0.33, 0.5, 0.66, 0.75, 1.0, 1.5])
    mise = max(1, round(pot * taille))
    requis = mise / (pot + 2 * mise)
    rue = "Flop" if len(board) == 3 else "Turn"
    print(f" {rue} : {cartes_poker(board)}")
    print(f" Ta main : {cartes_poker(hero)}")
    print(f" Le vilain (range d'ouverture {nom_range}, ~{pourcentage(classes):.0f} %) mise {mise} dans un pot de {pot}.")
    n_outs, txt_outs = texte_outs(hero, board)
    aides = [f"équité nécessaire = mise / (pot + 2 x mise) = {mise} / {pot + 2 * mise} = {requis * 100:.0f} %.",
             f"ta main actuelle : {nom_main(evaluer_7(hero + board))}. Tes outs : {txt_outs}",
             f"règle du {'4' if len(board) == 3 else '2'} : {n_outs} outs x {'4' if len(board) == 3 else '2'} "
             f"≈ {estimation_regle(n_outs, board)} % de chances de toucher. Compare avec les {requis * 100:.0f} % nécessaires."]
    while True:
        s = lire_aide("Call ou fold ? (c / f, ? = aide) > ", aides)
        if s in ('c', 'f'):
            break
        print(" c ou f")
    choix = 'CALL' if s == 'c' else 'FOLD'
    bonne = 'CALL' if e >= requis else 'FOLD'
    eff = choix
    note = ""
    if abs(e - requis) < 0.03:
        eff = bonne
        note = " Spot limite : les deux se défendent (implied odds, position)."
    raison = (f"Il faut {requis * 100:.0f} % d'équité (cote {pot + mise}:{mise}), tu as ≈ {e * 100:.0f} % "
              f"contre cette range.{note}")
    corriger(etat, eff, bonne, raison, f"Cotes : {cartes_poker(hero)} sur {cartes_poker(board)}")
    if etat.get('guide', True):
        print(f" Méthode : 1) il faut {mise} / {pot + 2 * mise} = {requis * 100:.0f} %."
              f" 2) tes outs : {txt_outs}")
        print(f"           3) équité réelle ≈ {e * 100:.0f} % contre cette range -> {bonne.lower()}.\n")


def drill_equite(etat):
    hero, board, nom_range, classes = generer_spot()
    e = equite(hero, board, classes)
    rue = "Flop" if len(board) == 3 else "Turn"
    print(f" {rue} : {cartes_poker(board)}")
    print(f" Ta main : {cartes_poker(hero)}")
    print(f" Contre la range d'ouverture {nom_range} (~{pourcentage(classes):.0f} %), ton équité jusqu'au river ?")
    n_outs, txt_outs = texte_outs(hero, board)
    aides = [f"d'abord, qu'as-tu déjà ? {nom_main(evaluer_7(hero + board))}. Une paire correcte vaut souvent 55 à 70 %.",
             f"compte tes outs : {txt_outs}",
             f"règle du {'4' if len(board) == 3 else '2'} : {n_outs} outs -> ≈ {estimation_regle(n_outs, board)} % de chances de toucher. "
             "Ajoute ce que ta main vaut déjà contre la range.",
             "repères : paire forte 60 à 80 %, tirage couleur ~35 %, deux surcartes ~25-30 %, rien 10-20 %."]
    while True:
        s = lire_aide("Équité en % (? = aide) > ", aides).replace('%', '').replace(',', '.')
        try:
            guess = float(s)
            break
        except ValueError:
            print(" Un nombre, par exemple 35")
    ok = abs(guess - e * 100) <= 6
    vrai = f"{e * 100:.0f} %"
    corriger(etat, vrai if ok else f"{guess:.0f} %", vrai,
             "Tu as droit à ±6 points. Astuce : outs x 4 au flop, outs x 2 au turn.",
             f"Équité : {cartes_poker(hero)} sur {cartes_poker(board)}")
    if etat.get('guide', True):
        print(f" Méthode : main actuelle {nom_main(evaluer_7(hero + board))}, tes outs : {txt_outs}")
        print(f"           tu avais répondu {guess:.0f} %, l'équité réelle est {e * 100:.0f} %.\n")


def generer_spot_outs():
    for _ in range(200):
        p = random.sample(paquet_complet(), 2 + 4)
        hero, board = p[:2], p[2:2 + random.choice([3, 4])]
        n = len(calcul_outs(hero, board))
        if 2 <= n <= 15:
            return hero, board
    return hero, board


def drill_outs(etat):
    hero, board = generer_spot_outs()
    rue = "Flop" if len(board) == 3 else "Turn"
    outs = calcul_outs(hero, board)
    n, txt = texte_outs(hero, board)
    print(f" {rue} : {cartes_poker(board)}")
    print(f" Ta main : {cartes_poker(hero)}  (actuellement : {nom_main(evaluer_7(hero + board))})")
    aides = ["un out = une carte qui améliore ta catégorie de main (paire, brelan, quinte, couleur...).",
             "tirage couleur = 9 outs, quinte ouverte = 8, quinte ventrale = 4, paire vers brelan = 2, "
             "deux surcartes = 6. Additionne sans compter deux fois la même carte.",
             "on ne compte pas une carte qui améliore seulement le board (par exemple une paire au board)."]
    while True:
        s = lire_aide("Combien d'outs as-tu ? (? = aide) > ", aides)
        try:
            guess = int(s)
            break
        except ValueError:
            print(" Un nombre entier, par exemple 9")
    ok = abs(guess - n) <= 1
    vrai = f"{n} outs"
    corriger(etat, vrai if ok else f"{guess} outs", vrai,
             f"Il y en a {txt} Tu as droit à ±1.",
             f"Outs : {cartes_poker(hero)} sur {cartes_poker(board)}")
    if etat.get('guide', True):
        print(f" Détail : {txt}")
        print(f" Chance de toucher ≈ {estimation_regle(n, board)} % "
              f"(règle du {'4' if len(board) == 3 else '2'}).\n")


MODES = {'1': ("Ouverture préflop par position", drill_ouverture),
         '2': ("Compter ses outs (le plus simple pour débuter)", drill_outs),
         '3': ("Cotes du pot : call ou fold", drill_cotes),
         '4': ("Estimer son équité (le plus dur)", drill_equite)}


def run_training_poker():
    print("\nEntraînement poker (Texas Hold'em, notation s h d c, As = A, Roi = K, Dame = Q, Valet = J, 10 = T)")
    print("Débutant : commence par le cours (c), puis les outs (2). Tape ? dans un exercice pour de l'aide.")
    print("Ranges de référence approximatives : modifie RANGES_RFI dans pp_poker.py pour tes propres tableaux.\n")
    etat = {'score': 0, 'total': 0, 'revoir': {}, 'guide': True}
    try:
        while True:
            for k, (nom, _) in MODES.items():
                print(f" {k}. {nom}")
            print(" 5. Mélange | c. Cours | g. Grille d'une range | a. Explications après chaque réponse "
                  f"({'oui' if etat.get('guide', True) else 'non'}) | q. Retour")
            print(" (dans chaque exercice, tape ? pour obtenir une aide progressive)")
            c = input("Mode > ").strip().lower()
            if c in ('q', 'quit', 'exit'):
                break
            if c == 'c':
                afficher_cours()
                continue
            if c == 'a':
                etat['guide'] = not etat.get('guide', True)
                print(" Explications après réponse :", "activées" if etat['guide'] else "désactivées")
                continue
            if c == 'g':
                p = input(f"Position {'/'.join(POSITIONS)} > ").strip().upper()
                if p in RANGE_SET:
                    afficher_grille(p)
                else:
                    print(" Position inconnue.")
                continue
            if c not in ('1', '2', '3', '4', '5'):
                continue
            print(" (q pour revenir au choix du mode)\n")
            while True:
                try:
                    f = MODES[c][1] if c in MODES else random.choice([m[1] for m in MODES.values()])
                    f(etat)
                except Quitter:
                    print()
                    break
    except Quitter:
        pass
    fin(etat, jeu=False)
    return etat

