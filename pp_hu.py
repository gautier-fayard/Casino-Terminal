import random
import time

import pp_poker as PK

STACK = 100.0
SB = 0.5
BB = 1.0
POSITIONS = ('hero', 'bot')

STYLES = {
    'serre': {
        'nom': 'Serré', 'ouvre': 0.57, 'limp': 0.50, 'trois_bet': 0.74, 'valeur': 0.68, 'bluff': 0.03,
        'bluff_relance': 0.01, 'marge': 0.08, 'respect': 0.15, 'agg': 0.55, 'taille': (0.5, 0.66),
        'desc': "joue peu de mains, relance surtout avec du solide, se couche facilement face à la pression",
    },
    'agressif': {
        'nom': 'Agressif', 'ouvre': 0.45, 'limp': 0.40, 'trois_bet': 0.62, 'valeur': 0.58, 'bluff': 0.22,
        'bluff_relance': 0.10, 'marge': 0.03, 'respect': 0.07, 'agg': 0.85, 'taille': (0.66, 1.0),
        'desc': "relance beaucoup, mise gros, met la pression même sans main",
    },
    'bluffeur': {
        'nom': 'Bluffeur', 'ouvre': 0.42, 'limp': 0.38, 'trois_bet': 0.64, 'valeur': 0.62, 'bluff': 0.45,
        'bluff_relance': 0.22, 'marge': 0.0, 'respect': 0.04, 'agg': 0.75, 'taille': (0.5, 1.2),
        'desc': "mise très souvent avec des mains faibles, relance en bluff, se fait payer par de la valeur",
    },
}
ORDRE_STYLES = ['serre', 'agressif', 'bluffeur']


class Sortie(Exception):
    pass


def fmt(x):
    x = round(x, 2)
    if x == int(x):
        return str(int(x))
    return f"{x:.1f}" if abs(x * 10 - round(x * 10)) < 1e-9 else f"{x:.2f}"


def lire(invite):
    s = input(invite).strip().lower()
    if s in ('q', 'quit', 'exit'):
        raise Sortie
    return s


_BASE = None
_CACHE_PREFLOP = {}


def base_paquet():
    global _BASE
    if _BASE is None:
        _BASE = PK.paquet_complet()
    return _BASE


def equite(hero, board, n=160):
    vus = {c[1] for c in hero + board}
    base = [c for c in base_paquet() if c[1] not in vus]
    manque = 5 - len(board)
    gain = 0.0
    for _ in range(n):
        t = random.sample(base, 2 + manque)
        b = board + t[2:]
        a = PK.evaluer_7(hero + b)
        o = PK.evaluer_7(t[:2] + b)
        gain += 1 if a > o else 0.5 if a == o else 0
    return gain / n


def equite_preflop(hero):
    a, b = sorted(hero, key=lambda c: c[2], reverse=True)
    cle = (a[2], b[2], a[3] == b[3])
    if cle not in _CACHE_PREFLOP:
        _CACHE_PREFLOP[cle] = equite(hero, [], 260)
    return _CACHE_PREFLOP[cle]


def equite_main(cartes, board):
    if not board:
        return equite_preflop(cartes)
    return equite(cartes, board)


def nouvelle_main(bouton):
    paquet = base_paquet()[:]
    random.shuffle(paquet)
    bb = 'bot' if bouton == 'hero' else 'hero'
    m = {
        'bouton': bouton, 'bb': bb, 'cartes': {'hero': paquet[:2], 'bot': paquet[2:4]},
        'reste': paquet[4:], 'board': [], 'stack': {'hero': STACK, 'bot': STACK},
        'mr': {'hero': 0.0, 'bot': 0.0}, 'total': {'hero': 0.0, 'bot': 0.0}, 'pot': 0.0,
        'fold': None, 'log': [], 'actions_bot': [], 'relance_min': BB,
    }
    poster(m, bouton, SB)
    poster(m, bb, BB)
    return m


def poster(m, j, montant):
    v = min(montant, m['stack'][j])
    m['stack'][j] -= v
    m['mr'][j] += v
    m['total'][j] += v
    m['pot'] += v


def autre(j):
    return 'bot' if j == 'hero' else 'hero'


