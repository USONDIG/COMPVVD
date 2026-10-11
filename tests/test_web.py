from contextlib import closing
import io
import json
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from werkzeug.datastructures import MultiDict
from app import domain as d
from app.web import create_app,connect,password
from tests.test_domain import fixture,win

TEST_PASSWORD=secrets.token_urlsafe(24)
HASH=password(TEST_PASSWORD)

def seed(app):
    with closing(connect(app.config["DATABASE"])) as db:
        for cid in ("club-a","club-b"):
            db.execute("INSERT INTO clubs VALUES(?,?)",(cid,cid))
        for ident,role,club in (("admin","admin",None),("organizer","organizer",None),("outsider","organizer",None),
                                ("club","club","club-a"),("club2","club","club-b"),("assistant","assistant",None),("assistant2","assistant",None)):
            db.execute("INSERT INTO users(id,name,username,role,club,password) VALUES(?,?,?,?,?,?)",(ident,ident,ident,role,club,HASH))
        c=d.new_competition("Coupe de test","2026-11-01",2026,"organizer")
        c["people"]=[dict(id="p1",name="Alice privée",club="club-a",birth="2000-04-12",grade=2,sex="F",weight=52,disciplines=["Combat"],status="approved"),
                     dict(id="p2",name="Béatrice privée",club="club-b",birth="2000-09-23",grade=3,sex="F",weight=51,disciplines=["Combat"],status="approved")]
        c["areas"]=[dict(id="aire",name="Tatami 1",assistant="assistant")]
        c["officials"]=[dict(id=str(i),name=f"Juge {i}",qualification="Arbitre") for i in range(4)]
        db.execute("INSERT INTO competitions VALUES(?,?,0)",(c["id"],json.dumps(c)))
        db.commit()
    return c

