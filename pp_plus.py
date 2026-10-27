"""Extensions de pp.py : craps, machine a sous, crash, Hi-Lo, double ou rien,
jackpot progressif, defis du jour et mode tournoi.

Ce module est charge par pp.py (installer). Il ne se lance pas tout seul.
"""
import json
import math
import random
import sys
import time
from datetime import date

try:
    import msvcrt  # Windows : lecture d'une touche sans bloquer
except ImportError:
    msvcrt = None

NEEDED = ['fmt', 'pause', 'corriger', 'debloquer', 'compter', 'Quitter', 'lire_montant', 'demander_mise',
          'ajouter_objectifs', 'JEUX_EXTRA', 'NOMS_JEUX', 'CUMULS', 'NOMS_CUMULS', 'charger', 'SAVE',
          'afficher_stats', 'afficher_objectifs', 'changer_jeu', 'PAUSE', 'DEPART', 'OBJECTIFS', 'RECOMPENSES',
          'LIBELLES']

POT_DEPART = 20000
JACKPOT_PART = 0.03        # part de chaque mise versée dans la cagnotte
JACKPOT_DIVISEUR = 600000  # chance par manche = mise / 600000 (mise 100 = 1 chance sur 6000)
JACKPOT_PLAFOND = 1000     # au-delà de cette mise, la chance n'augmente plus
JACKPOT_MIN = 10           # mise minimale pour être éligible
TOURNOI_DEFAUT = 30


def installer(ns):
    g = globals()
    for k in NEEDED:
        g[k] = ns[k]
    NOMS_JEUX.update({'craps': 'Craps', 'slots': 'Machine à sous', 'crash': 'Crash'})
    JEUX_EXTRA['craps'] = {
        'nom': 'Craps', 'demander': demander_craps, 'jouer': jouer_craps, 'compteur': 'craps',
        'aide': [" Craps. Une manche = un lanceur : come-out, puis point jusqu'au 7 ou au point.",
                 " Pass (p) ou Don't pass (dp) au come-out, puis cote libre derrière ton pari de base.",
                 " Entrée = lancer les dés, ? = aide détaillée des paris et de leurs avantages."]}
    JEUX_EXTRA['slots'] = {
        'nom': 'Machine à sous', 'demander': demander_slots, 'jouer': jouer_slots, 'compteur': 'slots',
        'aide': lignes_aide_slots()}
    JEUX_EXTRA['crash'] = {
        'nom': 'Crash', 'demander': demander_crash, 'jouer': jouer_crash, 'compteur': 'crash',
        'aide': [" Crash. Le multiplicateur monte, encaisse avant qu'il plante.",
                 " Retrait auto : tu fixes un multiplicateur cible, ou Entrée pour encaisser toi-même d'une touche."]}
    for cle, nom in (('craps', "Tours de craps"), ('slots', "Tours de machine à sous"),
                     ('crash', "Parties de crash"), ('defis', "Défis du jour réussis")):
        NOMS_CUMULS[cle] = nom
    CUMULS.update({'craps': [(50, 'craps50'), (500, 'craps500')],
                   'slots': [(100, 'slots100'), (1000, 'slots1000')],
                   'crash': [(50, 'crash50'), (500, 'crash500')],
                   'defis': [(5, 'defis5'), (30, 'defis30')]})
    ajouter_objectifs('Débutant', [
        ('craps_pass', "Craps : gagner un Pass line", 150),
        ('dr_gagne', "Gagner un double ou rien", 100),
        ('tournoi_fini', "Terminer un tournoi", 300),
    ])
    ajouter_objectifs('Confirmé', [
        ('craps_odds', "Craps : gagner une cote libre", 400),
        ('slots_free', "Machine à sous : déclencher les tours gratuits", 400),
        ('crash_x10', "Crash : encaisser à 10x ou plus", 500),
        ('dr3', "Gagner 3 doubles ou rien d'affilée", 800),
        ('hilo10', "Hi-Lo : 10 comptes justes d'affilée", 500),
        ('defis5', "Réussir 5 défis du jour (au total)", 500),
        ('craps50', "Jouer 50 tours de craps (au total)", 300),
        ('slots100', "Jouer 100 tours de machine à sous (au total)", 300),
        ('crash50', "Jouer 50 parties de crash (au total)", 300),
        ('tournoi_x3', "Tournoi : finir avec 3 000 jetons ou plus", 1500),
    ])
    ajouter_objectifs('Expert', [
        ('slots_777', "Machine à sous : 5 symboles 777 sur une ligne", 3000),
        ('slots_x100', "Machine à sous : gagner 100x la mise sur un tour", 3000),
        ('crash_x100', "Crash : encaisser à 100x ou plus", 5000),
        ('dr5', "Gagner 5 doubles ou rien d'affilée", 3000),
        ('hilo50', "Hi-Lo : 50 bons comptes (au total)", 2000),
        ('defis30', "Réussir 30 défis du jour (au total)", 3000),
        ('craps500', "Jouer 500 tours de craps (au total)", 3000),
        ('slots1000', "Jouer 1 000 tours de machine à sous (au total)", 3000),
        ('crash500', "Jouer 500 parties de crash (au total)", 3000),
        ('tournoi_x10', "Tournoi : finir avec 10 000 jetons ou plus", 5000),
    ])
    ajouter_objectifs('Légende', [
        ('jackpot', "Toucher le jackpot progressif", 20000),
    ])


# ============================================================ aides communes

def dormir(t):
    time.sleep(t)


def entree_pressee():
    """True si une touche (Entrée) a été pressée pendant l'animation ; vide le tampon clavier."""
    if msvcrt is not None:
        if msvcrt.kbhit():
            while msvcrt.kbhit():
                msvcrt.getwch()
            return True
        return False
    try:
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            return bool(sys.stdin.readline())
    except Exception:
        pass
    return False


