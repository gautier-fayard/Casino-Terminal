import json
import os
import random
import time
from collections import deque
from itertools import combinations

# Rangs dans l'ordre (l'index sert pour les suites du 21+3)
RANGS = [('2', 2), ('3', 3), ('4', 4), ('5', 5), ('6', 6), ('7', 7), ('8', 8),
         ('9', 9), ('10', 10), ('V', 10), ('D', 10), ('R', 10), ('A', 11)]
CARTES = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]  # 11 = As (mode entraînement)

# Couleurs : p = pique, c = coeur, k = carreau, t = trèfle (ex : Rc = roi de coeur)
COULEURS = 'pckt'
ROUGES = 'ck'

DEPART = 1000
MAX_MAINS = 4
FENETRE_RECENTES = 50  # nombre de décisions récentes pour le pourcentage
PAUSE = 1.3  # secondes entre deux cartes de la banque
SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pp_save.json")


def pause():
    time.sleep(PAUSE)


# Paliers : (id, libellé, prime en jetons versée au déblocage)
PALIERS = [
    ("Débutant", [
        ('bj', "Faire un blackjack", 150),
        ('side', "Gagner un side bet au blackjack", 150),
        ('double', "Gagner une main doublée", 150),
        ('split', "Gagner une main après un split", 150),
        ('assurance5', "Refuser l'assurance 5 fois dans une session", 100),
        ('deux_jeux', "Jouer à deux jeux différents dans la même session", 100),
        ('serie10', "10 bonnes décisions d'affilée", 200),
        ('manches5', "Gagner 5 manches d'affilée", 250),
        ('jetons2000', "Atteindre 2 000 jetons", 200),
        ('poker_paire', "Poker : paire de valets ou mieux", 100),
        ('poker_double', "Poker : double paire ou mieux", 150),
        ('manches50', "Jouer 50 manches (au total)", 200),
        ('bonnes100', "100 bonnes décisions (au total)", 300),
    ]),
    ("Confirmé", [
        ('roul_plein', "Roulette : gagner un numéro seul", 400),
        ('roul_zero', "Roulette : toucher le 0 avec un pari dessus", 500),
        ('bac_egalite', "Baccara : gagner un pari Égalité", 400),
        ('bac_paire', "Baccara : gagner un pari Paire", 400),
        ('paire_parfaite', "Blackjack : toucher une paire parfaite (side bet)", 500),
        ('brelan', "Blackjack : toucher un brelan ou mieux au 21+3", 1000),
        ('trois_jeux', "Jouer à trois jeux différents dans la même session", 300),
        ('quatre_jeux', "Jouer aux quatre jeux dans la même session", 500),
        ('serie30', "30 bonnes décisions d'affilée", 1000),
        ('manches10', "Gagner 10 manches d'affilée", 1500),
        ('precision', "80 % de bonnes décisions sur 50 décisions (session)", 1000),
        ('jetons5000', "Atteindre 5 000 jetons", 500),
        ('jetons10000', "Atteindre 10 000 jetons", 1000),
        ('gain1k', "Gagner 1 000 jetons sur une seule manche", 1000),
        ('allin', "Miser tous ses jetons et gagner", 1000),
        ('remontada', "Remonter à 2 000 jetons après être tombé sous 300", 1500),
        ('poker_brelan', "Poker : brelan ou mieux", 200),
        ('poker_suite', "Poker : suite ou mieux", 300),
        ('poker_couleur', "Poker : couleur ou mieux", 400),
        ('poker_full', "Poker : full ou mieux", 800),
        ('manches250', "Jouer 250 manches (au total)", 1000),
        ('vic25', "Gagner 25 manches (au total)", 300),
        ('vic100', "Gagner 100 manches (au total)", 1000),
        ('bj10', "Faire 10 blackjacks (au total)", 800),
        ('bonnes500', "500 bonnes décisions (au total)", 1500),
        ('pleins3', "Roulette : gagner 3 numéros seuls (au total)", 1000),
        ('roul50', "Jouer 50 tours de roulette (au total)", 300),
        ('bac50', "Jouer 50 mains de baccara (au total)", 300),
        ('poker50', "Jouer 50 mains de poker (au total)", 300),
    ]),
    ("Expert", [
        ('serie50', "50 bonnes décisions d'affilée", 3000),
        ('precision90', "90 % de bonnes décisions sur 100 décisions (session)", 3000),
        ('jetons25k', "Atteindre 25 000 jetons", 2500),
        ('jetons50k', "Atteindre 50 000 jetons", 5000),
        ('gain5k', "Gagner 5 000 jetons sur une seule manche", 3000),
        ('brelan_couleur', "Blackjack : brelan de couleur au 21+3 (100:1)", 5000),
        ('poker_carre', "Poker : carré ou mieux", 2000),
        ('manches1000', "Jouer 1 000 manches (au total)", 5000),
        ('vic500', "Gagner 500 manches (au total)", 5000),
        ('bj50', "Faire 50 blackjacks (au total)", 3000),
        ('bonnes2000', "2 000 bonnes décisions (au total)", 7500),
        ('pleins10', "Roulette : gagner 10 numéros seuls (au total)", 5000),
        ('roul500', "Jouer 500 tours de roulette (au total)", 3000),
        ('bac500', "Jouer 500 mains de baccara (au total)", 3000),
        ('poker500', "Jouer 500 mains de poker (au total)", 3000),
    ]),
    ("Légende", [
        ('jetons100k', "Atteindre 100 000 jetons", 10000),
        ('jetons250k', "Atteindre 250 000 jetons", 25000),
        ('jetons500k', "Atteindre 500 000 jetons", 50000),
        ('jetons1m', "Atteindre 1 000 000 de jetons", 100000),
        ('gain25k', "Gagner 25 000 jetons sur une seule manche", 15000),
        ('gain100k', "Gagner 100 000 jetons sur une seule manche", 50000),
        ('serie100', "100 bonnes décisions d'affilée", 10000),
        ('manches20', "Gagner 20 manches d'affilée", 25000),
        ('manches5000', "Jouer 5 000 manches (au total)", 25000),
        ('vic2500', "Gagner 2 500 manches (au total)", 15000),
        ('bj200', "Faire 200 blackjacks (au total)", 15000),
        ('bonnes10000', "10 000 bonnes décisions (au total)", 40000),
        ('poker_sf', "Poker : quinte flush ou mieux", 10000),
        ('poker_royale', "Poker : quinte flush royale", 50000),
        ('platine', "Débloquer tous les autres objectifs", 200000),
    ]),
]
OBJECTIFS = [o for _, objs in PALIERS for o in objs]
LIBELLES = {c: l for c, l, _ in OBJECTIFS}
RECOMPENSES = {c: p for c, _, p in OBJECTIFS}

JALONS = ((2000, 'jetons2000'), (5000, 'jetons5000'), (10000, 'jetons10000'),
          (25000, 'jetons25k'), (50000, 'jetons50k'), (100000, 'jetons100k'),
          (250000, 'jetons250k'), (500000, 'jetons500k'), (1000000, 'jetons1m'))

# Compteurs cumulés entre les sessions : compteur -> [(seuil, objectif)]
CUMULS = {
    'manches': [(50, 'manches50'), (250, 'manches250'), (1000, 'manches1000'), (5000, 'manches5000')],
    'victoires': [(25, 'vic25'), (100, 'vic100'), (500, 'vic500'), (2500, 'vic2500')],
    'bj': [(10, 'bj10'), (50, 'bj50'), (200, 'bj200')],
    'bonnes': [(100, 'bonnes100'), (500, 'bonnes500'), (2000, 'bonnes2000'), (10000, 'bonnes10000')],
    'roulette': [(50, 'roul50'), (500, 'roul500')],
    'baccara': [(50, 'bac50'), (500, 'bac500')],
    'poker': [(50, 'poker50'), (500, 'poker500')],
    'pleins': [(3, 'pleins3'), (10, 'pleins10')],
}


def debloquer(etat, cle):
    """Débloque un objectif et verse sa prime (jeu avec jetons uniquement)."""
    if 'objectifs' not in etat or cle in etat['objectifs']:
        return
    etat['objectifs'].add(cle)
    etat['nouveaux'].append(cle)
    prime = RECOMPENSES[cle]
    etat['jetons'] += prime
    etat['bonus'] += prime
    print(f" Objectif atteint : {LIBELLES[cle]} (+{fmt(prime)} jetons)")
    if cle != 'platine' and len(etat['objectifs']) >= len(OBJECTIFS) - 1:
        debloquer(etat, 'platine')


def compter(etat, cle, n=1):
    """Compteur cumulé (sauvegardé) qui débloque des objectifs par seuils."""
    if 'cumul' not in etat:
        return
    etat['cumul'][cle] = etat['cumul'].get(cle, 0) + n
    for seuil, objectif in CUMULS.get(cle, ()):
        if etat['cumul'][cle] >= seuil:
            debloquer(etat, objectif)


class Quitter(Exception):
    pass


def fmt(x):
    x = round(x, 2)
    if x == int(x):
        return str(int(x))
    return f"{x:.2f}".rstrip('0').rstrip('.')


def lire_montant(texte, minimum=1):
    """'250', '10k' (10 000), '1.5k' ou '2m' (2 000 000) -> entier >= minimum, sinon None."""
    texte = texte.strip().lower().replace(',', '.')
    facteur = 1
    if texte.endswith('k'):
        facteur, texte = 1000, texte[:-1]
    elif texte.endswith('m'):
        facteur, texte = 1000000, texte[:-1]
    try:
        valeur = float(texte) * facteur
        entier = int(round(valeur))
    except (ValueError, OverflowError):
        return None
    if abs(valeur - entier) > 1e-9 or entier < minimum:
        return None
    return entier