def afficher_table(m, rue):
    b = PK.cartes_poker(m['board']) if m['board'] else "-"
    print(f"\n {rue.upper()} | Board : {b}")
    print(f" Pot : {fmt(m['pot'])} bb | Toi : {fmt(m['stack']['hero'])} bb | Bot : {fmt(m['stack']['bot'])} bb"
          f" | {'Tu es au bouton' if m['bouton'] == 'hero' else 'Le bot est au bouton'}")
    print(f" Ta main : {PK.cartes_poker(m['cartes']['hero'])}")


def borne_relance(m, j):
    o = autre(j)
    mini = m['mr'][o] + max(m['relance_min'], BB)
    maxi = m['mr'][j] + m['stack'][j]
    return min(mini, maxi), maxi


def decision_bot(m, style, relances, rue):
    s = STYLES[style]
    j, o = 'bot', 'hero'
    a_payer = m['mr'][o] - m['mr'][j]
    cartes = m['cartes']['bot']
    eq = equite_main(cartes, m['board'])
    pot = m['pot']
    mini, maxi = borne_relance(m, j)
    peut_relancer = m['stack'][o] > 0 and maxi > m['mr'][o] and relances < 4

    def taille_pot(f):
        cible = m['mr'][o] + a_payer + f * (pot + a_payer)
        return max(mini, min(maxi, round(cible * 2) / 2))

    if rue == 'preflop':
        if a_payer > 0 and m['mr'][o] <= BB + 1e-9 and m['bouton'] == 'bot':
            if eq >= s['ouvre'] or random.random() < s['bluff'] * 0.6:
                if peut_relancer:
                    return ('r', max(mini, min(maxi, 2.5 if random.random() < 0.7 else 3.0)))
                return ('c', 0)
            if eq >= s['limp']:
                return ('c', 0)
            return ('f', 0)
        if a_payer > 0:
            gros = m['mr'][o] / BB
            eq_adj = eq - s['respect'] * min(gros / 4, 1.5)
            if peut_relancer and eq_adj >= s['trois_bet'] and random.random() < s['agg']:
                return ('r', taille_pot(0.9))
            if peut_relancer and random.random() < s['bluff_relance'] and eq < 0.5:
                return ('r', taille_pot(0.9))
            req = a_payer / (pot + a_payer)
            if eq_adj >= req + s['marge'] * 0.5:
                return ('c', 0)
            return ('f', 0)
        if peut_relancer and (eq >= s['ouvre'] - 0.02 or random.random() < s['bluff'] * 0.8):
            return ('r', max(mini, min(maxi, 3.5)))
        return ('c', 0)

    if a_payer <= 0:
        if not peut_relancer and maxi <= m['mr'][o]:
            return ('c', 0)
        if eq >= s['valeur'] and random.random() < min(0.95, s['agg'] + 0.15):
            f = random.uniform(*s['taille'])
            return ('r', taille_pot(f))
        faible = eq < 0.38
        if faible and random.random() < s['bluff']:
            f = random.uniform(*s['taille'])
            return ('r', taille_pot(f))
        if rue != 'river' and 0.38 <= eq < s['valeur'] and random.random() < s['bluff'] * 0.6:
            return ('r', taille_pot(random.uniform(0.4, 0.66)))
        return ('c', 0)

    avant = max(pot - a_payer, 1.0)
    fraction = a_payer / avant
    eq_adj = eq - s['respect'] * min(fraction, 1.5)
    req = a_payer / (pot + a_payer)
    if peut_relancer and eq_adj >= s['valeur'] + 0.08 and random.random() < s['agg']:
        return ('r', taille_pot(random.uniform(0.7, 1.0)))
    if peut_relancer and random.random() < s['bluff_relance'] and eq < 0.35 and rue != 'river':
        return ('r', taille_pot(0.9))
    if eq_adj >= req + s['marge']:
        return ('c', 0)
    return ('f', 0)