def vider_clavier():
    """Supprime les touches pressées pendant une séquence non passable (évite les mises accidentelles)."""
    try:
        for _ in range(50):
            if not entree_pressee():
                break
    except Exception:
        pass


def dormir_ou_passer(t):
    """Attend t secondes par petits pas. Retourne True si Entrée a été pressée (on saute l'attente)."""
    ecoule = 0.0
    while True:
        if entree_pressee():
            return True
        if ecoule >= t:
            return False
        pas = min(0.02, t - ecoule)
        dormir(pas)
        ecoule += pas


def transformer(saisie, f):
    """Applique f aux montants d'une saisie 'code montant code montant'."""
    tokens = saisie.replace(',', ' ').split()
    out = []
    for k, t in enumerate(tokens):
        if k % 2 == 1:
            m = lire_montant(t)
            out.append(str(max(1, f(m))) if m is not None else t)
        else:
            out.append(t)
    return " ".join(out)


def commande_globale(etat, saisie):
    """q, st, ob, j, dr, hl. Retourne None (pas une commande), True (traitée) ou 'jeu'."""
    if saisie in ('q', 'quit', 'exit'):
        raise Quitter
    if saisie in ('st', 'stats'):
        afficher_stats(etat)
        return True
    if saisie in ('ob', 'objectifs'):
        afficher_objectifs(etat['objectifs'])
        return True
    if saisie in ('j', 'jeu'):
        changer_jeu(etat)
        return 'jeu'
    if saisie == 'dr':
        basculer_dr(etat)
        return True
    if saisie in ('df', 'defi', 'défi'):
        afficher_defi(etat)
        return True
    if saisie == 'hl':
        basculer_hilo(etat)
        return True
    return None


# ============================================================ double ou rien

def basculer_dr(etat):
    etat['dr_actif'] = not etat.get('dr_actif', True)
    print(f" Double ou rien : {'activé' if etat['dr_actif'] else 'désactivé'}.")


def double_ou_rien(etat, gain):
    """Propose de remettre un gain en jeu sur une couleur (carte rouge ou noire)."""
    if gain <= 0 or not etat.get('dr_actif', True):
        return
    enjeu = gain
    while enjeu > 0:
        s = input(f"Double ou rien sur +{fmt(enjeu)} ? (r = rouge, n = noir, Entrée = non) > ").strip().lower()
        if s not in ('r', 'n', 'rouge', 'noir'):
            break
        carte = random.choice('pckt')
        rang = random.choice(['2', '3', '4', '5', '6', '7', '8', '9', '10', 'V', 'D', 'R', 'A'])
        rouge = carte in 'ck'
        pause()
        print(f" Carte : {rang}{carte} ({'rouge' if rouge else 'noir'})")
        if rouge == s.startswith('r'):
            etat['jetons'] += enjeu
            enjeu *= 2
            etat['dr_serie'] = etat.get('dr_serie', 0) + 1
            print(f" Gagné : ton gain passe à +{fmt(enjeu)}")
            debloquer(etat, 'dr_gagne')
            if etat['dr_serie'] >= 3:
                debloquer(etat, 'dr3')
            if etat['dr_serie'] >= 5:
                debloquer(etat, 'dr5')
        else:
            etat['jetons'] -= enjeu
            etat['dr_serie'] = 0
            print(f" Perdu -{fmt(enjeu)}")
            break
    etat['jetons'] = round(etat['jetons'], 2)
    print()


# ============================================================ jackpot

def chance_jackpot(engage):
    if engage < JACKPOT_MIN:
        return 0.0
    return min(engage, JACKPOT_PLAFOND) / JACKPOT_DIVISEUR


def jackpot(etat, engage):
    """Alimente la cagnotte (3 % de la mise) puis tire le jackpot : chance = mise / 600 000 (plafonnée)."""
    if etat.get('tournoi'):
        return
    etat['jackpot'] = round(etat.get('jackpot', POT_DEPART) + engage * JACKPOT_PART, 2)
    p = chance_jackpot(engage)
    if p and random.random() < p:
        gain = round(etat['jackpot'])
        vider_clavier()
        print("\n Jackpot progressif !")
        dormir(1.2)
        print(f" Le tirage du jackpot est tombé sur ta mise de {fmt(engage)} (1 chance sur {round(1 / p)} par manche).")
        dormir(1.5)
        print(f" +{fmt(gain)} jetons\n")
        dormir(1.0)
        vider_clavier()
        etat['jetons'] += gain
        etat['bonus'] += gain
        etat['jackpot'] = max(POT_DEPART, round(engage * 100))
        debloquer(etat, 'jackpot')


# ============================================================ défis du jour

DEFIS = [
    ('d_gain', "Finir la session avec 500 jetons de plus qu'au départ", 300,
     lambda e: e['jetons'] - e['stats']['hist'][0] >= 500),
    ('d_serie3', "Gagner 3 manches d'affilée", 250, lambda e: e['stats']['serie'] >= 3),
    ('d_dec15', "15 bonnes décisions d'affilée", 300, lambda e: e.get('serie_ok', 0) >= 15),
    ('d_manches20', "Jouer 20 manches", 200, lambda e: e['stats']['manches'] >= 20),
    ('d_jeux3', "Jouer à 3 jeux différents", 300, lambda e: len(e['jeux_joues']) >= 3),
    ('d_prec', "85 % de bonnes décisions sur au moins 20 décisions", 400,
     lambda e: e['total'] >= 20 and e['score'] / e['total'] >= 0.85),
    ('d_bj15', "Jouer 15 mains de blackjack", 250, lambda e: e['compte_session'].get('blackjack', 0) >= 15),
    ('d_roul10', "Jouer 10 tours de roulette", 200, lambda e: e['compte_session'].get('roulette', 0) >= 10),
    ('d_craps5', "Jouer 5 tours de craps", 250, lambda e: e['compte_session'].get('craps', 0) >= 5),
    ('d_slots20', "Jouer 20 tours de machine à sous", 200, lambda e: e['compte_session'].get('slots', 0) >= 20),
]