def valeur(main):
    """Retourne (total, est_souple)."""
    total = sum(main)
    as_11 = main.count(11)
    while total > 21 and as_11:
        total -= 10
        as_11 -= 1
    return total, as_11 > 0


# ---------- Stratégie : chaque fonction retourne (action, raison) ----------
# dbl = le double est possible (2 cartes et assez de jetons)

def doubler(dbl, raison):
    if dbl:
        return 'double', raison
    return 'hit', "Double impossible ici, on tire."


def decision_paire(v, d, dbl):
    if v == 11:
        return 'split', "As-As : 12 ou deux mains à 11, on split toujours."
    if v == 8:
        return 'split', "16 est la pire main, deux 8 valent mieux."
    if v == 10:
        return 'stand', "20 est trop fort pour le casser."
    if v == 9:
        if d == 7:
            return 'stand', "18 bat le 17 probable de la banque."
        if d in (10, 11):
            return 'stand', "Banque forte : split perd plus que garder 18."
        return 'split', "Deux mains de 9 valent plus qu'un 18 battable."
    if v == 7:
        if d <= 7:
            return 'split', "14 est faible, banque <= 7 : on split."
        return 'hit', "Banque 8+ : split de 7 perd trop, on tire sur 14."
    if v == 6:
        if 3 <= d <= 6:
            return 'split', "Banque faible : on split pour l'exploiter."
        return 'hit', "12 se tire, split seulement contre 3-6."
    if v == 5:
        if d <= 9:
            return doubler(dbl, "C'est un 10 : on double tant que la banque n'a pas 10/As.")
        return 'hit', "Banque 10/As trop forte pour doubler un 10."
    if v == 4:
        if d in (5, 6):
            return 'split', "Banque très faible (5-6) : on split."
        return 'hit', "8 se tire, split seulement contre 5-6."
    # 2-2, 3-3
    if d <= 7:
        return 'split', "Banque <= 7 : split pour deux mains favorables."
    return 'hit', "Banque 8+ : pas de split, on tire."


def decision_souple(total, d, dbl):
    if total >= 19:
        return 'stand', f"Soft {total} est déjà très fort, on garde."
    if total == 18:
        if d in (2, 7, 8):
            return 'stand', "18 suffit contre cette banque."
        if 3 <= d <= 6:
            if dbl:
                return 'double', "Banque faible, pas de risque de bust : on double."
            return 'stand', "Double impossible ici : 18 contre banque faible, on garde."
        return 'hit', "18 est battu trop souvent par 9, 10, As : on tire sans risque de bust."
    # soft 12 à 17
    seuil = {2: 5, 3: 5, 4: 4, 5: 4, 6: 3}.get(total - 11)
    if dbl and seuil is not None:
        if seuil <= d <= 6:
            return 'double', "Banque faible, l'As t'évite le bust : on double."
        return 'hit', f"Double seulement contre {seuil}-6, sinon on tire sans risque."
    return 'hit', "Aucun risque de bust, main trop faible pour rester."


def decision_dure(total, d, dbl):
    if total >= 17:
        return 'stand', "17+ : tirer risque trop de bust."
    if total <= 8:
        return 'hit', "8 ou moins : aucun risque de bust, on tire."
    if total == 9:
        if 3 <= d <= 6:
            return doubler(dbl, "Banque faible : 9 devient souvent 19, on double.")
        return 'hit', "Banque hors 3-6 : double trop risqué, on tire."
    if total == 10:
        if d <= 9:
            return doubler(dbl, "10 + figure = 20 : on double sauf contre 10/As.")
        return 'hit', "Banque 10/As trop forte pour doubler."
    if total == 11:
        if d <= 10:
            return doubler(dbl, "11 + figure = 21 : on double.")
        return 'hit', "Banque As : trop dangereux de doubler."
    if total == 12:
        if 4 <= d <= 6:
            return 'stand', "Banque 4-6 : elle bust souvent, on la laisse faire."
        return 'hit', "12 est trop faible contre cette banque."
    # 13 à 16
    if d <= 6:
        return 'stand', "Banque faible : elle bust souvent, on ne prend pas le risque."
    return 'hit', "Banque forte (7+) : rester perd presque toujours, on tire."


def decision(main, d, dbl, spl):
    total, soft = valeur(main)
    if len(main) == 2 and main[0] == main[1] and spl:
        return decision_paire(main[0], d, dbl)
    if soft:
        return decision_souple(total, d, dbl)
    return decision_dure(total, d, dbl)


# ---------- Affichage et saisie ----------

CMD = {
    'h': 'hit', 'hit': 'hit',
    's': 'stand', 'stand': 'stand',
    'd': 'double', 'double': 'double',
    'sp': 'split', 'split': 'split',
}


def decrire(vals, noms):
    total, soft = valeur(vals)
    cartes = " + ".join(noms)
    if len(vals) == 2 and vals[0] == vals[1]:
        return f"Paire : {cartes}"
    if soft:
        return f"Soft {total} ({cartes})"
    return f"Total {total} ({cartes})"


# Une carte du jeu = (valeur, libellé, index du rang, couleur), ex : (10, 'Rc', 11, 'c')

def vals_de(h):
    return [c[0] for c in h['cartes']]


def noms_de(h):
    return [c[1] for c in h['cartes']]


def demander_action(dbl, spl):
    while True:
        saisie = input("Ta décision ? > ").strip().lower()
        if saisie in ('q', 'quit', 'exit'):
            raise Quitter
        action = CMD.get(saisie)
        if not action:
            print(" h, s, d, sp ou q")
            continue
        if action == 'double' and not dbl:
            print(" Double impossible ici.")
            continue
        if action == 'split' and not spl:
            print(" Split impossible ici.")
            continue
        return action


def corriger(etat, action, bonne, raison, situation):
    etat['total'] += 1
    recents = etat.setdefault('recents', [])
    recents.append(action == bonne)
    del recents[:-FENETRE_RECENTES]
    if action == bonne:
        etat['score'] += 1
        print(f" EXACT ({bonne.upper()})\n")
    else:
        print(f" FAUX ({action.upper()}), bonne décision : {bonne.upper()}")
        print(f" {raison}\n")
        etat['revoir'][situation] = bonne
    if action == bonne:
        etat['serie_ok'] = etat.get('serie_ok', 0) + 1
        etat['meilleure_serie_ok'] = max(etat.get('meilleure_serie_ok', 0), etat['serie_ok'])
        compter(etat, 'bonnes')
        for n, cle in ((10, 'serie10'), (30, 'serie30'), (50, 'serie50'), (100, 'serie100')):
            if etat['serie_ok'] >= n:
                debloquer(etat, cle)
    else:
        etat['serie_ok'] = 0


def courbe(hist, largeur=60, hauteur=8):
    n = len(hist)
    if n < 2:
        return
    if n > largeur:
        pts = [hist[int(i * (n - 1) / (largeur - 1))] for i in range(largeur)]
    else:
        pts = hist
    bas, haut = min(pts), max(pts)
    if haut == bas:
        haut = bas + 1
    lignes = [[' '] * len(pts) for _ in range(hauteur)]
    for x, v in enumerate(pts):
        y = int((v - bas) / (haut - bas) * (hauteur - 1))
        lignes[hauteur - 1 - y][x] = '*'
    larg = max(len(fmt(haut)), len(fmt(bas)))
    for r, ligne in enumerate(lignes):
        if r == 0:
            etiquette = fmt(haut)
        elif r == hauteur - 1:
            etiquette = fmt(bas)
        else:
            etiquette = ''
        print(f"  {etiquette:>{larg}} |{''.join(ligne)}")


def afficher_session(etat):
    print(f"Série de bonnes décisions : {etat.get('serie_ok', 0)} "
          f"(meilleure : {etat.get('meilleure_serie_ok', 0)})")
    s = etat['stats']
    if not s['manches']:
        return
    print(f"Manches : {s['manches']} ({s['gagnees']} gagnées, {s['perdues']} perdues, "
          f"{s['egalites']} égalités)")
    print(f"Meilleure série de manches : {s['meilleure_serie']} | "
          f"Plus gros gain : +{fmt(s['gain_max'])} | Plus grosse perte : {fmt(s['perte_max'])}")
    print()
    courbe(s['hist'])


def afficher_stats(etat):
    """Stats en cours de partie (commande st à la mise)."""
    total, score = etat['total'], etat['score']
    pct = score / total * 100 if total else 0
    print()
    print(f"Jetons : {fmt(etat['jetons'])} | Record : {fmt(etat['record'])}")
    print(f"Décisions : {score}/{total} ({pct:.0f}%) | Bonnes au total : {etat['cumul'].get('bonnes', 0)}")
    recents = etat['recents']
    if recents:
        print(f"{len(recents)} dernières décisions : {sum(recents) * 100 // len(recents)} %")
    print(f"Victoires d'affilée : {etat['stats']['serie']} (record {etat['stats']['meilleure_serie']})")
    afficher_session(etat)
    afficher_progression(etat)
    print()


