"""Règles Quyen et épreuves collectives : scénarios complets et limites."""
import copy
import unittest
from unittest.mock import patch
from app import domain as d
from app import disciplines as x


def fixture(discipline='Quyen',count=6):
    c=d.new_competition('Disciplines','2026-11-01',2026,'org');c['open']=[]
    c['areas']=[dict(id='area',assistant='assistant')]
    c['people']=[dict(id=str(i),name=f'Personne {i}',club=str(i%3),birth='2000-01-01',sex='F',weight=50+i,grade=0,disciplines=[discipline],status='approved') for i in range(count)]
    return c


def prepared(c,discipline='Quyen'):
    d.generate(c,discipline);t=c['tables'][-1]
    t.update(area='area',judges=['j1','j2','j3'],referee=None if discipline in x.QUYEN else 'ref',rounds=1,seconds=1,rest=0)
    d.draw(c,t);d.start_table(c,t)
    return t


def notes(c,t,values):
    for p in list(t['passes']):
        if p['wave']==t['wave'] and p['state']=='pending':
            x.quyen_start(c,t,p);x.quyen_score(t,p,[values[p['entry']]]*3)
    d.advance(c,t)


def teams(sizes=(3,3),discipline='Dau équipe'):
    c=fixture(discipline,sum(sizes));offset=0
    for i,size in enumerate(sizes):
        x.team(c,f'Équipe {i}',discipline,[str(j) for j in range(offset,offset+size)])
        offset+=size
    return c


def finish_encounter(t,e,wins_a=None,points_a=1,points_b=1):
    ms=[m for m in t['matches'] if m['encounter']==e['id']]
    if wins_a is None:wins_a=len(ms)
    for i,m in enumerate(ms):
        m.update(sa=points_a,sb=points_b)
        d.finish(m,m['a'] if i<wins_a else m['b'],'points')


