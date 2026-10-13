import copy
import unittest
from app import domain as d
from app.brackets import diagram,CARD_W,CARD_H
from tests.test_domain import fixture,win
from tests import test_web

class DiagramTests(unittest.TestCase):
    def test_future_rounds_and_bronze_without_mutation(self):
        c,t=fixture(8);before=copy.deepcopy(t)
        graph=diagram(t,{p['id']:p['name'] for p in c['people']})
        self.assertEqual(t,before)
        self.assertEqual(len(graph['nodes']),8) # 4 quarters, 2 semis, final, bronze
        self.assertEqual(sum(n['title']=='Finale' for n in graph['nodes']),1)
        self.assertEqual(sum('Places 3' in n['title'] for n in graph['nodes']),1)
        self.assertTrue(all(0<=n['x'] and 0<=n['y'] and n['x']+CARD_W<=graph['width'] and n['y']+CARD_H<=graph['height'] for n in graph['nodes']))

    def test_odd_draw_keeps_repechage_undetermined(self):
        c,t=fixture(5);graph=diagram(t,{p['id']:p['name'] for p in c['people']})
        self.assertTrue(any(n['id']=='future-complement' for n in graph['nodes']))
        self.assertTrue(any('Repêché' in r['name'] for n in graph['nodes'] for r in n['rows']))
        self.assertFalse(any(e['kind']=='repechage' for e in graph['edges']))

    def test_completed_results_and_repechage_edges(self):
        c,t=fixture(5)
        for m in list(t['matches']):win(m)
        d.advance(c,t)
        graph=diagram(t,{p['id']:p['name'] for p in c['people']})
        self.assertTrue(any(e['kind']=='repechage' for e in graph['edges']))
        self.assertTrue(any(r['winner'] for n in graph['nodes'] for r in n['rows']))

    def test_two_people_are_a_final_not_a_bronze(self):
        c,t=fixture(2);graph=diagram(t,{p['id']:p['name'] for p in c['people']})
        self.assertEqual([n['title'] for n in graph['nodes']],['Finale'])

class PrintWebTests(unittest.TestCase):
    setUp=test_web.WebTests.setUp
    tearDown=test_web.WebTests.tearDown
    login=test_web.WebTests.login
    token=test_web.WebTests.token
    post=test_web.WebTests.post
    action=test_web.WebTests.action
    stored=test_web.WebTests.stored

    def prepare(self):
        self.login();self.action('discipline',discipline='Dau');self.action('generate',revision=1)
        c,rev=self.stored();t=c['tables'][0];self.action('draw',revision=rev,table=t['id']);return t

    def test_organizer_prints_tree_and_rankings(self):
        t=self.prepare();base='/c/'+self.c['id']+'/print'
        for query in ('?kind=rankings','?kind=tree&table='+t['id'],'?kind=table&table='+t['id']):
            r=self.client.get(base+query);self.assertEqual(r.status_code,200,r.data)
            self.assertIn('Imprimer / Enregistrer en PDF',r.text)
            self.assertNotIn('data-public-live',r.text)
        r=self.client.get(base+'?kind=tree&table='+t['id']+'&paper=a3');self.assertIn('print-a3',r.text);self.assertIn('<svg',r.text)

    def test_print_authorization_and_public_code_revocation(self):
        t=self.prepare();base='/c/'+self.c['id']+'/print'
        self.login('club');self.assertEqual(self.client.get(base+'?kind=rankings').status_code,403)
        self.assertEqual(self.client.get(base+'?kind=tree&table='+t['id']).status_code,403)
        public=self.app.test_client();self.assertEqual(public.get('/public/print?kind=rankings').status_code,302)
        public.get('/public');self.post('/public',dict(code=self.c['code']),public)
        r=public.get('/public/print?kind=tree&table='+t['id']);self.assertEqual(r.status_code,200,r.data)
        self.assertNotIn('2000-04-12',r.text);self.assertNotIn('52 kg',r.text)
        self.login();_,rev=self.stored();self.action('rotate_code',revision=rev)
        self.assertEqual(public.get('/public/print?kind=rankings').status_code,302)
