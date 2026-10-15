from contextlib import closing
import copy,json,unittest
from app import domain as d
from app.web import connect
from tests import test_web

class OperationsTests(unittest.TestCase):
    setUp=test_web.WebTests.setUp
    tearDown=test_web.WebTests.tearDown
    login=test_web.WebTests.login
    token=test_web.WebTests.token
    post=test_web.WebTests.post
    def prepare(self):
        c=self.c;c['open']=[];d.generate(c);t=c['tables'][0]
        t.update(area='aire',referee='3',judges=['0','1','2']);d.draw(c,t)
        c['areas'].append(dict(id='other',name='Autre aire',assistant='assistant2'))
        other=copy.deepcopy(t);other.update(id='other-table',area='other');c['tables'].append(other)
        with closing(connect(self.app.config['DATABASE'])) as db:
            db.execute('UPDATE competitions SET state=? WHERE id=?',(json.dumps(c),c['id']));db.commit()
        return t
    def test_manager_workspaces_and_preparation_redirect(self):
        t=self.prepare();self.login();base='/c/'+self.c['id']
        prep=self.client.get(base);self.assertEqual(prep.status_code,200,prep.text)
        self.assertIn('name="action" value="configure"',prep.text)
        self.assertNotIn('name="action" value="start_table"',prep.text)
        op=self.client.get(base+'/operations');self.assertEqual(op.status_code,200,op.text)
        self.assertIn('Lancer le tableau',op.text);self.assertNotIn('name="action" value="configure"',op.text)
        self.assertNotIn('2000-04-12',op.text)
        filtered=self.client.get(base+'/operations?area=aire')
        self.assertNotIn('data-operation-table="other-table"',filtered.text)
        self.assertIn('data-operation-table="'+t['id']+'"',filtered.text)
        r=self.post(base+'/action',dict(action='configure',revision=0,table=t['id'],area='aire',referee='3',rounds=2,seconds=60,rest=30,judges=['0','1','2']))
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json['redirect'],base+'#tableaux')
    def test_assistant_landing_and_scope(self):
        self.prepare();self.login('assistant');base='/c/'+self.c['id']
        r=self.client.get(base);self.assertEqual(r.status_code,302);self.assertTrue(r.location.endswith('/operations'))
        r=self.client.get(base+'/operations');self.assertEqual(r.status_code,200,r.text)
        for text in ['Autre aire','other-table',self.c['code'],'2000-04-12']:self.assertNotIn(text,r.text)
        self.assertEqual(self.client.get(base+'/operations?area=other').status_code,404)
    def test_club_and_unrelated_organizer_denied(self):
        self.prepare()
        for user in ['club','outsider']:
            self.login(user);self.assertEqual(self.client.get('/c/'+self.c['id']+'/operations').status_code,403)