def defi_du_jour():
    rng = random.Random(date.today().isoformat())
    return rng.choice(DEFIS)


def verifier_defi(etat):
    d = etat.get('defi')
    if not d or etat.get('defi_fait') == date.today().isoformat():
        return
    if d[3](etat):
        etat['jetons'] += d[2]
        etat['bonus'] += d[2]
        etat['defi_fait'] = date.today().isoformat()
        print(f" Défi du jour réussi : {d[1]} (+{fmt(d[2])} jetons)")
        compter(etat, 'defis')


def afficher_defi(etat):
    d = etat.get('defi')
    if not d:
        print("Pas de défi du jour dans ce mode.")
        return
    if etat.get('defi_fait') == date.today().isoformat():
        print("Défi du jour : réussi")
    else:
        print(f"Défi du jour : {d[1]} (+{fmt(d[2])})")


# ============================================================ Hi-Lo

def hl(carte):
    v = carte[0]
    return 1 if v <= 6 else (0 if v <= 9 else -1)


def basculer_hilo(etat):
    etat['hilo'] = not etat.get('hilo', False)
    if etat['hilo']:
        etat['hilo_dans'] = random.randint(2, 4)
        print(" Hi-Lo activé : 2 à 6 = +1, 7 à 9 = 0, 10 à As = -1.")
        print(" Tous les 2 à 5 mains de blackjack, le jeu te demande le compte (comptes à part de tes décisions).")
        print(" hl pour désactiver.")
    else:
        print(" Hi-Lo désactivé.")


def compte_courant(etat):
    """Compte Hi-Lo des cartes sorties : un sabot neuf vaut 0, donc c'est l'opposé du reste."""
    return -sum(hl(c) for c in etat['sabot'])


def _compte_hilo(etat, ok):
    s = etat.setdefault('hilo_stats', {'ok': 0, 'total': 0, 'serie': 0, 'record': 0})
    s['total'] += 1
    if ok:
        s['ok'] += 1
        s['serie'] += 1
        s['record'] = max(s['record'], s['serie'])
        etat['cumul']['hilo_ok'] = etat['cumul'].get('hilo_ok', 0) + 1
        if s['serie'] >= 10:
            debloquer(etat, 'hilo10')
        if etat['cumul']['hilo_ok'] >= 50:
            debloquer(etat, 'hilo50')
    else:
        s['serie'] = 0


def _lire_entier(invite, defaut_vide=None):
    while True:
        s = input(invite).strip().lower().replace(',', '.').replace('+', '')
        if s in ('q', 'quit', 'exit'):
            raise Quitter
        if s == '':
            return defaut_vide
        try:
            return float(s)
        except ValueError:
            print(" Un nombre, par exemple 3 ou -2 (Entrée = voir le compte)")


def questions_hilo(etat):
    """Pose les questions de comptage avant la mise, de temps en temps."""
    if etat['jeu'] != 'blackjack' or not etat.get('hilo'):
        return
    etat['hilo_dans'] = etat.get('hilo_dans', 3) - 1
    if etat['hilo_dans'] > 0:
        return
    etat['hilo_dans'] = random.randint(2, 5)
    sabot = etat['sabot']
    exact = compte_courant(etat)
    vues = 312 - len(sabot)
    bas = 120 - sum(1 for c in sabot if c[0] <= 6)
    haut = 120 - sum(1 for c in sabot if c[0] >= 10)
    print(f" Hi-Lo : {vues} cartes sorties depuis le mélange.")
    rep = _lire_entier("Compte courant ? (Entrée = le voir) > ")
    detail = f"{bas} petites (2-6) - {haut} grosses (10-As) = {exact:+d}"
    if rep is None:
        print(f" Compte : {detail}\n")
        return
    ok = abs(rep - exact) < 0.01
    _compte_hilo(etat, ok)
    print(f" {'Exact' if ok else 'Faux'} : {detail}")
    if random.random() < 0.5 or not ok:
        jeux = len(sabot) / 52
        vrai = exact / max(jeux, 0.5)
        rep2 = _lire_entier(f"Vrai compte ? ({jeux:.1f} jeux restants, Entrée = passer) > ")
        if rep2 is not None:
            ok2 = abs(rep2 - vrai) <= 1.0
            _compte_hilo(etat, ok2)
            print(f" {'Exact' if ok2 else 'Faux'} : {exact:+d} / {jeux:.1f} = {vrai:+.1f} (±1 accepté)")
    s = etat['hilo_stats']
    print(f" Hi-Lo : {s['ok']}/{s['total']} (série {s['serie']}, record {s['record']})\n")


# ============================================================ craps

RATIO = {4: (2, 1), 10: (2, 1), 5: (3, 2), 9: (3, 2), 6: (6, 5), 8: (6, 5)}
CAP = {4: 3, 10: 3, 5: 4, 9: 4, 6: 5, 8: 5}
PLACE = {4: 9 / 5, 10: 9 / 5, 5: 7 / 5, 9: 7 / 5, 6: 7 / 6, 8: 7 / 6}
UN_COUP = {'f': ("Field", 2.78), '7': ("Any 7", 16.67), 'c': ("Any craps", 11.11), 'y': ("Yo (11)", 11.11)}
PAUSE_DES = 0.7


