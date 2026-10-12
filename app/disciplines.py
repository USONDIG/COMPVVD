"""Quyen individuel/synchro et poule Dau équipe. Notes stockées en dixièmes."""
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from itertools import combinations
import copy
import secrets
from . import domain as d

QUYEN=('Quyen','Quyen Arme','Quyen synchro')
TEAM=('Quyen synchro','Dau équipe')

def get(items, ident):
    item=next((x for x in items if x['id']==ident),None)
    d.require(item is not None,'Élément introuvable.')
    return item

def members(c, entry):
    team=next((x for x in c.get('teams',[]) if x['id']==entry),None)
    return team['members'] if team else [entry]

def names(c):
    return {x['id']:x['name'] for x in c['people']+c.get('teams',[])}

def team(c, name, discipline, ids, ident=None):
    d.require(discipline in TEAM,'Discipline collective invalide.')
    d.require(not any(t['discipline']==discipline for t in c['tables']),'Équipes verrouillées après génération des tableaux.')
    d.require(isinstance(name,str) and 0<len(name.strip())<=120,'Nom de l’équipe requis (120 caractères maximum).')
    d.require(len(set(ids))==len(ids) and (3 if discipline=='Dau équipe' else 2)<=len(ids)<=6,'Effectif : 3 à 6 en Dau équipe, 2 à 6 en Quyen synchro, sans doublon.')
    if ident:d.require(get(c.get('teams',[]),ident)['discipline']==discipline,'La discipline d’une équipe ne peut pas être modifiée.')
    people=[get(c['people'],pid) for pid in ids]
    d.require(all(p['status']=='approved' and discipline in p['disciplines'] for p in people),'Chaque membre doit avoir une inscription approuvée dans cette discipline.')
    senior=[d.age_index(p,c)==7 for p in people]
    d.require(all(senior) if discipline=='Dau équipe' else len(set(senior))==1,'Seniors uniquement en Dau équipe ; mélange seniors / moins de 18 ans interdit en Quyen synchro.')
    teams=c.setdefault('teams',[])
    d.require(not any(x['id']!=ident and x['discipline']==discipline and (set(ids)&set(x['members']) or x['name'].casefold()==name.strip().casefold()) for x in teams),'Nom déjà utilisé ou membre déjà affecté à une équipe de cette discipline.')
    record=dict(name=name.strip(),discipline=discipline,members=list(ids),group='Seniors' if all(senior) else 'Moins de 18 ans')
    if ident:get(teams,ident).update(record)
    else:teams.append(dict(record,id=d.uid()))

def remove_team(c, ident):
    item=get(c.get('teams',[]),ident)
    d.require(not any(t['discipline']==item['discipline'] for t in c['tables']),'Équipes verrouillées après génération.')
    c['teams'].remove(item)

def generate(c, discipline):
    d.require(discipline in QUYEN+('Dau équipe',),'Discipline invalide.')
    d.require(discipline not in c['open'],'Fermez les inscriptions avant de générer les tableaux.')
    d.require(not any(t['discipline']==discipline for t in c['tables']),'Les tableaux ont déjà été générés.')
    groups=defaultdict(list)
    if discipline in TEAM:
        teams=[x for x in c.get('teams',[]) if x['discipline']==discipline]
        assigned={pid for x in teams for pid in x['members']}
        registered={p['id'] for p in c['people'] if p['status']=='approved' and discipline in p['disciplines']}
        d.require(assigned==registered,'Affectez chaque inscrit approuvé à une équipe avant la génération.')
        for x in teams:groups[x['group']].append(x['id'])
    else:
        for p in c['people']:
            if p['status']=='approved' and discipline in p['disciplines']:
                groups[f"{p['sex']} · {d.AGES[d.age_index(p,c)]}"].append(p['id'])
    d.require(groups,'Aucun participant ou équipe disponible.')
    for label,ids in sorted(groups.items()):
        c['tables'].append(dict(id=d.uid(),name=label,discipline=discipline,members=ids,status='draft',matches=[],
                               turn=0,spare=None,area=None,judges=[],referee=None,rounds=2,seconds=60,rest=30,
                               started=None,closed=None,places={},repechages=[],passes=[],encounters=[],active_encounter=None))