def aide_hero(m, rue):
    j, o = 'hero', 'bot'
    a_payer = m['mr'][o] - m['mr'][j]
    print(" Aide :")
    if a_payer > 0:
        req = a_payer / (m['pot'] + a_payer)
        print(f"  Tu dois payer {fmt(a_payer)} bb pour un pot final de {fmt(m['pot'] + a_payer)} bb :"
              f" il te faut {req * 100:.0f} % d'équité pour que le call soit rentable.")
    else:
        print("  Personne n'a misé : tu peux checker (c) ou miser (r X, h = demi-pot, p = pot).")
    if m['board']:
        n, txt = PK.texte_outs(m['cartes']['hero'], m['board'])
        print(f"  Ta main : {PK.nom_main(PK.evaluer_7(m['cartes']['hero'] + m['board']))}. Outs : {txt}")
        if n and len(m['board']) in (3, 4):
            print(f"  Chance de toucher ≈ {PK.estimation_regle(n, m['board'])} % (règle du 4 et du 2).")
    else:
        print("  Préflop heads-up : le bouton (petite blinde) parle en premier et joue plus de la moitié des mains.")
    print("  Actions : f = fold | c = check ou call | r X = relance à X bb au total sur cette rue |")
    print("            h = demi-pot | p = pot | a = tout-in | q = arrêter et voir le bilan")


def action_hero(m, rue):
    j, o = 'hero', 'bot'
    a_payer = m['mr'][o] - m['mr'][j]
    mini, maxi = borne_relance(m, j)
    peut = m['stack'][o] > 0 and maxi > m['mr'][o]
    if a_payer > 0:
        invite = f"A toi : payer {fmt(a_payer)} bb (f, c, r X, h, p, a, ? = aide) > "
    else:
        invite = "A toi : check ou miser (c, r X, h, p, a, ? = aide) > "
    while True:
        s = lire(invite)
        if s == '?':
            aide_hero(m, rue)
            continue
        if s in ('f', 'fold'):
            if a_payer <= 0:
                print(" Tu peux checker gratuitement (c), pas besoin de te coucher.")
                continue
            return ('f', 0)
        if s in ('c', 'check', 'call', ''):
            return ('c', 0)
        cible = None
        if s in ('a', 'allin', 'tapis'):
            cible = maxi
        elif s in ('h', 'demi'):
            cible = m['mr'][o] + a_payer + 0.5 * (m['pot'] + a_payer)
        elif s in ('p', 'pot'):
            cible = m['mr'][o] + a_payer + (m['pot'] + a_payer)
        else:
            morceaux = s.replace(',', '.').split()
            if morceaux and morceaux[0] in ('r', 'b', 'bet', 'raise') and len(morceaux) == 2:
                try:
                    cible = float(morceaux[1])
                except ValueError:
                    cible = None
        if cible is None:
            print(" f, c, r X, h, p, a ou ? pour l'aide.")
            continue
        if not peut:
            print(" Relance impossible ici : le bot est déjà à tapis, tu peux seulement payer (c) ou te coucher (f).")
            continue
        cible = round(cible * 2) / 2
        if cible < mini - 1e-9:
            print(f" Relance minimale : {fmt(mini)} bb au total sur cette rue.")
            continue
        cible = min(cible, maxi)
        return ('r', cible)


def appliquer(m, j, act):
    o = autre(j)
    a_payer = m['mr'][o] - m['mr'][j]
    if act[0] == 'f':
        m['fold'] = j
        return 'fold'
    if act[0] == 'c':
        v = min(a_payer, m['stack'][j])
        if v > 0:
            poster(m, j, v)
            return 'call'
        return 'check'
    cible = act[1]
    v = cible - m['mr'][j]
    m['relance_min'] = max(cible - m['mr'][o], BB)
    poster(m, j, v)
    return 'bet' if m['mr'][o] == 0 else 'raise'


def texte_action(m, j, genre, act):
    qui = "Tu" if j == 'hero' else "Le bot"
    if genre == 'fold':
        return f" {qui} {'te couches' if j == 'hero' else 'se couche'}."
    if genre == 'check':
        return f" {qui} {'checkes' if j == 'hero' else 'checke'}."
    if genre == 'call':
        return f" {qui} {'paies' if j == 'hero' else 'paie'}."
    verbe = 'mises' if genre == 'bet' else 'relances'
    if j == 'bot':
        verbe = 'mise' if genre == 'bet' else 'relance'
    tout = " (tout-in)" if m['stack'][j] <= 0 else ""
    return f" {qui} {verbe} à {fmt(m['mr'][j])} bb{tout}."