def aide_craps(phase='sortie'):
    print(" Syntaxe : code montant, plusieurs paris possibles (ex : p 20 f 10)")
    print(" Come-out (avant le point) :")
    print("   p  = Pass line : gagne sur 7 ou 11, perd sur 2, 3, 12 (avantage banque 1,41 %)")
    print("   dp = Don't pass : l'inverse, 12 = égalité (1,36 %). Pass et Don't pass ne se jouent pas ensemble.")
    print("   Le point (4,5,6,8,9,10) fixé, il faut le refaire avant le 7 pour gagner le Pass.")
    print(" Cote libre : après le point, derrière ton pari de base, aucun avantage pour la banque.")
    print("   Pass : paie 2:1 sur 4/10, 3:2 sur 5/9, 6:5 sur 6/8. Max 3x, 4x, 5x ta mise de base.")
    print(" Paris à un coup (tous les lancers) : f Field (2,78 %), 7 Any seven 4:1 (16,67 %),")
    print("   c Any craps 7:1 (11,11 %), y Yo 15:1 (11,11 %).")
    print(" Place (après le point) : pl6 pl8 7:6 (1,52 %), pl5 pl9 7:5 (4 %), pl4 pl10 9:5 (6,67 %).")
    print(" Field : paie sur 3, 4, 9, 10, 11 (1:1), 2 (2:1), 12 (3:1).")
    print(" Entrée = refaire les mêmes paris, x = doubler, / = diviser par 2.")


def lire_paris_craps(saisie, phase):
    tokens = saisie.replace(',', ' ').split()
    if not tokens or len(tokens) % 2:
        return None, "Chaque pari est suivi d'un montant (ex : p 20 f 10)."
    permis = {'sortie': {'p', 'dp', 'f', '7', 'c', 'y'},
              'point': {'f', '7', 'c', 'y', 'pl4', 'pl5', 'pl6', 'pl8', 'pl9', 'pl10'}}[phase]
    paris = {}
    for k in range(0, len(tokens), 2):
        code, txt = tokens[k], tokens[k + 1]
        montant = lire_montant(txt)
        if montant is None:
            return None, f"Montant invalide : {txt}"
        if code not in permis:
            if phase == 'point' and code in ('p', 'dp'):
                return None, "Pass et Don't pass se jouent avant le point."
            if phase == 'sortie' and code.startswith('pl'):
                return None, "Les paris Place se posent une fois le point établi."
            return None, f"Pari inconnu : {code} (? pour l'aide)"
        paris[code] = paris.get(code, 0) + montant
    if 'p' in paris and 'dp' in paris:
        return None, "Pass et Don't pass ensemble : choisis l'un des deux."
    return paris, None