class QuyenTests(unittest.TestCase):
    def test_categories_without_weight(self):
        c=fixture();c['people'][0]['weight']=150
        d.generate(c,'Quyen');self.assertEqual(len(c['tables']),1)
        self.assertNotIn('kg',c['tables'][0]['name'])

    def test_more_than_five_final_ignores_first_round(self):
        c=fixture();t=prepared(c)
        notes(c,t,{str(i):10-i*.5 for i in range(6)})
        self.assertEqual(set(t['q_finalists']),set('01234'))
        notes(c,t,{str(i):6+i*.5 for i in range(5)})
        self.assertEqual(t['status'],'closed');self.assertEqual(t['places']['1'],'4')
        self.assertEqual(t['q_ranking'][0]['total'],240)
        self.assertEqual({r['id']:r['points'] for r in d.rankings(c)['Adultes']},dict(zip('012345',[1,2,3,5,5,0])))

    def test_two_rounds_sum_and_independent_repeated_tie(self):
        c=fixture(count=2);t=prepared(c)
        notes(c,t,{'0':10,'1':8});notes(c,t,{'0':6,'1':8})
        self.assertEqual(t['q_control']['phase'],'final')
        notes(c,t,{'0':7,'1':7})
        self.assertEqual(t['q_control']['phase'],'final')
        notes(c,t,{'0':6,'1':10})
        self.assertEqual(t['places'],{'1':'1','2':'0'})
        self.assertEqual([r['total'] for r in t['q_ranking']],[480,480])

    def test_cutoff_three_way_tie_only_fifth_place(self):
        c=fixture(count=7);t=prepared(c)
        notes(c,t,dict(zip(map(str,range(7)),[10,9,8,7,6,6,6])))
        self.assertEqual(t['q_control']['phase'],'qualify')
        self.assertEqual({p['entry'] for p in t['passes'] if p['wave']==2},set('456'))
        notes(c,t,{'4':6,'5':7,'6':8})
        self.assertEqual(set(t['q_finalists']),set('01236'))

    def test_ties_fully_above_cutoff_do_not_need_extra_pass(self):
        c=fixture();t=prepared(c)
        notes(c,t,dict(zip(map(str,range(6)),[10,10,10,10,9,8])))
        self.assertEqual(t['q_control']['phase'],'round');self.assertEqual(t['q_control']['stage'],2)

    def test_separate_final_tie_groups_do_not_compete_with_each_other(self):
        c=fixture(count=4);t=prepared(c)
        notes(c,t,dict(zip('0123',[8,8,6,6])));notes(c,t,dict(zip('0123',[8,8,6,6])))
        notes(c,t,dict(zip('0123',[6,7,10,9])))
        self.assertEqual(list(t['places'].values()),list('1023'))

    def test_notes_reject_nonfinite_range_precision_or_count(self):
        for raw in (['nan']*3,['inf']*3,[5.9]*3,[10.1]*3,[6.01]*3,[7]*2,['x']*3):
            with self.subTest(raw=raw),self.assertRaises(d.RuleError):x.parse_notes(raw)
        self.assertEqual(x.parse_notes(['6,1','7.2','10']),[61,72,100])

    def test_correction_recalculates_only_unstarted_later_waves(self):
        c=fixture(count=2);t=prepared(c);notes(c,t,{'0':8,'1':9})
        first=t['passes'][0];x.quyen_correct(t,first,[10]*3)
        self.assertEqual(t['wave'],1);self.assertEqual(len(t['passes']),2)
        d.advance(c,t);p=next(p for p in t['passes'] if p['wave']==2);x.quyen_start(c,t,p)
        with self.assertRaises(d.RuleError):x.quyen_correct(t,first,[7]*3)

    def test_single_entry_requires_merge(self):
        c=fixture(count=1);d.generate(c,'Quyen')
        with self.assertRaises(d.RuleError):d.draw(c,c['tables'][0])

    def test_quyen_arme_same_rules(self):
        c=fixture('Quyen Arme',2);t=prepared(c,'Quyen Arme')
        notes(c,t,{'0':8,'1':9});notes(c,t,{'0':8,'1':9});self.assertEqual(t['places']['1'],'1')

    def test_synchro_scores_are_not_general_points(self):
        c=teams((2,3),'Quyen synchro');t=prepared(c,'Quyen synchro')
        values={t['members'][0]:7,t['members'][1]:8};notes(c,t,values);notes(c,t,values)
        self.assertEqual(t['status'],'closed')
        self.assertTrue(all(r['points']==0 for group in d.rankings(c).values() for r in group))

    def test_cross_discipline_and_team_member_cannot_start_twice(self):
        c=teams((2,2),'Quyen synchro');t=prepared(c,'Quyen synchro')
        p=t['passes'][0];x.quyen_start(c,t,p)
        person=x.members(c,p['entry'])[0]
        m=d.match(person,'opponent',1)
        other=dict(t,id='other',area='other',discipline='Dau',matches=[m]);c['tables'].append(other)
        with self.assertRaises(d.RuleError):d.start_round(c,other,m)
        x.quyen_score(t,p,[7]*3);d.start_round(c,other,m)
        pending=next(q for q in t['passes'] if q['state']=='pending')
        # A running individual bout blocks a synchro passage involving its fighter.
        pending['entry']=p['entry']
        with self.assertRaises(d.RuleError):x.quyen_start(c,t,pending)