def tour_encheres(m, rue, style, stats):
    ordre = [m['bouton'], m['bb']] if rue == 'preflop' else [m['bb'], m['bouton']]
    agi = {'hero': False, 'bot': False}
    relances = 0
    i = 0
    if rue != 'preflop':
        m['relance_min'] = BB
    while True:
        if m['fold']:
            return
        j = ordre[i % 2]
        o = autre(j)
        egal = abs(m['mr'][j] - m['mr'][o]) < 1e-9
        if egal and agi['hero'] and agi['bot']:
            return
        if m['stack']['hero'] <= 0 and m['stack']['bot'] <= 0:
            return
        if m['stack'][j] <= 0:
            if m['mr'][o] <= m['mr'][j] + 1e-9:
                return
            i += 1
            continue
        if m['stack'][o] <= 0 and egal:
            return
        if j == 'hero':
            afficher_etat_decision(m, rue)
            avant = {'a_payer': m['mr'][o] - m['mr'][j], 'pot': m['pot'], 'rue': rue,
                     'board': list(m['board']), 'cartes': list(m['cartes']['hero'])}
            act = action_hero(m, rue)
        else:
            time.sleep(0.5)
            act = decision_bot(m, style, relances, rue)
        genre = appliquer(m, j, act)
        agi[j] = True
        if genre in ('bet', 'raise'):
            relances += 1
            agi[o] = False
        if j == 'hero':
            avant['action'] = genre
            avant['montant'] = m['mr'][j]
            m['log'].append(avant)
            stats['hero_actions'][genre] = stats['hero_actions'].get(genre, 0) + 1
        else:
            m['actions_bot'].append((rue, genre))
            stats['bot_actions'][genre] = stats['bot_actions'].get(genre, 0) + 1
        print(texte_action(m, j, genre, act))
        i += 1


def afficher_etat_decision(m, rue):
    o = 'bot'
    a_payer = m['mr'][o] - m['mr']['hero']
    print(f"   Pot {fmt(m['pot'])} bb | tes {fmt(m['stack']['hero'])} bb | {'à payer ' + fmt(a_payer) + ' bb' if a_payer > 0 else 'rien à payer'}")


def distribuer_board(m, nb):
    for _ in range(nb):
        m['board'].append(m['reste'].pop(0))


def fin_rue(m):
    m['mr'] = {'hero': 0.0, 'bot': 0.0}


def jouer_main(numero, bouton, style, stats):
    m = nouvelle_main(bouton)
    print(f"\n{'=' * 60}\n Main {numero}")
    print(f" Tu es {'au bouton (petite blinde 0,5)' if bouton == 'hero' else 'en grosse blinde (1)'}.")
    afficher_table(m, 'preflop')
    rues = [('preflop', 0), ('flop', 3), ('turn', 1), ('river', 1)]
    for rue, nb in rues:
        if m['fold']:
            break
        if rue != 'preflop':
            distribuer_board(m, nb)
            fin_rue(m)
            if m['stack']['hero'] > 0 and m['stack']['bot'] > 0:
                afficher_table(m, rue)
        if m['stack']['hero'] > 0 and m['stack']['bot'] > 0:
            tour_encheres(m, rue, style, stats)
    gagnant = None
    if m['fold']:
        gagnant = autre(m['fold'])
        showdown = False
    else:
        while len(m['board']) < 5:
            distribuer_board(m, 1)
        showdown = True
        print(f"\n Board final : {PK.cartes_poker(m['board'])}")
        print(f" Ta main : {PK.cartes_poker(m['cartes']['hero'])} ({PK.nom_main(PK.evaluer_7(m['cartes']['hero'] + m['board']))})")
        print(f" Bot : {PK.cartes_poker(m['cartes']['bot'])} ({PK.nom_main(PK.evaluer_7(m['cartes']['bot'] + m['board']))})")
        a = PK.evaluer_7(m['cartes']['hero'] + m['board'])
        b = PK.evaluer_7(m['cartes']['bot'] + m['board'])
        gagnant = 'hero' if a > b else 'bot' if b > a else None
    if gagnant is None:
        gain = {'hero': m['pot'] / 2, 'bot': m['pot'] / 2}
        print(" Égalité, pot partagé.")
    else:
        gain = {'hero': 0.0, 'bot': 0.0}
        gain[gagnant] = m['pot']
        if gagnant == 'hero':
            print(f" Tu gagnes {fmt(m['pot'] - m['total']['hero'])} bb.")
        else:
            print(f" Le bot gagne le pot : tu perds {fmt(m['total']['hero'])} bb.")
    net = gain['hero'] - m['total']['hero']
    stats['net'] += net
    stats['mains'] += 1
    if showdown:
        stats['showdowns'] += 1
        if gagnant == 'hero':
            stats['showdowns_gagnes'] += 1
    if gagnant == 'hero':
        stats['gagnees'] += 1
    if m['fold'] == 'bot':
        stats['bot_fold'] += 1
    if m['fold'] == 'hero':
        stats['hero_fold'] += 1
    stats['mains_log'].append({'numero': numero, 'net': net, 'log': m['log'], 'showdown': showdown,
                               'cartes': list(m['cartes']['hero']), 'board': list(m['board']),
                               'bot': list(m['cartes']['bot']), 'fold': m['fold'], 'gagnant': gagnant})
    print(f" Résultat de la main : {'+' if net >= 0 else ''}{fmt(net)} bb | Total : {'+' if stats['net'] >= 0 else ''}{fmt(stats['net'])} bb")
    return m


