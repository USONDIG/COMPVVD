from contextlib import closing
import json
import unittest
from werkzeug.datastructures import MultiDict
from app import domain as d
from app import disciplines as x
from app.web import connect
from tests import test_web
from tests.test_disciplines import teams

class DisciplineWebTests(unittest.TestCase):
    setUp=test_web.WebTests.setUp
    tearDown=test_web.WebTests.tearDown
    token=test_web.WebTests.token
    login=test_web.WebTests.login
    post=test_web.WebTests.post
    action=test_web.WebTests.action
    stored=test_web.WebTests.stored

    def save(self,c):
        with closing(connect(self.app.config['DATABASE'])) as db:
            db.execute('UPDATE competitions SET state=? WHERE id=?',(json.dumps(c),self.c['id']));db.commit()

    def act(self,action_name,**fields):
        _,rev=self.stored();r=self.action(action_name,revision=rev,**fields)
        self.assertEqual(r.status_code,200,r.data)

    def test_quyen_operator_lifecycle_and_public_privacy(self):
        c=self.c;c['open']=[]
        for p in c['people']:p['disciplines']=['Quyen']
        self.save(c);self.login('organizer');self.act('generate',discipline='Quyen')
        c,_=self.stored();tid=c['tables'][0]['id']
        self.act('configure',table=tid,area='aire',judges=['0','1','2'])
        self.act('draw',table=tid)
        self.login('assistant2');_,rev=self.stored()
        self.assertEqual(self.action('start_table',revision=rev,table=tid).status_code,403)
        self.login('assistant');self.act('start_table',table=tid)
        for stage in (1,2):
            c,_=self.stored();passes=[p for p in c['tables'][0]['passes'] if p['wave']==stage]
            for p in passes:
                self.act('quyen_start',table=tid,match=p['id'])
                page=self.client.get(f'/c/{c["id"]}/table/{tid}')
                self.assertEqual(page.status_code,200,page.data);self.assertIn('Valider les trois notes',page.text)
                self.act('quyen_pause',table=tid,match=p['id']);self.act('quyen_pause',table=tid,match=p['id'])
                _,rev=self.stored();self.assertEqual(self.action('quyen_score',revision=rev,table=tid,match=p['id'],notes=['6.01']*3).status_code,422)
                self.act('quyen_score',table=tid,match=p['id'],notes=['8.1' if p['entry']=='p1' else '9.2']*3)
            self.act('advance',table=tid)
        c,rev=self.stored();self.assertEqual(c['tables'][0]['status'],'closed')
        p=c['tables'][0]['passes'][-1]
        self.assertEqual(self.action('quyen_correct',revision=rev,table=tid,match=p['id'],notes=['7']*3).status_code,403)
        self.client.get('/public');self.post('/public',dict(code=c['code']));page=self.client.get('/public')
        self.assertEqual(page.status_code,200,page.data);self.assertIn('Classement final',page.text)
        self.assertNotIn('2000-04-12',page.text);self.assertNotIn('52 kg',page.text)
        self.login('organizer');self.act('quyen_correct',table=tid,match=p['id'],notes=['7']*3)
        self.act('advance',table=tid)
        audit=self.client.get(f'/c/{c["id"]}/audit');self.assertIn('quyen_correct',audit.text)

    def test_team_creation_lock_and_pool_pages(self):
        c=self.c;fixture=teams((3,3));c['people']=fixture['people'];c['open']=[]
        for p in c['people']:p['club']='club-a'
        self.save(c);self.login('club')
        self.assertEqual(self.action('team',name='Collectif A',discipline='Dau équipe',members=['0','1','2']).status_code,403)
        self.login('organizer')
        self.act('team',name='Collectif A',discipline='Dau équipe',members=['0','1','2'])
        self.act('team',name='Collectif B',discipline='Dau équipe',members=['3','4','5'])
        page=self.client.get('/c/'+c['id']);self.assertEqual(page.status_code,200,page.data)
        self.assertIn('Collectif A',page.text)
        _,rev=self.stored();self.assertEqual(self.action('reject',revision=rev,person='0').status_code,422)
        self.act('generate',discipline='Dau équipe');c,_=self.stored();tid=c['tables'][0]['id']
        self.act('configure',table=tid,area='aire',referee='3',judges=['0','1','2'],rounds='2',seconds='60',rest='30')
        self.act('draw',table=tid);self.login('assistant');self.act('start_table',table=tid)
        page=self.client.get(f'/c/{c["id"]}/table/{tid}');self.assertEqual(page.status_code,200,page.data);self.assertIn('Lancer la rencontre',page.text)
        c,_=self.stored();e=c['tables'][0]['encounters'][0];self.act('pool_start',table=tid,encounter=e['id'])
        c,_=self.stored();m=c['tables'][0]['matches'][0];self.act('start',table=tid,match=m['id'])
        page=self.client.get(f'/c/{c["id"]}/table/{tid}');self.assertEqual(page.status_code,200,page.data);self.assertIn('Valider les six scores',page.text)
        self.client.get('/public');self.post('/public',dict(code=c['code']));page=self.client.get('/public')
        self.assertEqual(page.status_code,200,page.data);self.assertIn('Collectif A',page.text);self.assertIn('Poule unique',page.text)

    def test_synchro_cannot_merge_senior_and_youth(self):
        c=self.c;source=teams((2,2,2,2),'Quyen synchro');c['people']=source['people'];c['teams']=source['teams'];c['open']=[]
        for p in c['people'][:4]:p['birth']='2010-01-01'
        for team in c['teams'][:2]:team['group']='Moins de 18 ans'
        d.generate(c,'Quyen synchro');self.save(c);self.login('organizer')
        a,b=c['tables'];self.assertEqual(self.action('merge',source=a['id'],target=b['id']).status_code,422)