def fin(etat, jeu):
    total, score = etat['total'], etat['score']
    pct = score / total * 100 if total else 0
    if jeu:
        print(f"\nJetons : {fmt(etat['jetons'])} (départ {DEPART}) | Record : {fmt(etat['record'])}")
    else:
        print()
    print(f"Décisions : {score}/{total} ({pct:.0f}%)")
    if jeu:
        afficher_session(etat)
    if jeu:
        if etat['nouveaux']:
            print("Objectifs atteints : " + ", ".join(LIBELLES[c] for c in etat['nouveaux']))
        if etat['bonus']:
            print(f"Primes d'objectifs : +{fmt(etat['bonus'])} jetons")
        print(f"Objectifs : {len(etat['objectifs'])}/{len(OBJECTIFS)}")
    if etat['revoir']:
        print("À revoir :")
        for situation, action in etat['revoir'].items():
            print(f"  {situation} -> {action.upper()}")
    print()


# ====================== MODE JEU (jetons) ======================

def nouveau_sabot(jeux=6):
    sabot = [(v, r + s, i, s)
             for _ in range(jeux)
             for i, (r, v) in enumerate(RANGS)
             for s in COULEURS]
    random.shuffle(sabot)
    return sabot


def tirer(etat):
    return etat['sabot'].pop()