def analyser(stats):
    fautes = []
    for h in stats['mains_log']:
        for d in h['log']:
            if 'eq' not in d:
                d['eq'] = equite_main(d['cartes'], d['board']) if d['cartes'] else 0.5
            eq = d['eq']
            a_payer = d['a_payer']
            pot = d['pot']
            act = d['action']
            desc_main = PK.cartes_poker(d['cartes'])
            desc_board = PK.cartes_poker(d['board']) if d['board'] else "préflop"
            if a_payer > 0:
                avant = max(pot - a_payer, 1.0)
                fraction = a_payer / avant
                req = a_payer / (pot + a_payer)
                if d['rue'] == 'preflop':
                    adj = eq - 0.03 * min(fraction, 1.5)
                    marge_fold = 0.05
                else:
                    adj = eq - 0.07 * min(fraction, 1.5)
                    marge_fold = 0.10
                if act == 'call' and adj < req - 0.06:
                    fautes.append(('call_large', h['numero'], desc_main, desc_board, d['rue'],
                                   f"Call trop large : il fallait {req * 100:.0f} % d'équité et ta main en avait environ {adj * 100:.0f} %."))
                elif act == 'fold' and adj > req + marge_fold:
                    fautes.append(('fold_serre', h['numero'], desc_main, desc_board, d['rue'],
                                   f"Fold alors que la cote te le permettait : il fallait {req * 100:.0f} % et tu avais environ {adj * 100:.0f} %."))
            else:
                if act == 'check' and d['rue'] != 'preflop' and eq >= 0.74:
                    fautes.append(('passif', h['numero'], desc_main, desc_board, d['rue'],
                                   f"Check avec une main forte (≈ {eq * 100:.0f} % d'équité) : une mise de valeur rapportait plus."))
                if act in ('bet', 'raise') and d['rue'] == 'river' and eq < 0.22 and d['montant'] > 0.9 * pot:
                    fautes.append(('bluff_gros', h['numero'], desc_main, desc_board, d['rue'],
                                   f"Bluff de grosse taille sur la river avec presque aucune chance de gagner au showdown (≈ {eq * 100:.0f} %)."))
                if d['rue'] == 'preflop' and act == 'fold' and eq >= 0.48:
                    fautes.append(('fold_serre', h['numero'], desc_main, desc_board, d['rue'],
                                   f"Fold au bouton avec {desc_main} : en heads-up cette main (≈ {eq * 100:.0f} % contre une main au hasard) se joue."))
    return fautes


CONSEILS = {
    'call_large': "Tu paies trop de mises avec des mains qui n'ont pas la cote. Avant de payer, calcule l'équité nécessaire (mise / pot final) et compare-la à tes outs.",
    'fold_serre': "Tu te couches trop souvent quand la cote te permet de continuer. Heads-up, les ranges sont larges : un call coûte peu pour la valeur du pot.",
    'passif': "Tu ne mises pas assez tes mains fortes. Une main à plus de 70 % d'équité doit en général construire le pot.",
    'bluff_gros': "Tes bluffs de river sont trop gros ou sans scénario crédible. Bluffe avec des mains qui ne peuvent pas gagner au showdown, avec une taille adaptée.",
}


