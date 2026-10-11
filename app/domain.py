"""Règles du parcours Combat individuel. Indépendant du serveur HTTP."""
from collections import defaultdict
from datetime import date
import math
import copy
import secrets
import time
import uuid

GRADES = ["Ceinture blanche", "Premier cap", "Deuxième cap", "Troisième cap", "Ceinture bleue", "Ceinture noire"]
DISCIPLINES = ["Combat", "Kata", "Lutte", "Kata Arme", "Combat équipe", "Kata synchro"]
AGES = ["Mini-poussins", "Poussins", "Pupilles", "Benjamins", "Minimes", "Cadets", "Juniors", "Seniors"]
WEIGHTS = {
    "F": [[25,35],[25,35],[25,30,35,40,45],[30,35,40,45,50],[35,40,45,50,55],[47,54,61],[48,53,59,66],[50,55,61,68]],
    "M": [[25,35],[25,35],[25,30,35,40,45,50],[30,35,40,45,50,55],[35,40,45,50,55,60,65],[52,57,63,70],[55,61,68,76],[60,67,75,84]],
}
POINTS = {"1":5, "2":5, "3":3, "4":2, "5":1}

class RuleError(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise RuleError(message)

def uid():
    return uuid.uuid4().hex

def integer(v, low, high, label):
    require(type(v) is int and low <= v <= high, f"{label} : entier entre {low} et {high}.")
    return v

def new_competition(name, day, season, owner):
    date.fromisoformat(day)
    integer(season, 2020, 2100, "Saison")
    return dict(id=uid(), name=name, date=day, season=season, owner=owner, code=secrets.token_hex(6).upper(),
                open=["Combat"], weights=copy.deepcopy(WEIGHTS), people=[], areas=[], officials=[], tables=[])

def age_index(p, c):
    age = c["season"] - date.fromisoformat(p["birth"]).year
    require(4 <= age <= 120, "Âge hors catégories.")
    return min((age - 4) // 2, 7)

def category(p, c):
    index = age_index(p, c)
    bounds = c["weights"][p["sex"]][index]
    weight = next((f"−{v:g} kg" for v in bounds if p["weight"] < v), f"{bounds[-1]:g} kg et +")
    return f'{p["sex"]} · {AGES[index]} · {weight}'

def pair(ids, people, rng=None):
    """Tirage par clubs : minimise les duels intra-club après choix de l'isolé."""
    rng = rng or secrets.SystemRandom()
    ids = list(ids)
    rng.shuffle(ids)
    spare = ids.pop() if len(ids) % 2 else None
    groups = defaultdict(list)
    for pid in ids:
        groups[people[pid]["club"]].append(pid)
    out = []
    while any(groups.values()):
        clubs = [k for k in groups if groups[k]]
        rng.shuffle(clubs)
        clubs.sort(key=lambda k: len(groups[k]), reverse=True)
        a = groups[clubs[0]].pop()
        b = groups[clubs[1] if len(clubs) > 1 else clubs[0]].pop()
        out.append((a, b))
    return out, spare

def match(a, b, turn, kind="main"):
    return dict(id=uid(), a=a, b=b, turn=turn, kind=kind, state="pending", rounds=[],
                sa=0, sb=0, winner=None, loser=None, reason=None, votes=None, timer=None)

def generate(c, discipline="Combat"):
    require(discipline in ("Combat","Lutte"), "Discipline non disponible.")
    require(not any(t["discipline"]==discipline for t in c["tables"]), "Les tableaux ont déjà été générés.")
    require(discipline not in c["open"], "Fermez d’abord les inscriptions "+discipline+".")
    groups = defaultdict(list)
    for p in c["people"]:
        if p["status"] == "approved" and discipline in p["disciplines"]:
            groups[category(p, c)].append(p["id"])
    require(groups, "Aucune inscription approuvée pour cette discipline.")
    for label, ids in sorted(groups.items()):
        c["tables"].append(dict(id=uid(), name=label, discipline=discipline, members=ids, status="draft",
            matches=[], turn=0, spare=None, area=None, judges=[], referee=None, rounds=2, seconds=60,
            rest=30, started=None, closed=None, places={}, repechages=[]))

def draw(c, t):
    require(t["status"] == "draft", "Le tirage est définitif.")
    require(len(t["members"]) >= 2, "Fusionnez cette catégorie avant le tirage.")
    pairs, spare = pair(t["members"], {p["id"]:p for p in c["people"]})
    t.update(turn=1, spare=spare, status="ready", matches=[match(a,b,1) for a,b in pairs])

def best_loser(c, matches, excluded=(), discipline="Combat"):
    excluded = set(excluded) | {m["loser"] for m in matches if m["state"] == "done" and m["reason"] != "points"}
    eligible = [m for m in matches if m["state"] == "done" and m["reason"] == "points" and m["loser"] not in excluded]
    require(eligible, "Aucun perdant éligible au repêchage. Décision de l’organisation nécessaire.")
    people = {p["id"]:p for p in c["people"]}
    def key(m):
        p = people[m["loser"]]
        criterion = -fight_time(m) if discipline=="Lutte" else abs(m["sa"]-m["sb"])
        return criterion, p["grade"], -date.fromisoformat(p["birth"]).toordinal()
    best = min(map(key, eligible))
    return secrets.choice([m["loser"] for m in eligible if key(m) == best])

def start_table(c, t):
    require(t["status"] == "ready", "Le tableau doit être prêt.")
    require(t["seconds"] > 0, "Configurez la durée des rounds avant de lancer ce tableau.")
    area = next((a for a in c["areas"] if a["id"] == t["area"]), None)
    require(area and area["assistant"], "Affectez une aire et un assistant.")
    require(t["referee"] and (not t["judges"] if t["discipline"]=="Lutte" else len(t["judges"])==3), "Affectez l’arbitre central et les juges requis par la discipline.")
    for other in c["tables"]:
        if other["status"] != "active":
            continue
        require(other["area"] != t["area"], "Cette aire accueille déjà un tableau.")
        require(not (set(t["judges"]+[t["referee"]]) & set(other["judges"]+[other["referee"]])),
                "Un officiel est déjà affecté à un tableau en cours.")
    t.update(status="active", started=time.time())

def advance(c, t):
    require(t["status"] == "active", "Le tableau doit être en cours.")
    current = [m for m in t["matches"] if m["turn"] == t["turn"] and m["kind"] != "bronze"]
    require(current and all(m["state"] == "done" for m in current), "Terminez les combats du tour.")
    if t["spare"]:
        pid = best_loser(c, current, discipline=t["discipline"])
        t["matches"].append(match(t["spare"], pid, t["turn"], "odd"))
        t["repechages"].append(dict(turn=t["turn"], participant=pid, kind="combat complémentaire"))
        t["spare"] = None
        return
    winners = [m["winner"] for m in current]
    require(len(set(winners)) == len(winners), "Double qualification incohérente.")
    if len(winners) == 1:
        bronze = [m for m in t["matches"] if m["kind"] == "bronze"]
        require(not bronze or bronze[0]["state"] == "done", "Terminez le combat de classement.")
        t["places"] = {"1":current[0]["winner"], "2":current[0]["loser"]}
        if bronze:
            t["places"].update({"3":bronze[0]["winner"], "4":bronze[0]["loser"]})
        # Trois inscrits : pas de place 3 automatique, règle non encore validée.
        quarters = [m for m in t["matches"] if m["turn"] == t["turn"]-2 and m["kind"] != "bronze"]
        if quarters:
            try:
                t["places"]["5"] = best_loser(c, quarters, t["places"].values(), t["discipline"])
            except RuleError:
                pass
        t.update(status="closed", closed=time.time())
        return
    if len(winners) % 2:
        pid = best_loser(c, current, winners, t["discipline"])
        winners.append(pid)
        t["repechages"].append(dict(turn=t["turn"], participant=pid, kind="qualification"))
    t["turn"] += 1
    if len(winners) == 2:
        losers = list(dict.fromkeys(m["loser"] for m in current if m["loser"] not in winners))
        if len(losers) == 2:
            t["matches"].append(match(*losers, t["turn"], "bronze"))
    t["matches"] += [match(winners[i],winners[i+1],t["turn"]) for i in range(0,len(winners),2)]

def elapsed(timer, now=None):
    if not timer:
        return 0
    return timer["elapsed"] + (max(0,(time.time() if now is None else now)-timer["since"]) if timer["running"] else 0)

def fight_time(m):
    if "fight_elapsed" in m:
        return m["fight_elapsed"]
    return elapsed(m.get("timer"))

def bank_time(m):
    timer=m.get("timer")
    if timer and m["state"] in ("running","paused"):
        seconds=elapsed(timer)
        if timer["duration"] is not None:
            seconds=min(seconds,timer["duration"])
        m["fight_elapsed"]=m.get("fight_elapsed",0)+seconds

def start_round(c, t, m):
    require(t["status"] == "active" and m["state"] in ("pending","rest"), "Combat non disponible.")
    for other in c["tables"]:
        for bout in other["matches"]:
            if bout["id"] != m["id"] and bout["state"] in ("running","paused","rest","correction"):
                require(other["area"] != t["area"], "Un combat est déjà engagé sur cette aire.")
                require(not ({m["a"],m["b"]} & {bout["a"],bout["b"]}), "Un participant est engagé sur une autre aire.")
    if m["state"] == "rest":
        require(elapsed(m["timer"]) >= m["timer"]["duration"], "La pause n’est pas terminée.")
    n = len(m["rounds"])
    require(t["seconds"] > 0, "Configurez la durée des rounds avant de lancer ce tableau.")
    duration = t["seconds"] if n < t["rounds"] else (15 if n < t["rounds"]+2 else None)
    m.update(state="running", timer=dict(running=True, since=time.time(), elapsed=0, duration=duration))

def pause(m):
    require(m["state"] in ("running","paused"), "Aucun round à suspendre.")
    timer = m["timer"]
    timer["elapsed"] = elapsed(timer)
    timer["since"] = time.time()
    timer["running"] = not timer["running"]
    m["state"] = "running" if timer["running"] else "paused"

def finish(m, winner, reason):
    require(winner in (m["a"],m["b"]), "Vainqueur invalide.")
    bank_time(m)
    if m["timer"]:
        m["timer"]["elapsed"] = elapsed(m["timer"])
        m["timer"]["running"] = False
    m.update(state="done", winner=winner, loser=m["b"] if winner==m["a"] else m["a"], reason=reason)

def lutte_point(t, m, winner):
    require(t["discipline"]=="Lutte" and t["status"]=="active", "Tableau Lutte actif requis.")
    require(m["state"] in ("running","paused") and m["timer"]["duration"] is None,
            "Le premier point ne termine que la mort subite.")
    require(len(m["rounds"])>=t["rounds"]+2, "Les rounds et prolongations doivent être terminés.")
    require(winner in (m["a"],m["b"]), "Vainqueur invalide.")
    m["sa" if winner==m["a"] else "sb"]+=1
    m["votes"]=["a" if winner==m["a"] else "b"]
    finish(m,winner,"points")

def validate_scores(scores, count=3):
    require(isinstance(scores,list) and len(scores)==2 and all(isinstance(s,list) and len(s)==count for s in scores),
            "Nombre de scores invalide.")
    for side in scores:
        for v in side:
            integer(v,0,999,"Score")

def score(t, m, scores):
    require(m["state"] in ("running","paused"), "Lancez le round avant la saisie.")
    require(m["timer"]["duration"] is not None, "Saisissez les votes de mort subite.")
    require(elapsed(m["timer"]) >= m["timer"]["duration"], "Le round n’est pas terminé.")
    validate_scores(scores,1 if t["discipline"]=="Lutte" else 3)
    m["rounds"].append(scores)
    m["sa"] += sum(scores[0])
    m["sb"] += sum(scores[1])
    if len(m["rounds"]) >= t["rounds"] and m["sa"] != m["sb"]:
        finish(m, m["a"] if m["sa"]>m["sb"] else m["b"], "points")
    else:
        bank_time(m)
        m.update(state="rest", timer=dict(running=True,since=time.time(),elapsed=0,duration=t["rest"]))

def sudden(m, votes):
    require(m["state"] in ("running","paused") and m["timer"]["duration"] is None, "Pas de mort subite en cours.")
    require(isinstance(votes,list) and len(votes)==3 and all(v in ("a","b","none") for v in votes), "Trois votes attendus.")
    side = "a" if votes.count("a")>=2 else ("b" if votes.count("b")>=2 else None)
    require(side, "Il faut la majorité des trois juges.")
    m["votes"] = votes
    m["s"+side] += 1
    finish(m,m[side],"points")

def correct(t, m, rounds, winner, reason, votes=None, duration=None):
    require(m["state"]=="done", "Seul un résultat validé peut être corrigé.")
    dependents = [x for x in t["matches"] if x["turn"]>m["turn"] or
                  (x["turn"]==m["turn"] and x["kind"]=="odd" and x["id"]!=m["id"])]
    require(all(x["state"]=="pending" for x in dependents),
            "Un combat dépendant a déjà commencé : correction bloquée pour préserver l’historique.")
    require(isinstance(rounds,list) and len(rounds)<=22, "Liste de rounds invalide.")
    require(reason in ("points","forfait","abandon","disqualification"), "Décision invalide.")
    for r in rounds:
        validate_scores(r,1 if t["discipline"]=="Lutte" else 3)
    sa, sb = sum(sum(r[0]) for r in rounds), sum(sum(r[1]) for r in rounds)
    if t["discipline"]=="Lutte":
        require(type(duration) in (int,float) and math.isfinite(duration) and duration>=0, "Durée effective invalide.")
    if reason=="points":
        require(t["discipline"]!="Lutte" or len(rounds)>=t["rounds"], "Tous les rounds réglementaires sont requis.")
        if sa==sb:
            needed=1 if t["discipline"]=="Lutte" else 2
            count=1 if t["discipline"]=="Lutte" else 3
            require((t["discipline"]!="Lutte" or len(rounds)>=t["rounds"]+2) and votes and len(votes)==count and
                    votes.count("a" if winner==m["a"] else "b")>=needed,
                    "Une égalité nécessite la décision de mort subite après les prolongations.")
            if winner==m["a"]: sa+=1
            else: sb+=1
        require(winner==(m["a"] if sa>sb else m["b"]), "Vainqueur incompatible avec les scores.")
    for x in dependents:
        if x["kind"]=="odd":
            t["spare"]=x["a"]
    t["matches"]=[x for x in t["matches"] if x not in dependents]
    t["repechages"]=[x for x in t["repechages"] if x["turn"]<m["turn"]]
    t.update(turn=m["turn"],status="active",closed=None,places={})
    m.update(rounds=rounds,sa=sa,sb=sb,votes=votes)
    if t["discipline"]=="Lutte":
        m["fight_elapsed"]=duration
        m["timer"]=dict(elapsed=duration,since=time.time(),running=False,duration=None)
    finish(m,winner,reason)

def rankings(c):
    points=defaultdict(int)
    for t in c["tables"]:
        if t["status"]=="closed" and t["discipline"] not in ("Combat équipe","Kata synchro"):
            for place,pid in t["places"].items():
                points[pid]+=POINTS[place]
    groups={"Enfants":[],"Adultes":[],"Clubs":[]}
    clubs=defaultdict(int)
    for p in c["people"]:
        if p["status"]!="approved":
            continue
        group="Enfants" if c["season"]-date.fromisoformat(p["birth"]).year<12 else "Adultes"
        groups[group].append(dict(id=p["id"],points=points[p["id"]],grade=p["grade"],birth=p["birth"]))
        clubs[p["club"]]+=points[p["id"]]
    for group in ("Enfants","Adultes"):
        rows=groups[group]
        rows.sort(key=lambda r:(-r["points"],r["grade"],-date.fromisoformat(r["birth"]).toordinal()))
        previous=None
        for i,r in enumerate(rows,1):
            key=(r["points"],r["grade"],r["birth"])
            if key!=previous:
                rank=i
            r["rank"]=rank
            previous=key
            del r["grade"],r["birth"]
    previous=None
    for i,(club,pts) in enumerate(sorted(clubs.items(),key=lambda x:-x[1]),1):
        if pts!=previous:
            rank=i
        groups["Clubs"].append(dict(id=club,points=pts,rank=rank))
        previous=pts
    return groups