def available(c, t, ids, exclude=None):
    requested=set(ids)
    for other in c['tables']:
        for m in other.get('matches',[]):
            if m['id']!=exclude and m['state'] in ('running','paused','rest','correction'):
                d.require(other['area']!=t['area'],'Une confrontation est déjà engagée sur cette aire.')
                d.require(not requested&{m['a'],m['b']},'Un participant est engagé sur une autre aire.')
        for p in other.get('passes',[]):
            if p['id']!=exclude and p['state'] in ('running','paused'):
                d.require(other['area']!=t['area'],'Un passage est déjà engagé sur cette aire.')
                d.require(not requested&set(members(c,p['entry'])),'Un participant est engagé sur une autre aire, individuellement ou en équipe.')

def wave(t, ids, phase, stage, groups=None):
    number=t.get('wave',0)+1
    control=dict(phase=phase,stage=stage,groups=copy.deepcopy(groups))
    t.update(wave=number,q_control=control)
    t.setdefault('q_checkpoints',{})[str(number)]=copy.deepcopy(control)
    for pid in ids:
        t['passes'].append(dict(id=d.uid(),entry=pid,wave=number,stage=stage,kind=phase,state='pending',notes=None,total=None,timer=None))

def draw(c, t):
    d.require(t['status']=='draft','Le tirage est définitif.')
    d.require(len(t['members'])>=2,'Au moins deux participants ou équipes sont nécessaires. Fusionnez une catégorie compatible si nécessaire.')
    ids=list(t['members']);secrets.SystemRandom().shuffle(ids)
    if t['discipline'] in QUYEN:
        t.update(passes=[],wave=0,q_checkpoints={},q_ranking=[],q_finalists=[])
        wave(t,ids,'round',1)
    else:
        pairs=list(combinations(ids,2));secrets.SystemRandom().shuffle(pairs)
        t.update(encounters=[],matches=[],pool_ranking=[],active_encounter=None)
        for turn,(a,b) in enumerate(pairs,1):
            encounter=dict(id=d.uid(),a=a,b=b,turn=turn,state='pending',winner=None,reason=None)
            left=list(get(c['teams'],a)['members']);right=list(get(c['teams'],b)['members'])
            size=max(len(left),len(right))
            for lineup in (left,right):
                secrets.SystemRandom().shuffle(lineup)
                lineup.extend(lineup[:size-len(lineup)])
                secrets.SystemRandom().shuffle(lineup)
            for pa,pb in zip(left,right):
                m=d.match(pa,pb,turn,'team');m['encounter']=encounter['id'];t['matches'].append(m)
            t['encounters'].append(encounter)
    t.update(status='ready',turn=1)

def parse_notes(raw):
    d.require(len(raw)==3,'Trois notes sont requises.')
    notes=[]
    for value in raw:
        try:n=Decimal(str(value).replace(',','.'))
        except InvalidOperation:raise d.RuleError('Note invalide.')
        d.require(n.is_finite() and Decimal(6)<=n<=Decimal(10) and n*10==(n*10).to_integral_value(),'Notes de 6,0 à 10,0 au dixième uniquement.')
        notes.append(int(n*10))
    return notes

def quyen_start(c,t,p):
    d.require(t['discipline'] in QUYEN and t['status']=='active' and p['wave']==t['wave'] and p['state']=='pending','Passage indisponible.')
    available(c,t,members(c,p['entry']))
    p.update(state='running',timer=dict(running=True,since=d.time.time(),elapsed=0,duration=None))

def quyen_score(t,p,raw):
    d.require(t['discipline'] in QUYEN and t['status']=='active' and p['wave']==t['wave'] and p['state'] in ('running','paused'),'Lancez le passage avant la notation.')
    notes=parse_notes(raw)
    p['timer'].update(elapsed=d.elapsed(p['timer']),running=False)
    p.update(notes=notes,total=sum(notes),state='done')