def bilan(stats, style_vrai, style_cache):
    n = stats['mains']
    print(f"\n{'=' * 60}\n Bilan du heads-up")
    if n == 0:
        print(" Aucune main jouée.")
        return
    print(f" Mains : {n} | Résultat : {'+' if stats['net'] >= 0 else ''}{fmt(stats['net'])} bb"
          f" ({'+' if stats['net'] >= 0 else ''}{stats['net'] / n:.2f} bb par main)")
    print(f" Mains gagnées : {stats['gagnees']}/{n} | Showdowns gagnés : {stats['showdowns_gagnes']}/{stats['showdowns']}")
    print(f" Tu t'es couché {stats['hero_fold']} fois, le bot {stats['bot_fold']} fois.")
    ha = stats['hero_actions']
    ba = stats['bot_actions']
    ag_h = ha.get('bet', 0) + ha.get('raise', 0)
    ag_b = ba.get('bet', 0) + ba.get('raise', 0)
    tot_h = sum(ha.values()) or 1
    tot_b = sum(ba.values()) or 1
    print(f" Agressivité (mises et relances / actions) : toi {ag_h * 100 / tot_h:.0f} % | bot {ag_b * 100 / tot_b:.0f} %")
    if style_cache:
        print(" Calcul de ton analyse...")
    fautes = analyser(stats)
    print(f"\n Erreurs repérées : {len(fautes)}")
    if not fautes:
        print(" Aucune erreur nette détectée par l'analyse. Joue plus de mains pour voir apparaître des tendances.")
    else:
        genres = {}
        for f in fautes:
            genres[f[0]] = genres.get(f[0], 0) + 1
        for f in fautes[:10]:
            print(f"  Main {f[1]} ({f[4]}) : {f[2]} sur {f[3]}")
            print(f"    {f[5]}")
        if len(fautes) > 10:
            print(f"  ... et {len(fautes) - 10} autres.")
        print("\n Tendances :")
        for g, c in sorted(genres.items(), key=lambda x: -x[1]):
            print(f"  {c} x : {CONSEILS[g]}")
    print("\n Note : l'analyse estime ton équité contre une main au hasard avec une correction selon la taille de la mise."
          " C'est une aide, pas une vérité absolue.")


def demander_style():
    print("\n Heads-up Texas Hold'em contre un bot (100 bb, blindes 0,5 / 1, tapis rechargés à chaque main).")
    print(" Style du bot :")
    for i, k in enumerate(ORDRE_STYLES, 1):
        print(f"  {i}. {STYLES[k]['nom']} : {STYLES[k]['desc']}")
    print("  4. Mystère : style caché, tu devras le deviner à la fin")
    while True:
        s = input("Style (1-4, q = retour) > ").strip().lower()
        if s in ('q', 'quit', 'exit'):
            return None, False
        if s in ('1', '2', '3'):
            return ORDRE_STYLES[int(s) - 1], False
        if s == '4':
            return random.choice(ORDRE_STYLES), True


def demander_mains():
    while True:
        s = input("Nombre de mains (Entrée = 20, q = retour) > ").strip().lower()
        if s in ('q', 'quit', 'exit'):
            return None
        if s == '':
            return 20
        if s.isdigit() and 1 <= int(s) <= 500:
            return int(s)
        print(" Un nombre entre 1 et 500.")


def run_headsup():
    style, cache = demander_style()
    if style is None:
        return
    n = demander_mains()
    if n is None:
        return
    stats = {'net': 0.0, 'mains': 0, 'gagnees': 0, 'showdowns': 0, 'showdowns_gagnes': 0, 'bot_fold': 0,
             'hero_fold': 0, 'hero_actions': {}, 'bot_actions': {}, 'mains_log': []}
    bouton = random.choice(POSITIONS)
    try:
        for numero in range(1, n + 1):
            jouer_main(numero, bouton, style, stats)
            bouton = autre(bouton)
            if numero < n:
                lire("\nEntrée = main suivante, q = arrêter > ")
    except Sortie:
        pass
    bilan(stats, style, cache)
    if cache:
        while True:
            s = input("\nQuel style avait le bot ? (1 serré, 2 agressif, 3 bluffeur) > ").strip().lower()
            if s in ('1', '2', '3'):
                break
            if s in ('q', ''):
                s = None
                break
        vrai = STYLES[style]['nom']
        if s and ORDRE_STYLES[int(s) - 1] == style:
            print(f" Bien vu : c'était un bot {vrai.lower()}.")
        else:
            print(f" C'était un bot {vrai.lower()} : {STYLES[style]['desc']}.")
    print()