class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=create_app(dict(TESTING=True,DATABASE=str(Path(self.tmp.name)/"test.sqlite3"),SECRET_KEY="test-key",SESSION_COOKIE_SECURE=False))
        self.c=seed(self.app)
        self.client=self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def token(self,client=None):
        client=client or self.client
        with client.session_transaction() as s:
            return s["csrf"]

    def login(self,name="admin",client=None):
        client=client or self.client
        client.get("/login")
        r=client.post("/login",data=dict(csrf=self.token(client),username=name,password=TEST_PASSWORD),headers={"X-Requested-With":"fetch"})
        self.assertEqual(r.status_code,200,r.data)
        return client

    def post(self,path,data,client=None):
        client=client or self.client
        data=MultiDict(data)
        data.add("csrf",self.token(client))
        return client.post(path,data=data,headers={"X-Requested-With":"fetch"})

    def action(self,action,revision=0,**kw):
        return self.post("/c/"+self.c["id"]+"/action",dict(action=action,revision=revision,**kw))

    def stored(self):
        with closing(connect(self.app.config["DATABASE"])) as db:
            r=db.execute("SELECT state,revision FROM competitions WHERE id=?",(self.c["id"],)).fetchone()
            return json.loads(r[0]),r[1]

    def test_login_required_and_csrf(self):
        self.assertEqual(self.client.get("/").status_code,302)
        self.client.get("/login")
        self.assertEqual(self.client.post("/login",data=dict(username="admin",password=TEST_PASSWORD)).status_code,403)

    def test_club_sees_only_own_private_records(self):
        self.login("club")
        r=self.client.get("/c/"+self.c["id"])
        self.assertEqual(r.status_code,200,r.data)
        self.assertIn("Alice privée",r.text)
        self.assertNotIn("Béatrice privée",r.text)
        self.assertNotIn("2000-09-23",r.text)
        self.assertNotIn(self.c["code"],r.text)

    def test_club_cannot_approve_or_open_admin(self):
        self.login("club")
        self.assertEqual(self.action("approve",person="p1").status_code,403)
        self.assertEqual(self.client.get("/admin").status_code,403)
        self.assertEqual(self.stored()[1],0)

    def test_organizer_scope(self):
        self.login("outsider")
        self.assertEqual(self.client.get("/c/"+self.c["id"]).status_code,403)
        self.assertEqual(self.action("generate").status_code,403)

    def test_stale_revision_refused(self):
        self.login()
        self.assertEqual(self.action("discipline",discipline="Combat").status_code,200)
        r=self.action("generate")
        self.assertEqual(r.status_code,409)
        self.assertEqual(self.stored()[0]["tables"],[])

    def test_transaction_rolls_back_invalid_action(self):
        self.login()
        r=self.action("weights",F0="broken")
        self.assertEqual(r.status_code,400)
        self.assertEqual(self.stored()[0]["weights"],d.WEIGHTS)
        self.assertEqual(self.stored()[1],0)

    def test_register_approve_generate_workflow(self):
        self.login("club")
        r=self.action("register",name="Caroline",birth="2000-03-10",sex="F",weight="53",grade="1",disciplines=["Combat"])
        self.assertEqual(r.status_code,200,r.data)
        c,rev=self.stored()
        p=c["people"][-1]
        self.assertEqual(p["status"],"pending")
        self.login("organizer")
        self.assertEqual(self.action("approve",revision=rev,person=p["id"]).status_code,200)
        self.assertEqual(self.action("discipline",revision=rev+1,discipline="Combat").status_code,200)
        self.assertEqual(self.action("generate",revision=rev+2).status_code,200)
        self.assertEqual(len(self.stored()[0]["tables"]),1)
        self.assertEqual(self.action("edit",revision=rev+3,person="p1").status_code,422)

    def test_public_code_and_privacy_and_rotation(self):
        self.client.get("/public")
        r=self.post("/public",dict(code=self.c["code"]))
        self.assertEqual(r.status_code,200)
        r=self.client.get("/public")
        self.assertEqual(r.status_code,200,r.data)
        self.assertIn("Alice privée",r.text)
        self.assertNotIn("2000-04-12",r.text)
        self.assertNotIn("52 kg",r.text)
        self.assertNotIn(self.c["code"],r.text)
        self.login()
        self.action("rotate_code")
        self.assertIn("Saisissez le code",self.client.get("/public").text)

    def test_export_scoped_and_valid_excel(self):
        self.login("club")
        r=self.client.get("/c/"+self.c["id"]+"/export")
        self.assertEqual(r.status_code,200)
        with zipfile.ZipFile(io.BytesIO(r.data)) as z:
            xml=z.read("xl/worksheets/sheet1.xml").decode()
        self.assertIn("Alice privée",xml)
        self.assertNotIn("Béatrice privée",xml)

    def test_assistant_scope_and_render_table(self):
        self.login()
        self.action("discipline",discipline="Combat")
        self.action("generate",revision=1)
        c,rev=self.stored();t=c["tables"][0]
        fields=MultiDict([("action","configure"),("revision",str(rev)),("table",t["id"]),("area","aire"),("referee","3"),
                          ("rounds","2"),("seconds","60"),("rest","30"),("judges","0"),("judges","1"),("judges","2")])
        r=self.post("/c/"+c["id"]+"/action",fields)
        self.assertEqual(r.status_code,200,r.data)
        self.action("draw",revision=3,table=t["id"])
        self.login("assistant2")
        self.assertEqual(self.client.get(f'/c/{c["id"]}/table/{t["id"]}').status_code,403)
        self.login("assistant")
        r=self.client.get(f'/c/{c["id"]}/table/{t["id"]}')
        self.assertEqual(r.status_code,200,r.data)
        r=self.action("start_table",revision=4,table=t["id"])
        self.assertEqual(r.status_code,200,r.data)
        c,rev=self.stored();m=c["tables"][0]["matches"][0]
        self.assertEqual(self.action("start",revision=rev,table=t["id"],match=m["id"]).status_code,200)
        r=self.client.get(f'/c/{c["id"]}/table/{t["id"]}')
        self.assertIn("Valider les six scores",r.text)
        self.assertEqual(r.status_code,200,r.data)

    def test_xss_escaped(self):
        self.login()
        self.post("/admin",dict(action="club",name='<script>alert(1)</script>'))
        r=self.client.get("/admin")
        self.assertNotIn("<script>alert(1)</script>",r.text)
        self.assertIn("&lt;script&gt;",r.text)

    def test_account_disable_revokes_session(self):
        other=self.login("club",self.app.test_client())
        self.login()
        self.post("/admin",dict(action="disable",user="club"))
        self.assertEqual(other.get("/").status_code,302)

    def test_error_forms_and_headers(self):
        self.login()
        for path in ("/","/admin","/account","/c/"+self.c["id"],"/c/"+self.c["id"]+"/audit"):
            r=self.client.get(path)
            self.assertEqual(r.status_code,200,(path,r.data))
            self.assertIn("default-src 'self'",r.headers["Content-Security-Policy"])
            self.assertEqual(r.headers["Cache-Control"],"no-store")

    def test_rate_limit_login(self):
        self.client.get("/login")
        for _ in range(15):
            r=self.post("/login",dict(username="wrong",password="wrong"))
            self.assertEqual(r.status_code,401)
        self.assertEqual(self.post("/login",dict(username="wrong",password="wrong")).status_code,429)

    def test_lutte_operator_flow_and_correction(self):
        c=self.c
        c['open']=[]
        for p in c['people']: p['disciplines'].append('Lutte')
        with closing(connect(self.app.config['DATABASE'])) as db:
            db.execute('UPDATE competitions SET state=? WHERE id=?',(json.dumps(c),c['id']))
            db.commit()
        self.login('organizer')
        def act(name,**kw):
            _,rev=self.stored()
            r=self.action(name,revision=rev,**kw)
            self.assertEqual(r.status_code,200,r.data)
        act('generate',discipline='Lutte')
        c,_=self.stored(); t=c['tables'][0]; tid=t['id']
        act('configure',table=tid,area='aire',referee='3',rounds='1',seconds='30',rest='10')
        act('draw',table=tid)
        self.login('assistant2')
        _,rev=self.stored()
        self.assertEqual(self.action('start_table',revision=rev,table=tid).status_code,403)
        self.login('assistant')
        act('start_table',table=tid)
        c,_=self.stored(); m=c['tables'][0]['matches'][0]; mid=m['id']
        act('start',table=tid,match=mid)
        page=self.client.get(f'/c/{c["id"]}/table/{tid}')
        self.assertEqual(page.status_code,200)
        self.assertIn('Valider les scores du round',page.text)
        self.assertNotIn('Valider les six scores',page.text)
        c,rev=self.stored()
        self.assertEqual(c['tables'][0]['matches'][0]['timer']['duration'],30)
        self.assertEqual(self.action('sudden',revision=rev,table=tid,match=mid).status_code,422)
        self.assertEqual(self.action('score',revision=rev,table=tid,match=mid,a0='2',b0='0').status_code,422)
        with patch('app.domain.time.time',return_value=c['tables'][0]['matches'][0]['timer']['since']+31):
            act('score',table=tid,match=mid,a0='2',b0='0')
        self.login('organizer')
        act('correct',table=tid,match=mid,count='1',r0_0_0='0',r0_1_0='2',winner=m['b'],reason='points',duration='35.7')
        c,_=self.stored(); result=c['tables'][0]['matches'][0]
        self.assertEqual(result['winner'],m['b'])
        self.assertEqual(result['timer']['elapsed'],35.7)
        act('advance',table=tid)
        c,_=self.stored()
        self.assertEqual(c['tables'][0]['status'],'closed')