def grouped(ids, totals):
    out=[]
    for pid in sorted(ids,key=lambda x:-totals[x]):
        if out and totals[pid]==totals[out[-1][0]]:out[-1].append(pid)
        else:out.append([pid])
    return out

def primary_total(t,pid):
    scores=[p['total'] for p in t['passes'] if p['entry']==pid and p['kind']=='round' and p['state']=='done' and (len(t['members'])<=5 or p['stage']==2)]
    return sum(scores)

def resolve_quyen(t,groups,phase,stage):
    tie_ids=[];count=0
    for group in groups:
        if len(group)>1 and (phase=='final' or count<5<count+len(group)):tie_ids+=group
        count+=len(group)
    if tie_ids:
        wave(t,tie_ids,phase,stage,groups)
    elif phase=='qualify':
        ids=[pid for group in groups for pid in group][:5]
        t['q_finalists']=ids
        wave(t,ids,'round',2)
    else:
        ids=[pid for group in groups for pid in group]
        t['q_ranking']=[dict(entry=pid,rank=i,total=primary_total(t,pid)) for i,pid in enumerate(ids,1)]
        t.update(places={str(i):pid for i,pid in enumerate(ids[:5],1)},status='closed',closed=d.time.time())

def quyen_advance(t):
    d.require(t['status']=='active','Tableau non actif.')
    current=[p for p in t['passes'] if p['wave']==t['wave']]
    d.require(current and all(p['state']=='done' for p in current),'Terminez tous les passages avant de valider le tour.')
    control=t['q_control'];stage=control['stage'];phase=control['phase']
    if phase=='round':
        if stage==1 and len(t['members'])<=5:
            t['q_finalists']=list(t['members']);wave(t,t['members'],'round',2);return
        totals={p['entry']:p['total'] if stage==1 else primary_total(t,p['entry']) for p in current}
        groups=grouped([p['entry'] for p in current],totals)
        resolve_quyen(t,groups,'qualify' if stage==1 else 'final',stage)
    else:
        totals={p['entry']:p['total'] for p in current}
        groups=[]
        for group in control['groups']:
            groups.extend(grouped(group,totals) if group[0] in totals else [group])
        resolve_quyen(t,groups,phase,stage)

def quyen_correct(t,p,raw):
    d.require(p['state']=='done','Seule une note validée peut être corrigée.')
    d.require(all(x['state']=='pending' for x in t['passes'] if x['wave']>p['wave']), 'Un passage dépendant a commencé : correction bloquée.')
    notes=parse_notes(raw)
    p.update(notes=notes,total=sum(notes))
    t['passes']=[x for x in t['passes'] if x['wave']<=p['wave']]
    t['q_control']=copy.deepcopy(t['q_checkpoints'][str(p['wave'])])
    t['q_checkpoints']={k:v for k,v in t['q_checkpoints'].items() if int(k)<=p['wave']}
    t.update(wave=p['wave'],status='active',closed=None,places={},q_ranking=[])
    if p['stage']==1:t['q_finalists']=[]

def current_match(t):
    eligible=[m for m in t['matches'] if m['state']!='done' and (t['discipline']!='Dau équipe' or m.get('encounter')==t.get('active_encounter'))]
    return next((m for m in eligible if m['state']!='pending'),eligible[0] if eligible else None)

def pool_start(c,t,ident):
    d.require(t['discipline']=='Dau équipe' and t['status']=='active' and not t.get('active_encounter'),'Terminez la rencontre en cours.')
    encounter=get(t['encounters'],ident)
    first=next((x for x in t['encounters'] if x['state']=='pending'),None)
    d.require(encounter is first,'Respectez l’ordre des rencontres tiré au sort.')
    encounter['state']='active';t['active_encounter']=ident

def encounter_stats(t,encounter):
    matches=[m for m in t['matches'] if m.get('encounter')==encounter['id'] and m['state']=='done']
    return dict(wins_a=sum(m['winner']==m['a'] for m in matches),wins_b=sum(m['winner']==m['b'] for m in matches),
                points_a=sum(m['sa'] for m in matches),points_b=sum(m['sb'] for m in matches))

