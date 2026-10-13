"""Read-only tournament diagram, including provisional future rounds.

No projected slot is written back to competition state. Repechage opponents
remain unspecified until the sporting engine selects them.
"""
from collections import defaultdict
from . import domain as d

CARD_W=270
CARD_H=142
GAP_X=90
GAP_Y=62

def diagram(t,names,clubs=None):
    if not t['matches']:return dict(nodes=[],edges=[],width=800,height=180)
    clubs=clubs or {}
    nodes=[];edges=[];latest={};byid={};bottoms=defaultdict(lambda:48)
    matches=[m for m in t['matches'] if m['kind']!='bronze']
    columns=sorted({(m['turn'],m['kind']=='odd') for m in matches})
    colmap={key:i for i,key in enumerate(columns)}
    def add(ident,title,rows,col,sources=(),state='future',kind='main',round_number=0):
        centers=[byid[src]['y']+CARD_H/2 for src,side,edgekind in sources if src in byid]
        preferred=(sum(centers)/len(centers)-CARD_H/2) if centers else 48
        y=max(bottoms[col],preferred)
        node=dict(id=ident,title=title,rows=rows,x=col*(CARD_W+GAP_X)+24,y=y,
                  state=state,kind=kind,round=round_number)
        nodes.append(node);byid[ident]=node;bottoms[col]=y+CARD_H+GAP_Y
        for src,side,edgekind in sources:
            if src in byid:edges.append(dict(source=src,target=ident,side=side,kind=edgekind))
        return node
    def label(size,number):
        return {1:'Finale',2:'Demi-finale',4:'Quart de finale',8:'Huitième de finale'}.get(size,f'Tour {number}')
    for m in matches:
        count=sum(x['turn']==m['turn'] for x in matches)
        # Before an odd preliminary bout is played the isolated participant
        # still needs a complementary bout: the first bout is not a final.
        if m['turn']==1 and t.get('spare'):count+=1
        title='Combat complémentaire' if m['kind']=='odd' else label(count,m['turn'])
        sources=[];rows=[]
        for side in ('a','b'):
            pid=m[side];source=latest.get(pid)
            if source:
                prior=next(x for x in matches if x['id']==source)
                sources.append((source,side,'qualification' if prior['winner']==pid else 'repechage'))
            rows.append(dict(name=names.get(pid,'Participant'),club=clubs.get(pid,''),pid=pid,
                             score=m['s'+side] if m['rounds'] or m['state']=='done' else '—',winner=m['winner']==pid))
        n=add(m['id'],title,rows,colmap[(m['turn'],m['kind']=='odd')],sources,m['state'],m['kind'],m['turn'])
        n['reason']=m.get('reason');n['duration']=round(d.fight_time(m),1) if t['discipline']=='Vat' and m['state']=='done' else None
        for side in ('a','b'):latest[m[side]]=m['id']
    last_turn=max(m['turn'] for m in matches)
    current=[m for m in matches if m['turn']==last_turn]
    refs=[dict(source=m['id'],pid=m.get('winner'),name=names.get(m.get('winner'),'Vainqueur à déterminer')) for m in current]
    col=max(colmap.values())+1
    if t.get('spare') and t['status']!='closed':
        spare=t['spare']
        row=lambda name,pid=None:dict(name=name,club=clubs.get(pid,''),pid=pid,score='—',winner=False)
        ident='future-complement'
        add(ident,'Combat complémentaire',[row(names.get(spare,'Participant isolé'),spare),row('Meilleur perdant à déterminer')],col,kind='odd',round_number=last_turn)
        refs.append(dict(source=ident,pid=None,name='Vainqueur du complément'))
        col+=1
    bronze_sources=None
    if len(refs)==2:bronze_sources=[r['source'] for r in refs]
    number=last_turn
    while len(refs)>1 and t['status']!='closed':
        if len(refs)%2:
            refs.append(dict(source=None,pid=None,name=f'Repêché du tour {number} à déterminer'))
        number+=1;next_refs=[];count=len(refs)//2
        for i in range(count):
            pair=refs[i*2:i*2+2];ident=f'future-{number}-{i}'
            rows=[dict(name=r['name'],club=clubs.get(r['pid'],''),pid=r['pid'],score='—',winner=False) for r in pair]
            sources=[(r['source'],'a' if j==0 else 'b','qualification') for j,r in enumerate(pair) if r['source']]
            add(ident,label(count,number),rows,col,sources,round_number=number)
            next_refs.append(dict(source=ident,pid=None,name='Vainqueur à déterminer'))
        if count==2:bronze_sources=[r['source'] for r in next_refs]
        refs=next_refs;col+=1
    bronze=next((m for m in t['matches'] if m['kind']=='bronze'),None)
    if bronze or (bronze_sources and len(t['members'])>=4 and t['status']!='closed'):
        col=max(0,col-1)
        if bronze:
            rows=[dict(name=names.get(bronze[s],'Participant'),club=clubs.get(bronze[s],''),pid=bronze[s],score=bronze['s'+s] if bronze['rounds'] or bronze['state']=='done' else '—',winner=bronze['winner']==bronze[s]) for s in ('a','b')]
            sources=[]
            for side in ('a','b'):
                prior=next((m for m in reversed(matches) if m['turn']<bronze['turn'] and bronze[side] in (m['a'],m['b'])),None)
                if prior:sources.append((prior['id'],side,'bronze'))
            add(bronze['id'],'Places 3 et 4',rows,col,sources,bronze['state'],'bronze',bronze['turn'])
        else:
            rows=[dict(name='Perdant de demi-finale',club='',pid=None,score='—',winner=False) for _ in range(2)]
            add('future-bronze','Places 3 et 4 · prévisionnel',rows,col,[(sid,'a' if i==0 else 'b','bronze') for i,sid in enumerate(bronze_sources)],kind='bronze')
    for e in edges:
        a,b=byid[e['source']],byid[e['target']]
        x1=a['x']+CARD_W;y1=a['y']+CARD_H/2;x2=b['x'];y2=b['y']+(64 if e['side']=='a' else 109)
        mid=x1+(x2-x1)/2
        e['path']=f'M {x1} {y1} H {mid} V {y2} H {x2}'
    return dict(nodes=nodes,edges=edges,width=max(n['x']+CARD_W for n in nodes)+24,height=max(n['y']+CARD_H for n in nodes)+36)