def demander_craps(etat):
    derniere = etat.get('derniere_craps', '')
    while True:
        invite = f"Come-out (Entrée = {derniere}, " if derniere else "Come-out ("
        invite += "p 20 = Pass, dp 20 = Don't pass, x, /, ? = aide, st, j, q) > "
        saisie = input(invite).strip().lower()
        r = commande_globale(etat, saisie)
        if r == 'jeu':
            return None
        if r:
            continue
        if saisie in ('?', 'aide'):
            aide_craps()
            continue
        if saisie == '':
            if not derniere:
                print(" Aucun pari précédent.")
                continue
            saisie = derniere
        elif saisie == 'x' and derniere:
            saisie = transformer(derniere, lambda m: m * 2)
        elif saisie in ('/', '/2') and derniere:
            saisie = transformer(derniere, lambda m: m // 2)
        paris, erreur = lire_paris_craps(saisie, 'sortie')
        if erreur:
            print(f" {erreur}")
            continue
        total = sum(paris.values())
        if total > etat['jetons']:
            print(f" Pas assez de jetons ({fmt(total)} demandés).")
            continue
        etat['derniere_craps'] = saisie
        return paris


def lancer_des():
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    print(f" Dés : {d1}", end="", flush=True)
    dormir(PAUSE_DES)
    print(f" + {d2}", end="", flush=True)
    dormir(PAUSE_DES)
    print(f" = {d1 + d2}{'  (hardway)' if d1 == d2 and d1 + d2 in (4, 6, 8, 10) else ''}")
    return d1 + d2


def _payer(etat, mise, gain, label, lignes):
    """gain > 0 : gagné (mise + gain rendus), 0 : égalité, None : perdu."""
    if gain is None:
        lignes.append(f" {label} : perdu -{fmt(mise)}")
    elif gain == 0:
        etat['jetons'] += mise
        lignes.append(f" {label} : égalité")
    else:
        gain = round(gain, 2)
        etat['jetons'] += mise + gain
        lignes.append(f" {label} : +{fmt(gain)}")


def _un_coup(etat, tot, unique, lignes):
    for code, m in unique.items():
        nom = UN_COUP[code][0]
        if code == 'f':
            mult = {2: 2, 12: 3}.get(tot, 1 if tot in (3, 4, 9, 10, 11) else None)
        elif code == '7':
            mult = 4 if tot == 7 else None
        elif code == 'c':
            mult = 7 if tot in (2, 3, 12) else None
        else:
            mult = 15 if tot == 11 else None
        _payer(etat, m, None if mult is None else m * mult, nom, lignes)
    unique.clear()


def _afficher_table(point, ligne, plat, cote, tenus):
    morceaux = [f"Point {point}"]
    if ligne:
        nom = "Pass" if ligne == 'p' else "Don't pass"
        morceaux.append(f"{nom} {fmt(plat)}" + (f" + cote {fmt(cote)}" if cote else ""))
    for code, m in tenus.items():
        morceaux.append(f"Place {code[2:]} : {fmt(m)}")
    print(" " + " | ".join(morceaux))


def jouer_craps(etat, paris):
    engage = sum(paris.values())
    etat['jetons'] -= engage
    ligne = 'p' if 'p' in paris else ('dp' if 'dp' in paris else None)
    plat = paris.get(ligne, 0) if ligne else 0
    unique = {k: v for k, v in paris.items() if k in UN_COUP}
    tenus = {}
    cote = 0
    point = None
    try:
        # Come-out
        print(" Come-out")
        pause()
        tot = lancer_des()
        lignes = []
        _un_coup(etat, tot, unique, lignes)
        if ligne:
            if tot in (7, 11):
                _payer(etat, plat, plat if ligne == 'p' else None, "Pass line" if ligne == 'p' else "Don't pass", lignes)
                if ligne == 'p':
                    debloquer(etat, 'craps_pass')
                plat = 0
            elif tot in (2, 3, 12):
                if ligne == 'p':
                    _payer(etat, plat, None, "Pass line", lignes)
                else:
                    _payer(etat, plat, 0 if tot == 12 else plat, "Don't pass", lignes)
                plat = 0
            else:
                point = tot
        for l in lignes:
            print(l)
        if point is None:
            etat['jetons'] = round(etat['jetons'], 2)
            print(f" Jetons : {fmt(etat['jetons'])}\n")
            return engage

        # Point établi : cote libre
        print(f" Le point est {point}.")
        num, den = RATIO[point]
        maxi = plat * CAP[point] if ligne == 'p' else int(plat * CAP[point] * num / den)
        maxi = min(int(maxi), int(etat['jetons']))
        if maxi >= 1:
            while True:
                s = input(f"Cote libre ? (montant, m = max {fmt(maxi)}, Entrée = non) > ").strip().lower()
                if s in ('q', 'quit', 'exit'):
                    raise Quitter
                if s == '':
                    montant = 0
                    break
                montant = maxi if s == 'm' else lire_montant(s)
                if montant is None or montant > maxi:
                    print(f" Entre 1 et {fmt(maxi)}.")
                    continue
                break
            bonne = 'COTE LIBRE'
            choix = 'COTE LIBRE' if montant > 0 else 'SANS COTE'
            corriger(etat, choix, bonne,
                     "La cote libre est le seul pari sans avantage pour la banque : prends-la (max 3-4-5x ramène "
                     "l'avantage total à ~0,4 %).", f"Craps : cote libre au point {point}")
            if montant:
                etat['jetons'] -= montant
                cote = montant
                engage += montant
        _afficher_table(point, ligne, plat, cote, tenus)

        # Lancers du point
        while True:
            while True:
                s = input("Lancer ? (Entrée = lancer, f 10 / pl6 12 / 7 5 pour parier, ? = aide) > ").strip().lower()
                if s in ('j', 'jeu'):
                    print(" Termine d'abord ce lancer.")
                    continue
                if commande_globale(etat, s):
                    continue
                if s in ('?', 'aide'):
                    aide_craps('point')
                    continue
                if s == '':
                    break
                nouveaux, erreur = lire_paris_craps(s, 'point')
                if erreur:
                    print(f" {erreur}")
                    continue
                total = sum(nouveaux.values())
                if total > etat['jetons']:
                    print(f" Pas assez de jetons ({fmt(total)} demandés).")
                    continue
                etat['jetons'] -= total
                engage += total
                for code, m in nouveaux.items():
                    if code in UN_COUP:
                        unique[code] = unique.get(code, 0) + m
                    else:
                        tenus[code] = tenus.get(code, 0) + m
                _afficher_table(point, ligne, plat, cote, tenus)
            tot = lancer_des()
            lignes = []
            _un_coup(etat, tot, unique, lignes)
            for code, m in list(tenus.items()):
                n = int(code[2:])
                if tot == n:
                    gain = round(m * PLACE[n], 2)
                    etat['jetons'] += gain
                    lignes.append(f" Place {n} : +{fmt(gain)} (la mise reste)")
                elif tot == 7:
                    lignes.append(f" Place {n} : perdu -{fmt(m)}")
                    del tenus[code]
            fini = tot in (7, point)
            if fini:
                if tot == point and ligne == 'p':
                    _payer(etat, plat, plat, "Pass line", lignes)
                    debloquer(etat, 'craps_pass')
                    if cote:
                        _payer(etat, cote, cote * num / den, "Cote libre", lignes)
                        debloquer(etat, 'craps_odds')
                elif tot == point and ligne == 'dp':
                    _payer(etat, plat, None, "Don't pass", lignes)
                    if cote:
                        _payer(etat, cote, None, "Cote (lay)", lignes)
                elif tot == 7 and ligne == 'p':
                    _payer(etat, plat, None, "Pass line", lignes)
                    if cote:
                        _payer(etat, cote, None, "Cote libre", lignes)
                else:
                    _payer(etat, plat, plat, "Don't pass", lignes)
                    if cote:
                        _payer(etat, cote, cote * den / num, "Cote (lay)", lignes)
                if tot == point:
                    lignes.append(f" Le point {point} est fait.")
                else:
                    lignes.append(" Sept : fin du lancer.")
                for code, m in tenus.items():
                    etat['jetons'] += m
                    lignes.append(f" Place {code[2:]} : mise rendue")
                tenus.clear()
            for l in lignes:
                print(l)
            if fini:
                break
            _afficher_table(point, ligne, plat, cote, tenus)
        etat['jetons'] = round(etat['jetons'], 2)
        print(f" Jetons : {fmt(etat['jetons'])}\n")
        return engage
    except Quitter:
        etat['jetons'] += plat + cote + sum(tenus.values()) + sum(unique.values())
        raise


# ============================================================ machine à sous

SYMBOLES = {'777': 1, 'BAR': 2, 'GEM': 3, 'BEL': 5, 'CHE': 7, 'LEM': 9, 'PLM': 10, 'WLD': 3, 'SCT': 1}
POOL = [s for s, n in SYMBOLES.items() for _ in range(n)]
# Retour théorique ~94 % (simulé sur 2 millions de tours, tours gratuits compris)
GAINS_SLOT = {
    '777': {3: 30, 4: 180, 5: 1200}, 'BAR': {3: 18, 4: 70, 5: 350}, 'GEM': {3: 12, 4: 48, 5: 240},
    'BEL': {3: 7, 4: 30, 5: 120}, 'CHE': {3: 5, 4: 18, 5: 70}, 'LEM': {3: 3, 4: 10, 5: 40},
    'PLM': {3: 3, 4: 10, 5: 36},
}
GAINS_SCATTER = {3: 2, 4: 10, 5: 50}  # x la mise totale
LIGNES = [(0, 0, 0, 0, 0), (1, 1, 1, 1, 1), (2, 2, 2, 2, 2), (0, 1, 2, 1, 0), (2, 1, 0, 1, 2)]
TOURS_GRATUITS = 8
MULT_GRATUIT = 2
RELANCE_TOURS = {3: 5, 4: 8, 5: 12}  # tours supplémentaires si 3 / 4 / 5 SCT pendant les tours gratuits
TOURS_MAX = 40


def tourner():
    """Grille [rouleau][rangée]."""
    return [[random.choice(POOL) for _ in range(3)] for _ in range(5)]


def gain_ligne(cases):
    premier = next((s for s in cases if s != 'WLD'), None)
    candidats = []
    prefixe = 0
    for s in cases:
        if s != 'WLD':
            break
        prefixe += 1
    if prefixe >= 3:
        candidats.append(GAINS_SLOT['777'].get(prefixe, 0))
    if premier in GAINS_SLOT:
        run = 0
        for s in cases:
            if s == premier or s == 'WLD':
                run += 1
            else:
                break
        if run >= 3:
            candidats.append(GAINS_SLOT[premier][run])
    return max(candidats) if candidats else 0


def evaluer_grille(grille):
    """Retourne (gains par ligne [(index, mult, symbole)], nb de scatters)."""
    gains = []
    for i, ligne in enumerate(LIGNES):
        cases = [grille[r][ligne[r]] for r in range(5)]
        m = gain_ligne(cases)
        if m:
            gains.append((i, m, cases))
    scatters = sum(1 for r in range(5) for c in grille[r] if c == 'SCT')
    return gains, scatters


def gain_total_slot(grille, mise, mult=1):
    gains, scatters = evaluer_grille(grille)
    par_ligne = mise / len(LIGNES)
    total = sum(par_ligne * m for _, m, _ in gains) * mult
    total += mise * GAINS_SCATTER.get(min(scatters, 5), 0) if scatters >= 3 else 0
    return total, gains, scatters


def afficher_grille_slot(grille):
    for row in range(3):
        print("   " + " | ".join(grille[r][row] for r in range(5)))


def animer(grille, passable=True):
    """Animation rouleau par rouleau. Entrée pendant le tirage : affichage immédiat (sauf bonus). True si sauté."""
    if not passable:
        vider_clavier()
        attente = lambda t: (dormir(t), False)[1]
    else:
        attente = dormir_ou_passer
    arret = []
    for stade in range(5):
        for _ in range(4):
            vue = arret + [random.choice(POOL) for _ in range(5 - stade)]
            print("\r   " + " | ".join(vue) + "   ", end="", flush=True)
            if attente(0.07):
                print("\r" + " " * 40 + "\r", end="")
                return True
        arret.append(grille[stade][1])
        print("\r   " + " | ".join(arret + ["   "] * (5 - len(arret))) + "   ", end="", flush=True)
        if attente(PAUSE * 0.4):
            print("\r" + " " * 40 + "\r", end="")
            return True
    print("\r" + " " * 40 + "\r", end="")
    if not passable:
        vider_clavier()
    return False


def lignes_aide_slots():
    out = [" Machine à sous 5 rouleaux x 3 rangées, 5 lignes (haut, milieu, bas, V, V inversé).",
           " Gains par ligne (x mise / 5), de gauche à droite avec 3 / 4 / 5 symboles :"]
    for sym, t in GAINS_SLOT.items():
        out.append(f"   {sym} : {t[3]} / {t[4]} / {t[5]}")
    out.append(" Pendant le tirage, appuie sur Entrée pour afficher le résultat tout de suite (fast spin).")
    out.append(" Le fast spin ne marche pas pendant les bonus (tours gratuits) ni pour le jackpot.")
    out.append(f" 3 / 4 / 5 SCT pendant les tours gratuits : +{RELANCE_TOURS[3]} / +{RELANCE_TOURS[4]} / +{RELANCE_TOURS[5]} tours (max {TOURS_MAX}).")
    out.append(f" WLD remplace tout sauf SCT. 3 / 4 / 5 SCT : {GAINS_SCATTER[3]}x / {GAINS_SCATTER[4]}x / "
               f"{GAINS_SCATTER[5]}x la mise totale + {TOURS_GRATUITS} tours gratuits (lignes x{MULT_GRATUIT}).")
    return out


def demander_slots(etat):
    while True:
        mise = demander_mise(etat)
        if mise is None:
            return None
        return mise


def jouer_slots(etat, mise):
    etat['jetons'] -= mise
    print()
    grille = tourner()
    total, gains, scatters = gain_total_slot(grille, mise)
    animer(grille, passable=(scatters < 3))  # le bonus ne se saute pas
    afficher_grille_slot(grille)
    _resume_slot(etat, mise, total, gains, scatters, grille)
    if scatters >= 3:
        debloquer(etat, 'slots_free')
        print(f"\n {TOURS_GRATUITS} tours gratuits (gains de lignes x{MULT_GRATUIT}) !")
        cumul = 0.0
        restants = TOURS_GRATUITS
        k = 0
        vider_clavier()
        while restants > 0:
            restants -= 1
            k += 1
            dormir(PAUSE * 0.5)
            g = tourner()
            t, gl, sc = gain_total_slot(g, mise, MULT_GRATUIT)
            if sc >= 3:
                t -= mise * GAINS_SCATTER.get(min(sc, 5), 0)  # le scatter ne paie pas en tour gratuit
            cumul += t
            etat['jetons'] += t
            if t:
                afficher_grille_slot(g)
            total_prevu = k + restants
            print(f" Tour gratuit {k}/{total_prevu} : {'+' + fmt(t) if t else 'rien'}")
            _verifier_slot(etat, mise, gl, t)
            if sc >= 3 and total_prevu < TOURS_MAX:
                en_plus = min(RELANCE_TOURS.get(min(sc, 5), 5), TOURS_MAX - total_prevu)
                restants += en_plus
                if not t:
                    afficher_grille_slot(g)
                dormir(0.6)
                print(f" {sc} SCT : +{en_plus} tours gratuits !")
                dormir(0.8)
        print(f" Tours gratuits : +{fmt(cumul)} ({k} tours)")
        vider_clavier()
    etat['jetons'] = round(etat['jetons'], 2)
    print(f" Jetons : {fmt(etat['jetons'])}\n")
    return mise


def _verifier_slot(etat, mise, gains, total):
    if any(m == 1200 for _, m, _ in gains):
        debloquer(etat, 'slots_777')
    if total >= 100 * mise:
        debloquer(etat, 'slots_x100')


def _resume_slot(etat, mise, total, gains, scatters, grille):
    for i, m, cases in gains:
        print(f" Ligne {i + 1} : {' '.join(cases)} = {fmt(mise / len(LIGNES) * m)}")
    if scatters >= 3:
        print(f" {scatters} SCT : +{fmt(mise * GAINS_SCATTER[min(scatters, 5)])}")
    etat['jetons'] += total
    if total:
        print(f" Gagné +{fmt(round(total, 2))}")
    else:
        print(f" Perdu -{fmt(mise)}")
    _verifier_slot(etat, mise, gains, total)


# ============================================================ crash

def touche_pressee():
    if msvcrt is None:
        return False
    if msvcrt.kbhit():
        while msvcrt.kbhit():
            msvcrt.getch()
        return True
    return False


def point_de_crash():
    u = random.random()
    cp = 0.97 / (1 - u)
    return min(1000.0, max(1.0, math.floor(cp * 100) / 100))


def demander_crash(etat):
    mise = demander_mise(etat)
    if mise is None:
        return None
    while True:
        if msvcrt is not None:
            invite = "Retrait auto à (ex : 2 = 2.00x, Entrée = manuel : une touche encaisse) > "
        else:
            invite = "Retrait auto à (ex : 2 = 2.00x, Entrée = 2) > "
        s = input(invite).strip().lower().replace('x', '').replace(',', '.')
        if s in ('q', 'quit', 'exit'):
            raise Quitter
        if s == '':
            return mise, (None if msvcrt is not None else 2.0)
        try:
            cible = float(s)
        except ValueError:
            print(" Un nombre supérieur à 1, par exemple 2.5")
            continue
        if cible <= 1.0:
            print(" Un nombre supérieur à 1, par exemple 2.5")
            continue
        return mise, cible


def jouer_crash(etat, choix):
    mise, cible = choix
    etat['jetons'] -= mise
    cp = point_de_crash()
    print()
    pause()
    if cible is None:
        while msvcrt is not None and msvcrt.kbhit():
            msvcrt.getch()
        print(" Appuie sur une touche pour encaisser.")
    t = 0.0
    mult = 1.0
    encaisse = None
    while True:
        mult = math.floor(math.exp(0.12 * t) * 100) / 100
        if mult >= cp:
            break
        if cible is not None and mult >= cible:
            encaisse = cible
            break
        if cible is None and t > 0 and touche_pressee():
            encaisse = mult
            break
        print(f"\r Multiplicateur : {mult:7.2f}x", end="", flush=True)
        dormir(0.1)
        t += 0.1
    print("\r" + " " * 40 + "\r", end="")
    if encaisse is not None:
        gain = round(mise * encaisse, 2)
        etat['jetons'] += gain
        print(f" Encaissé à {encaisse:.2f}x : +{fmt(round(gain - mise, 2))}")
        print(f" Le crash est tombé à {cp:.2f}x")
        if encaisse >= 10:
            debloquer(etat, 'crash_x10')
        if encaisse >= 100:
            debloquer(etat, 'crash_x100')
    else:
        pause()
        print(f" Crash à {cp:.2f}x ! Perdu -{fmt(mise)}")
    etat['jetons'] = round(etat['jetons'], 2)
    print(f" Jetons : {fmt(etat['jetons'])}\n")
    return mise


# ============================================================ tournoi

def demander_tournoi():
    s = input(f"Tournoi : nombre de manches (Entrée = {TOURNOI_DEFAUT}) > ").strip().lower()
    if s in ('q', 'quit', 'exit'):
        return 0
    n = lire_montant(s) if s else TOURNOI_DEFAUT
    if n is None or n < 5:
        print(" Au moins 5 manches.")
        return 0
    return min(n, 500)


def ligne_tournoi(etat):
    t = etat['tournoi']
    rec = etat.get('record_tournoi', {}).get(str(t['max']))
    return (f"Tournoi : manche {t['jouees'] + 1}/{t['max']} | "
            f"{'record ' + fmt(rec) if rec else 'aucun record pour cette durée'}")


def maj_save(f):
    data = charger() or {}
    f(data)
    try:
        with open(SAVE, 'w', encoding='utf-8') as fh:
            json.dump(data, fh)
    except OSError:
        pass


def bilan_tournoi(etat):
    t = etat.get('tournoi')
    if not t:
        return
    if t['jouees'] < t['max'] and etat['jetons'] >= 1:
        print("Tournoi abandonné : pas de record ni de prime.\n")
        return
    score = int(etat['jetons'])
    prime = min(5000, max(0, (score - DEPART) // 10))
    objectifs = ['tournoi_fini']
    if score >= 3000:
        objectifs.append('tournoi_x3')
    if score >= 10000:
        objectifs.append('tournoi_x10')
    resultat = {}

    def appliquer(data):
        records = data.setdefault('record_tournoi', {})
        cle = str(t['max'])
        ancien = records.get(cle, 0)
        resultat['record'] = score > ancien
        resultat['ancien'] = ancien
        records[cle] = max(ancien, score)
        faits = set(data.get('objectifs', []))
        nouveaux = [o for o in objectifs if o not in faits]
        primes = sum(RECOMPENSES.get(o, 0) for o in nouveaux)
        data['objectifs'] = sorted(faits | set(nouveaux))
        data['jetons'] = data.get('jetons', DEPART) + prime + primes
        data['record'] = max(data.get('record', DEPART), data['jetons'])
        resultat['nouveaux'] = nouveaux
        resultat['primes'] = primes

    maj_save(appliquer)
    print(f"Tournoi terminé : {fmt(score)} jetons en {t['max']} manches.")
    if resultat['record']:
        print(f"Nouveau record pour {t['max']} manches (ancien : {fmt(resultat['ancien'])}).")
    else:
        print(f"Record pour {t['max']} manches : {fmt(resultat['ancien'])}.")
    print(f"Prime versée sur ta réserve : +{fmt(prime)} jetons")
    for o in resultat['nouveaux']:
        print(f"Objectif atteint : {LIBELLES.get(o, o)} (+{fmt(RECOMPENSES.get(o, 0))} jetons)")
    print()


# ============================================================ branchement dans run_game

def initialiser(etat, save):
    """Prépare les états des extensions au début d'une session de casino."""
    save = save or {}
    tournoi = etat.get('tournoi')
    etat['jackpot'] = 0 if tournoi else max(POT_DEPART, save.get('jackpot', POT_DEPART))
    etat['record_tournoi'] = save.get('record_tournoi', {})
    etat['compte_session'] = {}
    etat['dr_actif'] = save.get('dr_actif', True)
    etat['dr_serie'] = 0
    etat['hilo'] = False
    etat['hilo_stats'] = dict(save.get('hilo_stats', {'ok': 0, 'total': 0, 'serie': 0, 'record': 0}))
    etat['cumul'].setdefault('hilo_ok', 0)
    etat['defi_fait'] = save.get('defi_fait', '')
    etat['defi'] = None if tournoi else defi_du_jour()
    if not tournoi:
        if len(etat['objectifs']) >= len(OBJECTIFS) - 1:
            debloquer(etat, 'platine')
        afficher_defi(etat)


def donnees_extra(etat):
    return {'jackpot': etat.get('jackpot', POT_DEPART), 'record_tournoi': etat.get('record_tournoi', {}),
            'dr_actif': etat.get('dr_actif', True), 'hilo_stats': etat.get('hilo_stats', {}),
            'defi_fait': etat.get('defi_fait', '')}


def avant_mise(etat):
    """Appelé à chaque tour de boucle : les questions ne tombent qu'une fois par manche."""
    if not etat.get('_manche_finie', True):
        return
    etat['_manche_finie'] = False
    questions_hilo(etat)


def apres_gain(etat, engage, net_prov):
    """Double ou rien sur le gain, puis alimentation du jackpot."""
    if net_prov > 0:
        double_ou_rien(etat, net_prov)
    jackpot(etat, engage)


def fin_manche(etat):
    """Suivi de fin de manche. Retourne True si le tournoi est terminé."""
    etat['_manche_finie'] = True
    j = etat['jeu']
    etat['compte_session'][j] = etat['compte_session'].get(j, 0) + 1
    t = etat.get('tournoi')
    if t:
        t['jouees'] += 1
        if t['jouees'] >= t['max']:
            print(f" Dernière manche jouée ({t['max']}/{t['max']}).\n")
            return True
        return False
    verifier_defi(etat)
    return False


def afficher_extra(etat):
    if etat.get('tournoi'):
        print(ligne_tournoi(etat))
        return
    print(f"Jackpot progressif : {fmt(etat.get('jackpot', POT_DEPART))}")
    print(f"  3 % de chaque mise l'alimente. Chaque manche (mise >= {JACKPOT_MIN}) le tire au sort : "
          f"chance = mise / {JACKPOT_DIVISEUR:,} (mise 100 = 1 sur {JACKPOT_DIVISEUR // 100}), plafonnée à une mise de {JACKPOT_PLAFOND}.".replace(',', ' '))
    afficher_defi(etat)
    s = etat.get('hilo_stats')
    if s and s['total']:
        print(f"Hi-Lo : {s['ok']}/{s['total']} (série {s['serie']}, record {s['record']}) | "
              f"{'actif' if etat.get('hilo') else 'désactivé'} (hl)")
    print(f"Double ou rien : {'activé' if etat.get('dr_actif', True) else 'désactivé'} (dr)")