def charger():
    try:
        with open(SAVE, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def sauver(etat):
    try:
        with open(SAVE, 'w', encoding='utf-8') as f:
            json.dump({'jetons': etat['jetons'], 'record': etat['record'],
                       'objectifs': sorted(etat['objectifs']), 'cumul': etat['cumul'],
                       'hist_roulette': etat['hist_roulette'], 'recents': etat['recents'],
                       'serie_ok': etat.get('serie_ok', 0),
                       'meilleure_serie_ok': etat.get('meilleure_serie_ok', 0)}, f)
    except OSError:
        pass


def demander_mise(etat):
    jetons = etat['jetons']
    defaut = min(etat['derniere'], int(jetons))
    invite = f"Mise (1-{int(jetons)}"
    if defaut >= 1:
        invite += f", Entrée = {defaut}, x = {defaut * 2}, / = {max(1, defaut // 2)}"
    invite += ", st = stats, j = jeu, q) > "
    while True:
        saisie = input(invite).strip().lower()
        if saisie in ('q', 'quit', 'exit'):
            raise Quitter
        if saisie in ('st', 'stats'):
            afficher_stats(etat)
            return None
        if saisie in ('j', 'jeu'):
            changer_jeu(etat)
            return None
        if saisie in ('ob', 'objectifs'):
            afficher_objectifs(etat['objectifs'])
            return None
        if saisie in ('x', '2x'):
            if defaut < 1:
                print(" Aucune mise précédente.")
                continue
            if defaut * 2 > jetons:
                print(" Pas assez de jetons pour doubler.")
                continue
            return defaut * 2
        if saisie in ('/', '/2'):
            if defaut < 1:
                print(" Aucune mise précédente.")
                continue
            return max(1, defaut // 2)
        if saisie == '':
            if defaut >= 1:
                return defaut
            print(" Mise requise.")
            continue
        mise = lire_montant(saisie)
        if mise is None:
            print(" Montant invalide (ex : 250, 10k).")
            continue
        if mise <= jetons:
            return mise
        print(" Mise invalide.")


def demander_side(etat, mise):
    """Side bets : une ligne 'Paires 21+3' (ex : 20 20). Retourne {'p': x, 't': y}."""
    libre = etat['jetons'] - mise
    if libre < 1:
        return {'p': 0, 't': 0}
    dernier = etat['dernier_side']
    if dernier['p'] or dernier['t']:
        defaut = f"{dernier['p']} {dernier['t']}"
    else:
        defaut = "non"
    invite = f"Side bets Paires 21+3 (ex : 20 20, 0 20, Entrée = {defaut}, x = double, / = moitié, n = non) > "
    while True:
        saisie = input(invite).strip().lower()
        if saisie in ('q', 'quit', 'exit'):
            raise Quitter
        if saisie == '':
            side = dict(dernier)
        elif saisie == 'x':
            side = {k: v * 2 for k, v in dernier.items()}
        elif saisie in ('/', '/2'):
            side = {k: v // 2 for k, v in dernier.items()}
        elif saisie in ('n', 'non'):
            side = {'p': 0, 't': 0}
        else:
            tokens = saisie.split()
            valeurs = [lire_montant(t, 0) for t in tokens]
            if not (1 <= len(tokens) <= 2) or None in valeurs:
                print(" Format : 20 20 (Paires puis 21+3), 0 20, 10k ou n")
                continue
            side = {'p': valeurs[0], 't': valeurs[1] if len(valeurs) == 2 else 0}
        if side['p'] + side['t'] > libre:
            print(" Pas assez de jetons.")
            continue
        etat['dernier_side'] = dict(side)
        return side


def gain_paires(c1, c2):
    if c1[2] != c2[2]:
        return None
    if c1[3] == c2[3]:
        return "paire parfaite", 25
    if (c1[3] in ROUGES) == (c2[3] in ROUGES):
        return "paire de couleur", 12
    return "paire mixte", 6


def gain_21_3(cartes):
    rangs = sorted(c[2] for c in cartes)
    meme_couleur = len({c[3] for c in cartes}) == 1
    brelan = rangs[0] == rangs[2]
    suite = len(set(rangs)) == 3 and (rangs[2] - rangs[0] == 2 or rangs == [0, 1, 12])
    if brelan and meme_couleur:
        return "brelan de couleur", 100
    if suite and meme_couleur:
        return "suite de couleur", 40
    if brelan:
        return "brelan", 30
    if suite:
        return "suite", 10
    if meme_couleur:
        return "couleur", 5
    return None


def regler_side(etat, side, c1, c2, u):
    if side['p']:
        r = gain_paires(c1, c2)
        if r:
            nom_, cote = r
            gain = side['p'] * cote
            etat['jetons'] += side['p'] + gain
            print(f" Paires : {nom_} ({c1[1]} + {c2[1]}) +{fmt(gain)}")
            debloquer(etat, 'side')
            if nom_ == 'paire parfaite':
                debloquer(etat, 'paire_parfaite')
        else:
            print(f" Paires : perdu -{fmt(side['p'])}")
    if side['t']:
        r = gain_21_3([c1, c2, u])
        if r:
            nom_, cote = r
            gain = side['t'] * cote
            etat['jetons'] += side['t'] + gain
            print(f" 21+3 : {nom_} ({c1[1]} + {c2[1]} + {u[1]}) +{fmt(gain)}")
            debloquer(etat, 'side')
            if cote >= 30:
                debloquer(etat, 'brelan')
            if cote >= 100:
                debloquer(etat, 'brelan_couleur')
        else:
            print(f" 21+3 : perdu -{fmt(side['t'])}")


def proposer_assurance(etat, mise, c1, c2, u):
    """Retourne la mise d'assurance prise (0 si refusée)."""
    cout = mise / 2
    if etat['jetons'] < cout:
        return 0
    print(f" Ta main : {decrire([c1[0], c2[0]], [c1[1], c2[1]])}")
    print(f" Banque  : {u[1]}")
    while True:
        saisie = input("Assurance ? (o/n, Entrée = non) > ").strip().lower()
        if saisie in ('', 'n', 'non'):
            action = 'refuser'
            break
        if saisie in ('o', 'oui'):
            action = 'assurer'
            break
        print(" o ou n")
    corriger(etat, action, 'refuser',
             "Pari perdant : la banque n'a un 10 que ~31 % du temps, il en faudrait 33 %.",
             "Banque As : assurance")
    if action == 'assurer':
        etat['jetons'] -= cout
        return cout
    etat['refus_assurance'] = etat.get('refus_assurance', 0) + 1
    if etat['refus_assurance'] >= 5:
        debloquer(etat, 'assurance5')
    return 0


def jouer_main(etat, mains, i, up, d_nom):
    h = mains[i]
    while True:
        vals, noms = vals_de(h), noms_de(h)
        total, _ = valeur(vals)
        if h['fini'] or total >= 21:
            return

        deux = len(vals) == 2
        dbl = deux and etat['jetons'] >= h['mise']
        spl = (deux and vals[0] == vals[1] and etat['jetons'] >= h['mise']
               and len(mains) < MAX_MAINS)
        bonne, raison = decision(vals, up, dbl, spl)
        description = decrire(vals, noms)

        label = f"Main {i + 1}/{len(mains)} | " if len(mains) > 1 else ""
        print(f" {label}Mise {fmt(h['mise'])}")
        print(f" Ta main : {description}")
        print(f" Banque  : {d_nom}")

        action = demander_action(dbl, spl)
        corriger(etat, action, bonne, raison, f"{description} vs {d_nom}")

        if action == 'stand':
            h['fini'] = True
            return

        if action == 'hit':
            h['cartes'].append(tirer(etat))
            t, _ = valeur(vals_de(h))
            if t > 21:
                print(f" Bust ({t})\n")
            elif t == 21:
                print(" 21\n")

        elif action == 'double':
            etat['jetons'] -= h['mise']
            h['mise'] *= 2
            h['doublee'] = True
            h['cartes'].append(tirer(etat))
            h['fini'] = True
            t, _ = valeur(vals_de(h))
            suite = " Bust" if t > 21 else ""
            print(f" Double : {decrire(vals_de(h), noms_de(h))}{suite}\n")
            return

        elif action == 'split':
            c1, c2 = h['cartes']
            etat['jetons'] -= h['mise']
            sur_as = c1[0] == 11
            h['cartes'] = [c1, tirer(etat)]
            h['fini'] = sur_as
            mains.insert(i + 1, {'cartes': [c2, tirer(etat)], 'mise': h['mise'], 'fini': sur_as})
            if sur_as:
                print(" Split d'As : une seule carte par main.\n")
                return


def jouer_manche(etat, mise, side):
    if len(etat['sabot']) < 78:
        etat['sabot'] = nouveau_sabot()
        print(" Sabot remélangé.")

    etat['jetons'] -= mise + side['p'] + side['t']
    c1 = tirer(etat)
    u = tirer(etat)
    c2 = tirer(etat)
    cache = tirer(etat)

    mains = [{'cartes': [c1, c2], 'mise': mise, 'fini': False}]
    dealer = [u, cache]
    up, d_nom = u[0], u[1]

    regler_side(etat, side, c1, c2, u)

    # Assurance si la banque montre un As
    assurance = proposer_assurance(etat, mise, c1, c2, u) if up == 11 else 0

    # Blackjacks (la banque regarde sa carte cachée avec 10 ou As)
    p_bj = valeur([c1[0], c2[0]])[0] == 21
    d_bj = up in (10, 11) and valeur([u[0], cache[0]])[0] == 21

    if assurance:
        if d_bj:
            etat['jetons'] += assurance * 3
            print(f" Assurance : +{fmt(assurance * 2)}")
        else:
            print(f" Assurance : perdue -{fmt(assurance)}")

    if p_bj or d_bj:
        print(f" Ta main : {'Blackjack ' if p_bj else ''}({c1[1]} + {c2[1]})")
        print(f" Banque  : {u[1]} + {cache[1]}")
        if p_bj and d_bj:
            etat['jetons'] += mise
            print(" Blackjack partout. Égalité.")
        elif p_bj:
            gain = mise * 1.5
            etat['jetons'] += mise + gain
            print(f" Blackjack ! +{fmt(gain)}")
            debloquer(etat, 'bj')
            compter(etat, 'bj')
        else:
            print(f" Blackjack de la banque. -{fmt(mise)}")
        print(f" Jetons : {fmt(etat['jetons'])}\n")
        return

    # Tour du joueur (si on quitte en cours de main, les mises sont rendues)
    try:
        i = 0
        while i < len(mains):
            jouer_main(etat, mains, i, up, d_nom)
            i += 1
    except Quitter:
        etat['jetons'] += sum(h['mise'] for h in mains)
        raise

    # Tour de la banque
    dv = [c[0] for c in dealer]
    print(f" Banque : {dealer[0][1]}", end="", flush=True)
    pause()
    print(f" + {dealer[1][1]}", end="", flush=True)
    if any(valeur(vals_de(h))[0] <= 21 for h in mains):
        while valeur(dv)[0] < 17:
            pause()
            c = tirer(etat)
            dealer.append(c)
            dv.append(c[0])
            print(f" + {c[1]}", end="", flush=True)
    pause()
    dt, _ = valeur(dv)
    suite = " (bust)" if dt > 21 else ""
    print(f" = {dt}{suite}")

    # Résultats
    for k, h in enumerate(mains):
        t, _ = valeur(vals_de(h))
        m = h['mise']
        if t > 21:
            texte = f"Perdu -{fmt(m)}"
        elif dt > 21 or t > dt:
            etat['jetons'] += 2 * m
            texte = f"Gagné +{fmt(m)}"
        elif t == dt:
            etat['jetons'] += m
            texte = "Égalité"
        else:
            texte = f"Perdu -{fmt(m)}"
        label = f"Main {k + 1} ({t}) : " if len(mains) > 1 else ""
        print(f" {label}{texte}")
        if texte.startswith("Gagné"):
            if h.get('doublee'):
                debloquer(etat, 'double')
            if len(mains) > 1:
                debloquer(etat, 'split')
    print(f" Jetons : {fmt(etat['jetons'])}\n")


# ====================== BACCARA ======================

NOMS_JEUX = {'blackjack': 'Blackjack', 'baccara': 'Baccara', 'roulette': 'Roulette', 'poker': 'Video poker'}


def changer_jeu(etat):
    while True:
        saisie = input(f"Jeu : 1 = Blackjack, 2 = Baccara, 3 = Roulette, 4 = Video poker "
                       f"(Entrée = {NOMS_JEUX[etat['jeu']]}) > ").strip().lower()
        if saisie in ('q', 'quit', 'exit'):
            raise Quitter
        if saisie == '':
            break
        if saisie in ('1', 'blackjack', 'bj'):
            etat['jeu'] = 'blackjack'
            break
        if saisie in ('2', 'baccara', 'bac'):
            etat['jeu'] = 'baccara'
            break
        if saisie in ('3', 'roulette', 'roul'):
            etat['jeu'] = 'roulette'
            break
        if saisie in ('4', 'poker', 'video poker'):
            etat['jeu'] = 'poker'
            break
        print(" 1, 2, 3 ou 4")
    if etat['jeu'] == 'baccara':
        print(" Paiements : Joueur 1:1, Banquier 0.95:1, Égalité 8:1, Paires 11:1")
    if etat['jeu'] == 'roulette':
        print(" Roulette européenne (La Partage sur le 0). ? = aide, h = historique.")
    if etat['jeu'] == 'poker':
        print(" Jacks or Better. Gains (x la mise) : royale 800, quinte flush 50, carré 25, full 9,")
        print(" couleur 6, suite 4, brelan 3, double paire 2, valets ou mieux 1.")
        print(" Tu choisis les cartes à garder (positions 1 à 5, de gauche à droite), le jeu corrige ton choix.")
    print()


def bac_valeur(carte):
    v = carte[0]
    if v == 11:
        return 1
    return 0 if v == 10 else v


def bac_total(cartes):
    return sum(bac_valeur(c) for c in cartes) % 10


def banquier_tire(tb, p3):
    """p3 = valeur baccara de la 3e carte du joueur (None s'il est resté)."""
    if p3 is None:
        return tb <= 5
    if tb <= 2:
        return True
    if tb == 3:
        return p3 != 8
    if tb == 4:
        return 2 <= p3 <= 7
    if tb == 5:
        return 4 <= p3 <= 7
    if tb == 6:
        return p3 in (6, 7)
    return False


def demander_pari(etat):
    defaut = etat['dernier_pari']
    while True:
        saisie = input(f"Pari (j = Joueur, b = Banquier, Entrée = {defaut}) > ").strip().lower()
        if saisie in ('q', 'quit', 'exit'):
            raise Quitter
        if saisie == '':
            pari = defaut
        elif saisie in ('j', 'joueur'):
            pari = 'joueur'
        elif saisie in ('b', 'banquier'):
            pari = 'banquier'
        else:
            print(" j ou b")
            continue
        break
    etat['dernier_pari'] = pari
    return pari


def demander_side_bac(etat, mise):
    """Side bets baccara : 'Égalité PaireJoueur PaireBanquier' (ex : 10 0 5)."""
    cles = ('e', 'pj', 'pb')
    libre = etat['jetons'] - mise
    if libre < 1:
        return {k: 0 for k in cles}
    dernier = etat['dernier_side_bac']
    defaut = " ".join(str(dernier[k]) for k in cles) if any(dernier.values()) else "non"
    invite = f"Side bets Égalité PaireJ PaireB (ex : 10 0 5, Entrée = {defaut}, x = double, / = moitié, n = non) > "
    while True:
        saisie = input(invite).strip().lower()
        if saisie in ('q', 'quit', 'exit'):
            raise Quitter
        if saisie == '':
            side = dict(dernier)
        elif saisie == 'x':
            side = {k: v * 2 for k, v in dernier.items()}
        elif saisie in ('/', '/2'):
            side = {k: v // 2 for k, v in dernier.items()}
        elif saisie in ('n', 'non'):
            side = {k: 0 for k in cles}
        else:
            tokens = saisie.split()
            valeurs = [lire_montant(t, 0) for t in tokens]
            if not (1 <= len(tokens) <= 3) or None in valeurs:
                print(" Format : 10 0 5 (Égalité, Paire Joueur, Paire Banquier), 10k ou n")
                continue
            side = {k: 0 for k in cles}
            for k, v in zip(cles, valeurs):
                side[k] = v
        if sum(side.values()) > libre:
            print(" Pas assez de jetons.")
            continue
        etat['dernier_side_bac'] = dict(side)
        return side


def jouer_baccara(etat, mise, pari, side):
    if len(etat['sabot_bac']) < 52:
        etat['sabot_bac'] = nouveau_sabot(8)
        print(" Sabot remélangé.")
    sabot = etat['sabot_bac']

    etat['jetons'] -= mise + sum(side.values())
    j = [sabot.pop()]
    b = [sabot.pop()]
    j.append(sabot.pop())
    b.append(sabot.pop())
    tj, tb = bac_total(j), bac_total(b)

    pause()
    print(f" Joueur   : {j[0][1]} + {j[1][1]} = {tj}{' (naturel)' if tj >= 8 else ''}")
    pause()
    print(f" Banquier : {b[0][1]} + {b[1][1]} = {tb}{' (naturel)' if tb >= 8 else ''}")

    if tj < 8 and tb < 8:
        p3 = None
        if tj <= 5:
            carte = sabot.pop()
            j.append(carte)
            p3 = bac_valeur(carte)
            tj = bac_total(j)
            pause()
            print(f" Joueur tire   : {carte[1]} -> {tj}")
        if banquier_tire(tb, p3):
            carte = sabot.pop()
            b.append(carte)
            tb = bac_total(b)
            pause()
            print(f" Banquier tire : {carte[1]} -> {tb}")

    pause()
    if tj > tb:
        print(f" Joueur gagne {tj} contre {tb}")
    elif tb > tj:
        print(f" Banquier gagne {tb} contre {tj}")
    else:
        print(f" Égalité {tj}")

    # Pari principal
    if tj == tb:
        etat['jetons'] += mise
        print(" Pari principal : mise rendue")
    elif (tj > tb) == (pari == 'joueur'):
        gain = mise if pari == 'joueur' else round(mise * 0.95, 2)
        etat['jetons'] += mise + gain
        print(f" {pari.capitalize()} : +{fmt(gain)}")
    else:
        print(f" {pari.capitalize()} : perdu -{fmt(mise)}")

    # Side bets
    if side['e']:
        if tj == tb:
            gain = side['e'] * 8
            etat['jetons'] += side['e'] + gain
            print(f" Égalité : +{fmt(gain)}")
            debloquer(etat, 'bac_egalite')
        else:
            print(f" Égalité : perdu -{fmt(side['e'])}")
    for cle, cartes, libelle in (('pj', j, 'Paire Joueur'), ('pb', b, 'Paire Banquier')):
        if side[cle]:
            if cartes[0][2] == cartes[1][2]:
                gain = side[cle] * 11
                etat['jetons'] += side[cle] + gain
                print(f" {libelle} : +{fmt(gain)}")
                debloquer(etat, 'bac_paire')
            else:
                print(f" {libelle} : perdu -{fmt(side[cle])}")

    etat['jetons'] = round(etat['jetons'], 2)
    print(f" Jetons : {fmt(etat['jetons'])}")
    print()


# ====================== VIDEO POKER ======================
# Jacks or Better 9/6. Table de garde simplifiée : les cas limites (petits tirages)
# acceptent plusieurs choix proches.

GAINS_POKER = {
    'quinte flush royale': 800, 'quinte flush': 50, 'carré': 25, 'full': 9,
    'couleur': 6, 'suite': 4, 'brelan': 3, 'double paire': 2,
    'paire de valets ou mieux': 1, 'rien': 0,
}
OBJECTIFS_POKER = ((1, 'poker_paire'), (2, 'poker_double'), (3, 'poker_brelan'),
                   (4, 'poker_suite'), (6, 'poker_couleur'), (9, 'poker_full'),
                   (25, 'poker_carre'), (50, 'poker_sf'), (800, 'poker_royale'))


def rang(c):
    return c[2] + 2  # 2..14 (As = 14)


def evaluer_poker(cartes):
    rangs = sorted(rang(c) for c in cartes)
    meme_couleur = len({c[3] for c in cartes}) == 1
    freq = sorted((rangs.count(x) for x in set(rangs)), reverse=True)
    suite = len(set(rangs)) == 5 and (rangs[4] - rangs[0] == 4 or rangs == [2, 3, 4, 5, 14])
    if suite and meme_couleur:
        return 'quinte flush royale' if rangs == [10, 11, 12, 13, 14] else 'quinte flush'
    if freq[0] == 4:
        return 'carré'
    if freq == [3, 2]:
        return 'full'
    if meme_couleur:
        return 'couleur'
    if suite:
        return 'suite'
    if freq[0] == 3:
        return 'brelan'
    if freq[:2] == [2, 2]:
        return 'double paire'
    if freq[0] == 2:
        paire = [x for x in set(rangs) if rangs.count(x) == 2][0]
        return 'paire de valets ou mieux' if paire >= 11 else 'rien'
    return 'rien'


def dans_une_quinte(rangs):
    """Ces rangs (distincts) tiennent-ils dans une même quinte ? (l'As compte haut ou bas)"""
    for r in (rangs, [1 if x == 14 else x for x in rangs]):
        if max(r) - min(r) <= 4:
            return True
    return False


def garde_poker(cartes):
    """Retourne (garde, raison, alternatives) : garde = positions (0-4) à garder."""
    idx = range(5)
    r = [rang(c) for c in cartes]
    s = [c[3] for c in cartes]
    main = evaluer_poker(cartes)
    tout = frozenset(idx)
    par_rang = {}
    for i in idx:
        par_rang.setdefault(r[i], []).append(i)
    paires = [g for g in par_rang.values() if len(g) == 2]
    hautes = [i for i in idx if r[i] >= 11]
    groupes = {c: [i for i in idx if s[i] == c] for c in set(s)}

    if main in ('quinte flush royale', 'quinte flush', 'carré'):
        return tout, "Main faite : on garde tout.", []
    for g in groupes.values():
        royales = [i for i in g if r[i] >= 10]
        if len(royales) == 4:
            return frozenset(royales), "4 cartes à la quinte flush royale : le gros lot est à une carte.", []
    if main in ('full', 'couleur', 'suite'):
        return tout, "Main faite : on garde tout.", []
    if main == 'brelan':
        trio = [g for g in par_rang.values() if len(g) == 3][0]
        return frozenset(trio), "Brelan : on garde les 3 et on tire 2 cartes (carré ou full possibles).", []
    for g in groupes.values():
        if len(g) == 4 and dans_une_quinte([r[i] for i in g]):
            return frozenset(g), "4 cartes à la quinte flush : on tente.", []
    if main == 'double paire':
        deux = [i for g in paires for i in g]
        return frozenset(deux), "Double paire : on garde les deux paires (un full est possible).", []
    if paires and r[paires[0][0]] >= 11:
        return frozenset(paires[0]), "Paire de valets ou mieux : elle paie déjà, on la garde.", []
    for g in groupes.values():
        royales = [i for i in g if r[i] >= 10]
        if len(royales) == 3:
            return frozenset(royales), "3 cartes à la quinte flush royale.", []
    for g in groupes.values():
        if len(g) == 4:
            return frozenset(g), "4 cartes à la couleur : 9 cartes la complètent.", []
    if {10, 11, 12, 13} <= set(r):
        garde = [par_rang[x][0] for x in (10, 11, 12, 13)]
        return frozenset(garde), "10-V-D-R : 8 cartes pour la suite, toutes hautes.", []
    if paires:
        return frozenset(paires[0]), "Petite paire : on tente le brelan plutôt que des cartes seules.", []
    for debut in range(2, 11):
        quatre = list(range(debut, debut + 4))
        if set(quatre) <= set(r):
            garde = [par_rang[x][0] for x in quatre]
            return frozenset(garde), "4 cartes à une suite ouverte : 8 cartes la complètent.", []

    # Mains faibles : plusieurs choix proches, le premier est le préféré
    candidats = []
    meilleur = None
    for g in groupes.values():
        for sous in combinations(g, 3):
            if dans_une_quinte([r[i] for i in sous]):
                nb = sum(1 for i in sous if r[i] >= 11)
                if meilleur is None or nb > meilleur[0]:
                    meilleur = (nb, sous)
    if meilleur:
        candidats.append((frozenset(meilleur[1]),
                          "3 cartes à la quinte flush : suite, couleur ou quinte flush possibles."))
    milieu = {}
    for sous in combinations(idx, 4):
        if dans_une_quinte([r[i] for i in sous]):
            nb = sum(1 for i in sous if r[i] >= 11)
            if nb >= 1:
                milieu.setdefault(min(nb, 3), sous)
    if 3 in milieu:
        candidats.append((frozenset(milieu[3]), "Suite par le milieu avec 3 cartes hautes."))
    for sous in combinations(hautes, 2):
        if s[sous[0]] == s[sous[1]]:
            candidats.append((frozenset(sous),
                              "Deux cartes hautes de même couleur : paire, couleur ou royale possibles."))
            break
    if 2 in milieu:
        candidats.append((frozenset(milieu[2]), "Suite par le milieu avec 2 cartes hautes."))
    if 1 in milieu:
        candidats.append((frozenset(milieu[1]), "Suite par le milieu avec 1 carte haute."))
    if len(hautes) >= 2:
        triees = sorted(hautes, key=lambda i: r[i])
        if r[triees[1]] == 14:
            candidats.append((frozenset(triees[:1]), "Une carte haute : on la garde et on tire 4 cartes."))
        else:
            candidats.append((frozenset(triees[:2]),
                              "Deux cartes hautes : une paire de valets ou mieux est possible."))
    elif len(hautes) == 1:
        candidats.append((frozenset(hautes), "Une carte haute : on la garde et on tire 4 cartes."))
    candidats.append((frozenset(), "Rien d'intéressant : on jette tout et on retire 5 cartes."))
    alternatives = [g for g, _ in candidats[1:] if g]
    return candidats[0][0], candidats[0][1], alternatives


def libelle_garde(garde):
    if not garde:
        return "tout jeter"
    if len(garde) == 5:
        return "tout garder"
    return "garder " + " ".join(str(i + 1) for i in sorted(garde))


def demander_garde():
    while True:
        saisie = input("Garder ? (ex : 1 3 5, t = tout, 0 = rien, q) > ").strip().lower()
        if saisie in ('q', 'quit', 'exit'):
            raise Quitter
        if saisie in ('t', 'tout'):
            return frozenset(range(5))
        if saisie in ('0', 'n', 'rien'):
            return frozenset()
        tokens = saisie.replace(',', ' ').split()
        if len(tokens) == 1 and len(tokens[0]) > 1:
            tokens = list(tokens[0])
        if tokens and all(t in ('1', '2', '3', '4', '5') for t in tokens) and len(set(tokens)) == len(tokens):
            return frozenset(int(t) - 1 for t in tokens)
        print(" Positions de 1 à 5 (ex : 1 3 5), t ou 0.")


def jouer_poker(etat, mise):
    paquet = nouveau_sabot(1)
    cartes = [paquet.pop() for _ in range(5)]
    print(" " + "  ".join(f"{c[1]:<3}" for c in cartes))
    garde = demander_garde()
    etat['jetons'] -= mise

    ideal, raison, alternatives = garde_poker(cartes)
    choix, bonne = libelle_garde(garde), libelle_garde(ideal)
    proche = garde != ideal and garde in alternatives
    corriger(etat, choix, choix if proche else bonne, raison,
             "Poker : " + " ".join(c[1] for c in cartes))
    if proche:
        print(f" Proche : le tableau préfère {bonne}.")
        print()

    pause()
    for i in range(5):
        if i not in garde:
            cartes[i] = paquet.pop()
    print(" " + "  ".join(f"{c[1]:<3}" for c in cartes))
    pause()
    main = evaluer_poker(cartes)
    mult = GAINS_POKER[main]
    etat['jetons'] += mise * mult
    if mult > 1:
        print(f" {main.capitalize()} : +{fmt(mise * (mult - 1))}")
    elif mult == 1:
        print(" Paire de valets ou mieux : mise rendue")
    else:
        print(f" Rien : perdu -{fmt(mise)}")
    for seuil, cle in OBJECTIFS_POKER:
        if mult >= seuil:
            debloquer(etat, cle)
    etat['jetons'] = round(etat['jetons'], 2)
    print(f" Jetons : {fmt(etat['jetons'])}")
    print()


# ====================== ROULETTE ======================
# Roulette européenne (0-36), plusieurs paris par tour, un seul prompt.

ROUGES_ROUL = frozenset({1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36})


def table_roulette():
    t = {}

    def ajouter(alias, label, nums, simple=False):
        for a in alias:
            t[a] = (label, frozenset(nums), simple)

    noirs = set(range(1, 37)) - ROUGES_ROUL
    ajouter(('r', 'rouge'), 'Rouge', ROUGES_ROUL, True)
    ajouter(('n', 'noir'), 'Noir', noirs, True)
    ajouter(('p', 'pair'), 'Pair', range(2, 37, 2), True)
    ajouter(('i', 'impair'), 'Impair', range(1, 37, 2), True)
    ajouter(('m', 'manque', '1-18'), 'Manque (1-18)', range(1, 19), True)
    ajouter(('passe', '19-36'), 'Passe (19-36)', range(19, 37), True)
    for k in (1, 2, 3):
        ajouter((f'd{k}',), f'Douzaine {k}', range(12 * (k - 1) + 1, 12 * k + 1))
        ajouter((f'c{k}',), f'Colonne {k}', range(k, 37, 3))
    return t


PARIS_ROULETTE = table_roulette()


def aide_roulette():
    print(" Syntaxe : code montant, plusieurs paris possibles (ex : r 20 k8 10 17 5)")
    print(" Plein (35:1) : 17        Cheval (17:1) : 17/18        (?plein, ?cheval)")
    print(" Transversale (11:1) : t7    Carré (8:1) : k8    Sixain (5:1) : s7    (?t, ?k, ?s)")
    print(" Douzaines (2:1) : d1 d2 d3    Colonnes (2:1) : c1 c2 c3    (?d)")
    print(" Chances simples (1:1) : r n p i m 1-18 19-36    (?r)")
    print(" Avec le 0 : 0, 0/1, 0/2, 0/3, 0/1/2, 0/2/3, 0/1/2/3    (?0)")
    print(" Le tapis : ?tapis | Toutes les aides : ?tout")
    print(" Entrée = refaire les mêmes paris, x = les doubler, / = les diviser par 2, h = historique")
    print(" Montants : 250, 10k (10 000), 1.5k, 2m (2 000 000)")
    print(" Sur le 0, les chances simples rendent la moitié de la mise.")


def combinaison_valide(nums):
    """Un ou plusieurs numéros voisins sur le tapis : plein, cheval, transversale, carré, sixain."""
    s = sorted(nums)
    n = len(s)
    if n == 1:
        return True
    if 0 in s:
        return s in ([0, 1], [0, 2], [0, 3], [0, 1, 2], [0, 2, 3], [0, 1, 2, 3])
    if n == 2:
        return s[1] - s[0] == 3 or (s[1] - s[0] == 1 and (s[0] - 1) // 3 == (s[1] - 1) // 3)
    if n == 3:
        return s[0] % 3 == 1 and s == [s[0], s[0] + 1, s[0] + 2]
    if n == 4:
        return s[0] % 3 in (1, 2) and s == [s[0], s[0] + 1, s[0] + 3, s[0] + 4]
    if n == 6:
        return s[0] % 3 == 1 and s == list(range(s[0], s[0] + 6))
    return False


def nombres_du_code(code):
    """k8 (carré 8/9/11/12), t7 (transversale 7/8/9), s7 (sixain 7 à 12) ou 17/18, 16/17/18..."""
    if code[0] in 'kts' and code[1:].isdigit():
        n = int(code[1:])
        if code[0] == 'k':
            nums = [n, n + 1, n + 3, n + 4]
        elif code[0] == 't':
            nums = [n, n + 1, n + 2]
        else:
            nums = list(range(n, n + 6))
    else:
        morceaux = code.split('/')
        if not all(m.isdigit() for m in morceaux):
            return None
        nums = [int(m) for m in morceaux]
    if len(set(nums)) != len(nums) or max(nums) > 36 or not combinaison_valide(nums):
        return None
    return frozenset(nums)


SUJETS_AIDE = ('tapis', 'plein', 'cheval', 't', 'k', 's', 'd', 'r', '0', 'tout')


def dessiner_tapis():
    print("           0")
    for ligne in range(12):
        a = 3 * ligne + 1
        print(f"      {a:>2}  {a + 1:>2}  {a + 2:>2}")


def par_lignes(items, par_ligne=4):
    for i in range(0, len(items), par_ligne):
        print("   " + "   ".join(items[i:i + par_ligne]))


def aide_detaillee(sujet):
    """Aides détaillées de la roulette : commande ?sujet (voir SUJETS_AIDE)."""
    if sujet == 'tout':
        for s in SUJETS_AIDE[:-1]:
            aide_detaillee(s)
            print()
        return
    if sujet == 'tapis':
        print(" Le tapis : 3 colonnes, 12 lignes. La ligne L contient 3L-2, 3L-1 et 3L.")
        dessiner_tapis()
        print(" Colonne 1 : 1, 4, 7... | colonne 2 : 2, 5, 8... | colonne 3 : 3, 6, 9...")
        print(" Le 0 est au-dessus du tapis : il touche 1, 2 et 3.")
    elif sujet == 'plein':
        print(" Plein (35:1) : un seul numéro, de 0 à 36. Code : le numéro. Ex : 17 10")
    elif sujet == 'cheval':
        print(" Cheval (17:1) : 2 numéros voisins sur le tapis. Code : les 2 numéros séparés par /")
        print("   Côte à côte (même ligne) : n/n+1, avec n en colonne 1 ou 2 : 1/2, 2/3, 4/5, 5/6, 7/8...")
        print("   L'un au-dessus de l'autre : n/n+3, n de 1 à 33 : 1/4, 2/5, 3/6, 4/7...")
        print("   Avec le 0 : 0/1, 0/2, 0/3")
        print("   Impossibles : 1/3 (pas voisins), 3/4 (fin de ligne et début de la suivante), 2/6")
    elif sujet == 't':
        print(" Transversale (11:1) : une ligne entière de 3 numéros.")
        print(" Code : t + le premier numéro de la ligne (ligne 1 : t1, ligne 2 : t4, ligne 3 : t7... +3 à chaque ligne)")
        par_lignes([f"t{n}={n}/{n + 1}/{n + 2}" for n in range(1, 35, 3)])
    elif sujet == 'k':
        print(" Carré (8:1) : 4 numéros qui forment un carré sur le tapis (2 colonnes voisines x 2 lignes voisines).")
        print(" Code : k + le PLUS PETIT des 4 numéros, c'est-à-dire celui en haut à gauche du carré.")
        print(" Exemple 8/9/11/12 :")
        print("       7  [ 8   9]")
        print("      10  [11  12]    -> le plus petit des 4 est 8 : k8")
        print(" Calcul : k n = n, n+1 (à droite), n+3 et n+4 (ligne du dessous).")
        print(" n est en colonne 1 ou 2 (jamais 3, 6, 9...) et au plus 32. Tous les carrés :")
        for ligne in range(1, 12):
            a = 3 * ligne - 2
            print(f"   Lignes {ligne}-{ligne + 1} : k{a}={a}/{a + 1}/{a + 3}/{a + 4}   "
                  f"k{a + 1}={a + 1}/{a + 2}/{a + 4}/{a + 5}")
    elif sujet == 's':
        print(" Sixain (5:1) : 2 lignes voisines = 6 numéros.")
        print(" Code : s + le premier numéro de la ligne du haut. Ex : s7 = lignes 7-8-9 et 10-11-12 = 7 à 12")
        par_lignes([f"s{n}={n}-{n + 5}" for n in range(1, 32, 3)])
    elif sujet == 'd':
        print(" Douzaines (2:1) : d1 = 1 à 12, d2 = 13 à 24, d3 = 25 à 36")
        print(" Colonnes (2:1) :")
        for c in (1, 2, 3):
            print(f"   c{c} : " + " ".join(str(n) for n in range(1, 37) if n % 3 == c % 3))
    elif sujet == 'r':
        rouges = sorted(ROUGES_ROUL)
        noirs = [n for n in range(1, 37) if n not in ROUGES_ROUL]
        print(" Chances simples (1:1) : sur le 0, la moitié de la mise est rendue.")
        print("   r (rouge) : " + " ".join(str(n) for n in rouges))
        print("   n (noir)  : " + " ".join(str(n) for n in noirs))
        print("   p (pair) : 2 4 6 ... 36        i (impair) : 1 3 5 ... 35")
        print("   m ou 1-18 (manque) : 1 à 18        19-36 (passe) : 19 à 36")
    elif sujet == '0':
        print(" Avec le 0 :")
        print("   0 : plein (35:1)")
        print("   0/1  0/2  0/3 : chevaux (17:1)")
        print("   0/1/2  0/2/3 : trios (11:1)")
        print("   0/1/2/3 : les quatre premiers (8:1)")


def lire_paris(saisie):
    """'r 20 17 5' -> (liste de paris, None) ou (None, message d'erreur)."""
    tokens = saisie.replace(',', ' ').split()
    if not tokens:
        return None, "Aucun pari."
    if len(tokens) % 2:
        return None, "Chaque pari est suivi d'un montant (ex : r 20 17 5)."
    paris = []
    for k in range(0, len(tokens), 2):
        code, texte_montant = tokens[k], tokens[k + 1]
        montant = lire_montant(texte_montant)
        if montant is None:
            return None, f"Montant invalide : {texte_montant}"
        if code in PARIS_ROULETTE:
            label, nums, simple = PARIS_ROULETTE[code]
        else:
            nums = nombres_du_code(code)
            if nums is None:
                return None, f"Pari inconnu ou combinaison impossible : {code} (? pour l'aide)"
            label = "/".join(str(x) for x in sorted(nums))
            simple = False
        paris.append({'label': label, 'nums': nums, 'simple': simple, 'mise': int(montant)})
    return paris, None


def afficher_historique(etat, detail=False):
    h = etat['hist_roulette']
    if not h:
        if detail:
            print(" Aucun tirage pour l'instant.")
        return

    def court(n):
        return f"{n}{'v' if n == 0 else 'r' if n in ROUGES_ROUL else 'n'}"

    print(" Derniers : " + " ".join(court(n) for n in reversed(h[-12:])))
    if not detail:
        return
    cpt = [h.count(n) for n in range(37)]
    chauds = sorted(range(37), key=lambda n: (-cpt[n], n))[:3]
    froids = sorted(range(37), key=lambda n: (cpt[n], n))[:3]
    print(" Chauds : " + ", ".join(f"{n} ({cpt[n]}x)" for n in chauds))
    print(" Froids : " + ", ".join(f"{n} ({cpt[n]}x)" for n in froids))
    total = len(h)
    rouges = sum(1 for n in h if n in ROUGES_ROUL)
    verts = h.count(0)
    print(f" Rouge {rouges * 100 // total} % | Noir {(total - rouges - verts) * 100 // total} % | "
          f"Vert {verts * 100 // total} % sur {total} tours")


def demander_paris_roulette(etat):
    derniere = etat['derniere_saisie_roulette']
    if derniere:
        invite = f"Paris (Entrée = {derniere}, x = double, / = moitié, h = historique, ? = aide) > "
    else:
        invite = "Paris (h = historique, ? = aide) > "
    while True:
        saisie = input(invite).strip().lower()
        if saisie in ('q', 'quit', 'exit'):
            raise Quitter
        if saisie in ('st', 'stats'):
            afficher_stats(etat)
            return None
        if saisie in ('j', 'jeu'):
            changer_jeu(etat)
            return None
        if saisie in ('h', 'hist'):
            afficher_historique(etat, True)
            continue
        if saisie in ('ob', 'objectifs'):
            afficher_objectifs(etat['objectifs'])
            continue
        if len(saisie) > 1 and saisie[0] == '?':
            if saisie[1:] in SUJETS_AIDE:
                aide_detaillee(saisie[1:])
            else:
                print(" Aides : ?tapis ?plein ?cheval ?t ?k ?s ?d ?r ?0 ?tout")
            continue
        if saisie in ('?', 'aide'):
            aide_roulette()
            continue
        if saisie in ('x', '2x'):
            if not derniere:
                print(" Aucun pari précédent.")
                continue
            tokens = derniere.replace(',', ' ').split()
            saisie = " ".join(t if k % 2 == 0 else str(lire_montant(t) * 2) for k, t in enumerate(tokens))
        if saisie in ('/', '/2'):
            if not derniere:
                print(" Aucun pari précédent.")
                continue
            tokens = derniere.replace(',', ' ').split()
            saisie = " ".join(t if k % 2 == 0 else str(max(1, lire_montant(t) // 2)) for k, t in enumerate(tokens))
        if saisie == '':
            if not derniere:
                print(" Aucun pari précédent.")
                continue
            saisie = derniere
        paris, erreur = lire_paris(saisie)
        if erreur:
            print(f" {erreur}")
            continue
        total = sum(p['mise'] for p in paris)
        if total > etat['jetons']:
            print(f" Pas assez de jetons ({fmt(total)} demandés).")
            continue
        etat['derniere_saisie_roulette'] = saisie
        return paris


def jouer_roulette(etat, paris):
    etat['jetons'] -= sum(p['mise'] for p in paris)
    print(" Rien ne va plus...")
    pause()
    pause()
    n = random.randint(0, 36)
    couleur = 'vert' if n == 0 else ('rouge' if n in ROUGES_ROUL else 'noir')
    print()
    print(f" {n} {couleur}")
    print()
    pause()
    etat['hist_roulette'].append(n)
    del etat['hist_roulette'][:-500]

    # Plusieurs gains : ils tombent un par un. Sinon tout d'un bloc.
    delai = 0.4 if sum(1 for p in paris if n in p['nums']) >= 2 else 0
    for p in paris:
        if delai:
            time.sleep(delai)
        m = p['mise']
        if n in p['nums']:
            gain = m * (36 // len(p['nums']) - 1)
            etat['jetons'] += m + gain
            print(f" {p['label']} : +{fmt(gain)}")
            if len(p['nums']) == 1:
                debloquer(etat, 'roul_plein')
                compter(etat, 'pleins')
            if n == 0:
                debloquer(etat, 'roul_zero')
        elif n == 0 and p['simple']:
            etat['jetons'] += m / 2
            print(f" {p['label']} : moitié rendue -{fmt(m / 2)}")
        else:
            print(f" {p['label']} : perdu -{fmt(m)}")

    etat['jetons'] = round(etat['jetons'], 2)
    print(f" Jetons : {fmt(etat['jetons'])}")
    print()


def serie_finale(recents):
    """Nombre de bonnes décisions consécutives à la fin de la liste."""
    n = 0
    for ok in reversed(recents):
        if not ok:
            break
        n += 1
    return n


SERIES_DECISIONS = ((10, 'serie10'), (30, 'serie30'), (50, 'serie50'), (100, 'serie100'))
SERIES_MANCHES = ((5, 'manches5'), (10, 'manches10'), (20, 'manches20'))
NOMS_CUMULS = {
    'manches': "Manches jouées", 'victoires': "Manches gagnées", 'bj': "Blackjacks",
    'bonnes': "Bonnes décisions", 'roulette': "Tours de roulette", 'baccara': "Mains de baccara",
    'poker': "Mains de poker", 'pleins': "Pleins gagnés à la roulette",
}


def ligne_statut(etat):
    """Ligne de suivi affichée avant chaque mise."""
    recents = etat['recents']
    pct = f"{sum(recents) * 100 // len(recents)} %" if recents else "-"
    return (f"Victoires d'affilée {etat['stats']['serie']} | "
            f"Bonnes décisions {etat['cumul'].get('bonnes', 0)} ({etat.get('serie_ok', 0)} d'affilée) | "
            f"{len(recents)} dernières {pct} | "
            f"Objectifs {len(etat['objectifs'])}/{len(OBJECTIFS)}")


def prochain_objectif(faits, paliers):
    for seuil, objectif in paliers:
        if objectif not in faits:
            return seuil, objectif
    return None


def afficher_progression(etat):
    """Avancement vers le prochain objectif de chaque compteur."""
    suivis = [
        ("Décisions d'affilée", etat.get('serie_ok', 0), SERIES_DECISIONS),
        ("Victoires d'affilée", etat['stats']['serie'], SERIES_MANCHES),
        ("Jetons", int(etat['jetons']), JALONS),
    ]
    for cle, nom in NOMS_CUMULS.items():
        suivis.append((nom, etat['cumul'].get(cle, 0), CUMULS[cle]))
    print("Prochains objectifs :")
    for nom, actuel, paliers in suivis:
        suivant = prochain_objectif(etat['objectifs'], paliers)
        if suivant:
            print(f"  {nom} : {fmt(actuel)}/{fmt(suivant[0])} (+{fmt(RECOMPENSES[suivant[1]])})")


def enregistrer(etat, net):
    s = etat['stats']
    s['manches'] += 1
    s['hist'].append(etat['jetons'])
    etat['record'] = max(etat['record'], etat['jetons'])
    if net > 0:
        s['gagnees'] += 1
        s['serie'] += 1
        s['meilleure_serie'] = max(s['meilleure_serie'], s['serie'])
        s['gain_max'] = max(s['gain_max'], net)
    elif net < 0:
        s['perdues'] += 1
        s['serie'] = 0
        s['perte_max'] = min(s['perte_max'], net)
    else:
        s['egalites'] += 1
    compter(etat, 'manches')
    if net > 0:
        compter(etat, 'victoires')
        for seuil, cle in ((1000, 'gain1k'), (5000, 'gain5k'), (25000, 'gain25k'), (100000, 'gain100k')):
            if net >= seuil:
                debloquer(etat, cle)
    if etat['jetons'] < 300:
        etat['creux'] = True
    if etat.get('creux') and etat['jetons'] >= 2000:
        debloquer(etat, 'remontada')
    for seuil, cle in JALONS:
        if etat['jetons'] >= seuil:
            debloquer(etat, cle)
    for seuil, cle in ((5, 'manches5'), (10, 'manches10'), (20, 'manches20')):
        if s['serie'] >= seuil:
            debloquer(etat, cle)


def run_game():
    print("\nCasino | j = changer de jeu, st = stats, ob = objectifs, q = quitter")
    print("Blackjack : h hit, s stand, d double, sp split")
    print("Cartes : p = pique, c = coeur, k = carreau, t = trèfle (Rc = roi de coeur)\n")

    jetons, record = DEPART, DEPART
    save = charger()
    if save:
        record = max(record, save.get('record', DEPART))
        if save.get('jetons', 0) >= 1:
            rep = input(f"Reprendre avec {fmt(save['jetons'])} jetons ? "
                        f"(Entrée = oui, n = repartir à {DEPART}) > ").strip().lower()
            if rep not in ('n', 'non'):
                jetons = save['jetons']
            print()

    etat = {
        'jetons': jetons, 'record': max(record, jetons), 'derniere': 0,
        'dernier_side': {'p': 0, 't': 0}, 'sabot': nouveau_sabot(),
        'dernier_side_bac': {'e': 0, 'pj': 0, 'pb': 0}, 'dernier_pari': 'banquier',
        'sabot_bac': nouveau_sabot(8), 'jeu': 'blackjack', 'jeux_joues': set(),
        'derniere_saisie_roulette': '', 'bonus': 0,
        'cumul': dict(save.get('cumul', {})) if save else {},
        'hist_roulette': list(save.get('hist_roulette', [])) if save else [],
        'recents': list(save.get('recents', [])) if save else [],
        'score': 0, 'total': 0, 'revoir': {},
        'objectifs': set(save.get('objectifs', [])) if save else set(), 'nouveaux': [],
        'stats': {'manches': 0, 'gagnees': 0, 'perdues': 0, 'egalites': 0,
                  'serie': 0, 'meilleure_serie': 0, 'gain_max': 0, 'perte_max': 0,
                  'hist': [jetons]},
    }
    # La série de bonnes décisions continue d'une session à l'autre
    if save:
        etat['serie_ok'] = save.get('serie_ok', serie_finale(etat['recents']))
        etat['meilleure_serie_ok'] = max(save.get('meilleure_serie_ok', 0), etat['serie_ok'])
    for seuil, cle in SERIES_DECISIONS:
        if etat.get('serie_ok', 0) >= seuil:
            debloquer(etat, cle)
    try:
        changer_jeu(etat)
        while etat['jetons'] >= 1:
            print(f"Jetons : {fmt(etat['jetons'])} | {NOMS_JEUX[etat['jeu']]}")
            print(ligne_statut(etat))
            if etat['jeu'] == 'roulette':
                afficher_historique(etat)
                mise = demander_paris_roulette(etat)
            else:
                mise = demander_mise(etat)
            if mise is None:
                continue
            avant = etat['jetons']
            bonus_avant = etat['bonus']
            etat['jeux_joues'].add(etat['jeu'])
            nb_jeux = len(etat['jeux_joues'])
            if nb_jeux >= 2:
                debloquer(etat, 'deux_jeux')
            if nb_jeux >= 3:
                debloquer(etat, 'trois_jeux')
            if nb_jeux == 4:
                debloquer(etat, 'quatre_jeux')
            if etat['jeu'] == 'blackjack':
                side = demander_side(etat, mise)
                etat['derniere'] = mise
                engage = mise + side['p'] + side['t']
                jouer_manche(etat, mise, side)
            elif etat['jeu'] == 'baccara':
                pari = demander_pari(etat)
                side = demander_side_bac(etat, mise)
                etat['derniere'] = mise
                engage = mise + sum(side.values())
                jouer_baccara(etat, mise, pari, side)
                compter(etat, 'baccara')
            elif etat['jeu'] == 'poker':
                etat['derniere'] = mise
                engage = mise
                jouer_poker(etat, mise)
                compter(etat, 'poker')
            else:
                engage = sum(p['mise'] for p in mise)
                jouer_roulette(etat, mise)
                compter(etat, 'roulette')
            net = etat['jetons'] - avant - (etat['bonus'] - bonus_avant)
            if engage >= avant and net > 0:
                debloquer(etat, 'allin')
            enregistrer(etat, net)
            sauver(etat)
        print("Plus de jetons.")
    except Quitter:
        pass
    if etat['total'] >= 50 and etat['score'] / etat['total'] >= 0.8:
        debloquer(etat, 'precision')
    if etat['total'] >= 100 and etat['score'] / etat['total'] >= 0.9:
        debloquer(etat, 'precision90')
    sauver(etat)
    fin(etat, jeu=True)


# ====================== MODE ENTRAÎNEMENT ======================
# Toutes les situations sont vues une fois avant de recommencer.
# Une situation ratée revient quelques mains plus tard.

def nom(carte):
    if carte == 11:
        return 'A'
    if carte == 10:
        return random.choice(['10', 'V', 'D', 'R'])
    return str(carte)


def construire_pool():
    pool = []
    for d in range(2, 12):
        for v in range(2, 12):
            pool.append(('paire', v, d))
        for x in range(2, 10):
            pool.append(('souple', x, d))
        for t in range(8, 18):
            pool.append(('dure', t, d))
        for t in range(9, 17):      # dur à 3 cartes ou plus (après un tirage)
            pool.append(('mdure', t, d))
        for t in range(15, 19):     # soft à 3 cartes ou plus
            pool.append(('msouple', t, d))
    random.shuffle(pool)
    return deque(pool)


def construire(cle):
    genre, x, d = cle
    if genre == 'paire':
        return [x, x], d
    if genre == 'souple':
        return [11, x], d
    for _ in range(500):
        if genre == 'dure':
            a = random.randint(2, 10)
            b = x - a
            if 2 <= b <= 10 and a != b:
                return [a, b], d
        elif genre == 'mdure':
            m = [random.randint(2, 10) for _ in range(3)]
            if sum(m) == x:
                return m, d
        elif genre == 'msouple':
            m = [random.randint(2, 7) for _ in range(2)]
            if 11 + sum(m) == x:
                return [11] + m, d
    return None


def cle_de(vals, d, cle_initiale):
    if len(vals) == 2:
        return cle_initiale
    total, soft = valeur(vals)
    return ('msouple' if soft else 'mdure', total, d)


def run_training():
    print("\nEntraînement | h hit, s stand, d double, sp split, q quitter\n")
    etat = {'score': 0, 'total': 0, 'revoir': {}}
    pool = deque()

    try:
        while True:
            if not pool:
                pool = construire_pool()
            cle = pool.popleft()
            base = construire(cle)
            if base is None:
                continue

            vals, d = base
            noms = [nom(c) for c in vals]
            d_nom = nom(d)

            # Une main peut avoir plusieurs décisions (tirages successifs)
            while True:
                deux = len(vals) == 2
                spl = deux and vals[0] == vals[1]
                bonne, raison = decision(vals, d, deux, spl)
                description = decrire(vals, noms)

                print(f" Ta main : {description}")
                print(f" Banque  : {d_nom}")

                action = demander_action(deux, spl)
                corriger(etat, action, bonne, raison, f"{description} vs {d_nom}")
                if action != bonne:
                    pool.insert(min(len(pool), random.randint(6, 14)), cle_de(vals, d, cle))

                if bonne != 'hit':
                    break

                carte = random.choice(CARTES)
                vals.append(carte)
                noms.append(nom(carte))
                total, _ = valeur(vals)
                if total > 21:
                    print(f" Bust ({total})\n")
                    break
                if total == 21:
                    print(" 21\n")
                    break
    except Quitter:
        pass
    fin(etat, jeu=False)


# ====================== MENU ======================

def afficher_objectifs(faits=None):
    if faits is None:
        faits = set((charger() or {}).get('objectifs', []))
    print()
    for titre, objs in PALIERS:
        n = sum(1 for c, _, _ in objs if c in faits)
        print(f"  {titre} ({n}/{len(objs)})")
        for c, libelle, prime in objs:
            print(f"    [{'x' if c in faits else ' '}] {libelle} (+{fmt(prime)})")
    primes = sum(RECOMPENSES[c] for c in faits if c in RECOMPENSES)
    print()
    print(f"  {len(set(faits) & set(LIBELLES))}/{len(OBJECTIFS)} | Primes obtenues : {fmt(primes)} jetons")
    print()


def main():
    while True:
        print("1. Casino avec jetons (blackjack, baccara, roulette, video poker)")
        print("2. Entraînement (toutes les situations)")
        print("3. Objectifs")
        print("q. Quitter")
        choix = input("Mode > ").strip().lower()
        if choix == '1':
            run_game()
        elif choix == '2':
            run_training()
        elif choix == '3':
            afficher_objectifs()
        elif choix in ('q', 'quit', 'exit'):
            return
        else:
            print(" 1, 2, 3 ou q\n")


if __name__ == "__main__":
    main()
