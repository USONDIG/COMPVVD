import unittest
from unittest.mock import patch
from app import domain as d
from tests.test_domain import fixture

def setup(n=8):
    c,_=fixture(n)
    c['tables']=[]
    for p in c['people']:p['disciplines']=['Dau','Vat']
    d.generate(c,'Vat');t=c['tables'][0]
    t.update(area='area',referee='3',judges=[],rounds=1,seconds=30,rest=10)
    d.draw(c,t);d.start_table(c,t)
    return c,t

def result(c,t,m,seconds=30):
    t['seconds']=seconds
    with patch('app.domain.time.time',return_value=100):d.start_round(c,t,m)
    with patch('app.domain.time.time',return_value=100+seconds):d.score(t,m,[[1],[0]])

class VatTests(unittest.TestCase):
    def test_separate_generation(self):
        c,t=setup();d.generate(c,'Dau')
        self.assertEqual({x['discipline'] for x in c['tables']},{'Dau','Vat'})
        with self.assertRaises(d.RuleError):d.generate(c,'Vat')

    def test_rounds_pause_and_effective_time(self):
        c,t=setup(2);t.update(rounds=2,seconds=20,rest=10);m=t['matches'][0]
        with patch('app.domain.time.time',return_value=100):d.start_round(c,t,m)
        with patch('app.domain.time.time',return_value=110):
            with self.assertRaises(d.RuleError):d.score(t,m,[[2],[0]])
            with self.assertRaises(d.RuleError):d.vat_point(t,m,m['a'])
            d.pause(m)
        with patch('app.domain.time.time',return_value=200):d.pause(m)
        with patch('app.domain.time.time',return_value=250):d.score(t,m,[[2],[0]])
        self.assertEqual(d.fight_time(m),20)
        self.assertEqual(m['state'],'rest')
        with patch('app.domain.time.time',return_value=255):
            with self.assertRaises(d.RuleError):d.start_round(c,t,m)
        with patch('app.domain.time.time',return_value=300):d.start_round(c,t,m)
        with patch('app.domain.time.time',return_value=320):d.score(t,m,[[1],[2]])
        self.assertEqual((m['sa'],m['sb'],m['winner']),(3,2,m['a']))
        self.assertEqual(d.fight_time(m),40)

    def test_two_extensions_then_referee_sudden_death(self):
        c,t=setup(2);m=t['matches'][0]
        now=100
        for duration in (30,15,15):
            with patch('app.domain.time.time',return_value=now):d.start_round(c,t,m)
            self.assertEqual(m['timer']['duration'],duration)
            with patch('app.domain.time.time',return_value=now+duration):d.score(t,m,[[1],[1]])
            now+=duration+10
        with patch('app.domain.time.time',return_value=now):d.start_round(c,t,m)
        self.assertIsNone(m['timer']['duration'])
        with patch('app.domain.time.time',return_value=now+7):d.vat_point(t,m,m['b'])
        self.assertEqual((m['sa'],m['sb']),(3,4))
        self.assertEqual(d.fight_time(m),67)

    def test_longest_loser_repechage(self):
        c,t=setup(7)
        for i,m in enumerate(t['matches']):result(c,t,m,10+i*20)
        expected=t['matches'][-1]['loser'];spare=t['spare'];d.advance(c,t)
        self.assertEqual(t['matches'][-1]['b'],expected)
        self.assertEqual(t['matches'][-1]['a'],spare)

    def test_ties_grade_then_age_and_forfeit_exclusion(self):
        c,t=setup(8)
        for m in t['matches']:result(c,t,m,60)
        losers=[m['loser'] for m in t['matches']]
        for p in c['people']:p.update(grade=3,birth='2000-01-01')
        people={p['id']:p for p in c['people']}
        people[losers[1]]['grade']=0;people[losers[2]].update(grade=0,birth='2001-01-01')
        self.assertEqual(d.best_loser(c,t['matches'],discipline='Vat'),losers[2])
        t['matches'][2]['reason']='forfait'
        self.assertEqual(d.best_loser(c,t['matches'],discipline='Vat'),losers[1])

    def test_all_sizes_classify(self):
        for n in range(2,17):
            c,t=setup(n)
            for turn in range(20):
                if t['status']=='closed':break
                for i,m in enumerate(t['matches']):
                    if m['state']!='done':result(c,t,m,10+i)
                d.advance(c,t)
            self.assertEqual(t['status'],'closed')
            self.assertEqual(len(t['places']),len(set(t['places'].values())))
            if n>=4:self.assertTrue({'3','4'}<=set(t['places']))
            if n>=5:self.assertIn('5',t['places'])

    def test_correction_duration_and_winner(self):
        c,t=setup(2);m=t['matches'][0];result(c,t,m)
        d.advance(c,t)
        d.correct(t,m,[[[0],[1]]],m['b'],'points',duration=42.5)
        self.assertEqual(d.fight_time(m),42.5)
        self.assertEqual((m['sa'],m['sb']),(0,1))
        d.advance(c,t);self.assertEqual(t['places']['1'],m['b'])
        with self.assertRaises(d.RuleError):d.correct(t,m,[],m['a'],'points',duration=float('nan'))

    def test_dau_scores_not_allowed(self):
        c,t=setup(2);m=t['matches'][0];d.start_round(c,t,m)
        with self.assertRaises(d.RuleError):d.score(t,m,[[1,0,0],[0,0,0]])