class TeamTests(unittest.TestCase):
    def test_membership_size_approval_and_age(self):
        c=fixture('Dau équipe',8)
        for ids in (['0','1'],list(map(str,range(7))),['0','0','1']):
            with self.assertRaises(d.RuleError):x.team(c,'Test','Dau équipe',ids)
        c['people'][0]['birth']='2010-01-01'
        with self.assertRaises(d.RuleError):x.team(c,'Test','Dau équipe',['0','1','2'])
        for p in c['people']:p['disciplines'].append('Quyen synchro')
        with self.assertRaises(d.RuleError):x.team(c,'Mix','Quyen synchro',['0','1'])
        c['people'][1]['birth']='2012-01-01';c['people'][1]['sex']='M'
        x.team(c,'Jeunes','Quyen synchro',['0','1'])
        self.assertEqual(c['teams'][0]['group'],'Moins de 18 ans')
        with self.assertRaises(d.RuleError):x.team(c,'Autre','Quyen synchro',['0','1'])

    def test_unassigned_member_blocks_generation_and_generated_team_is_locked(self):
        c=teams();c['people'].append(dict(c['people'][0],id='extra'))
        with self.assertRaises(d.RuleError):d.generate(c,'Dau équipe')
        c['people'].pop();d.generate(c,'Dau équipe')
        with self.assertRaises(d.RuleError):x.remove_team(c,c['teams'][0]['id'])

    def test_round_robin_all_pairs_and_repeat_limits(self):
        c=teams((3,4,6));t=prepared(c,'Dau équipe')
        self.assertEqual(len(t['encounters']),3)
        self.assertEqual(len({frozenset((e['a'],e['b'])) for e in t['encounters']}),3)
        for e in t['encounters']:
            ms=[m for m in t['matches'] if m['encounter']==e['id']]
            self.assertEqual(len(ms),max(len(x.members(c,e['a'])),len(x.members(c,e['b']))))
            for side in ('a','b'):
                roster=[m[side] for m in ms]
                self.assertEqual(set(roster),set(x.members(c,e[side])))
                self.assertLessEqual(max(roster.count(pid) for pid in roster),2)

    def test_pool_manual_start_rounds_and_score_gate(self):
        c=teams();t=prepared(c,'Dau équipe');m=t['matches'][0]
        with self.assertRaises(d.RuleError):d.start_round(c,t,m)
        e=t['encounters'][0];x.pool_start(c,t,e['id']);d.start_round(c,t,m)
        with self.assertRaises(d.RuleError):d.score(t,m,[[1,1,1],[0,0,0]])
        with patch('app.domain.time.time',return_value=m['timer']['since']+2):d.score(t,m,[[1,1,1],[0,0,0]])
        self.assertEqual(m['winner'],m['a'])
        with self.assertRaises(d.RuleError):d.advance(c,t)

    def test_three_vs_six_tie_smaller_wins_without_extra(self):
        c=teams((3,6));t=prepared(c,'Dau équipe');e=t['encounters'][0]
        x.pool_start(c,t,e['id']);finish_encounter(t,e,3);d.advance(c,t)
        small=next(x['id'] for x in c['teams'] if len(x['members'])==3)
        self.assertEqual(e['winner'],small);self.assertEqual(t['status'],'closed')
        self.assertEqual(len(t['matches']),6)

    def test_equal_team_tie_random_extra_and_no_general_points(self):
        c=teams((4,4));t=prepared(c,'Dau équipe');e=t['encounters'][0]
        x.pool_start(c,t,e['id']);finish_encounter(t,e,2);d.advance(c,t)
        extra=t['matches'][-1];self.assertEqual(extra['kind'],'team_extra')
        d.finish(extra,extra['b'],'points');d.advance(c,t)
        self.assertEqual(e['winner'],e['b']);self.assertEqual(t['status'],'closed')
        self.assertTrue(all(r['points']==0 for group in d.rankings(c).values() for r in group))

    def test_bout_wins_then_points(self):
        c=teams((4,4));t=prepared(c,'Dau équipe');e=t['encounters'][0]
        x.pool_start(c,t,e['id']);finish_encounter(t,e,2,2,1);d.advance(c,t)
        self.assertEqual(e['winner'],e['a']);self.assertEqual(e['reason'],'Cumul des points')

    def test_correction_blocks_later_started_encounter(self):
        c=teams((3,3,3));t=prepared(c,'Dau équipe');e=t['encounters'][0]
        x.pool_start(c,t,e['id']);finish_encounter(t,e);d.advance(c,t)
        m=next(m for m in t['matches'] if m['encounter']==e['id'])
        x.pool_correct(t,m,[[[0,0,0],[1,1,1]]],m['b'],'points',None)
        self.assertEqual(t['active_encounter'],e['id']);d.advance(c,t)
        x.pool_start(c,t,t['encounters'][1]['id'])
        with self.assertRaises(d.RuleError):x.pool_correct(t,m,[[[0,0,0],[1,1,1]]],m['b'],'points',None)

    def test_two_tied_direct_result_and_circular_exaequo(self):
        t=dict(members=['a','b','c'],encounters=[dict(a='a',b='b',winner='a',state='done',wins_a=2,wins_b=1,points_a=3,points_b=2),dict(a='b',b='c',winner='b',state='done',wins_a=2,wins_b=1,points_a=3,points_b=2),dict(a='c',b='a',winner='c',state='done',wins_a=2,wins_b=1,points_a=3,points_b=2)])
        self.assertEqual([r['rank'] for r in x.pool_standings(t)],[1,1,1])
        t['encounters'].pop();rows=x.pool_standings(t)
        self.assertEqual([r['entry'] for r in rows],['a','b','c'])
        self.assertEqual([r['rank'] for r in rows],[1,2,3])