def pool_advance(c,t):
    d.require(t['status']=='active' and t.get('active_encounter'),'Lancez une rencontre.')
    e=get(t['encounters'],t['active_encounter'])
    ms=[m for m in t['matches'] if m.get('encounter')==e['id']]
    d.require(ms and all(m['state']=='done' for m in ms),'Terminez tous les combats de la rencontre.')
    stats=encounter_stats(t,e);a=(stats['wins_a'],stats['points_a']);b=(stats['wins_b'],stats['points_b'])
    extra=next((m for m in ms if m['kind']=='team_extra'),None)
    if extra:
        winner=e['a'] if extra['winner']==extra['a'] else e['b'];reason='Combat supplémentaire'
    elif a!=b:
        winner=e['a'] if a>b else e['b'];reason='Combats gagnés' if a[0]!=b[0] else 'Cumul des points'
    else:
        left=members(c,e['a']);right=members(c,e['b'])
        counts=Counter(pid for m in ms for pid in (m['a'],m['b']))
        eligible_a=[pid for pid in left if counts[pid]<2];eligible_b=[pid for pid in right if counts[pid]<2]
        if len(left)<len(right) and not eligible_a:winner=e['a'];reason='Plus petite équipe sans combattant éligible'
        elif len(right)<len(left) and not eligible_b:winner=e['b'];reason='Plus petite équipe sans combattant éligible'
        else:
            d.require(eligible_a and eligible_b,'Aucun combattant éligible pour le départage.')
            m=d.match(secrets.choice(eligible_a),secrets.choice(eligible_b),e['turn'],'team_extra');m['encounter']=e['id'];t['matches'].append(m);return
    e.update(stats,state='done',winner=winner,reason=reason)
    t['active_encounter']=None
    t['pool_ranking']=pool_standings(t)
    if all(x['state']=='done' for x in t['encounters']):t.update(status='closed',closed=d.time.time())

def pool_standings(t):
    rows={pid:dict(entry=pid,played=0,wins=0,bouts=0,points=0) for pid in t['members']}
    for e in t['encounters']:
        if e['state']!='done':continue
        for side in ('a','b'):
            r=rows[e[side]];r['played']+=1;r['wins']+=int(e['winner']==e[side]);r['bouts']+=e['wins_'+side];r['points']+=e['points_'+side]
    groups=defaultdict(list)
    for r in rows.values():groups[r['wins']].append(r)
    out=[]
    for wins,group in sorted(groups.items(),reverse=True):
        if len(group)==2:
            ids={x['entry'] for x in group}
            direct=next((x['winner'] for x in t['encounters'] if x['state']=='done' and {x['a'],x['b']}==ids),None)
            for r in group:r['_key']=(int(r['entry']==direct),)
        else:
            for r in group:r['_key']=(r['bouts'],r['points'])
        group.sort(key=lambda r:r['_key'],reverse=True);previous=None;base=len(out)
        for i,r in enumerate(group,1):
            if r['_key']!=previous:rank=base+i
            previous=r.pop('_key');r['rank']=rank;out.append(r)
    return out

def pool_correct(t,m,rounds,winner,reason,votes):
    e=get(t['encounters'],m['encounter'])
    d.require(all(x['state']=='pending' for x in t['encounters'] if x['turn']>e['turn']),'Une rencontre suivante a commencé : correction bloquée.')
    extras=[x for x in t['matches'] if x.get('encounter')==e['id'] and x['kind']=='team_extra' and x['id']!=m['id']]
    d.require(all(x['state']=='pending' for x in extras),'Le combat de départage a commencé : correction bloquée.')
    temp=dict(t,matches=[m],repechages=[])
    d.correct(temp,m,rounds,winner,reason,votes)
    t['matches']=[x for x in t['matches'] if x not in extras]
    e.update(state='active',winner=None,reason=None)
    t.update(active_encounter=e['id'],status='active',closed=None,pool_ranking=[],places={})
