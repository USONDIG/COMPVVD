"""Application web hébergée, SQLite et contrôle des accès côté serveur."""
from contextlib import closing
from datetime import date
import getpass
import hashlib
import hmac
import io
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
import time
import zipfile
from xml.sax.saxutils import escape

import click
from flask import Flask, abort, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from . import domain as d

SCHEMA = """
CREATE TABLE IF NOT EXISTS clubs(id TEXT PRIMARY KEY,name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL,username TEXT NOT NULL UNIQUE COLLATE NOCASE,
 role TEXT NOT NULL,club TEXT REFERENCES clubs(id),password TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS competitions(id TEXT PRIMARY KEY,state TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,stamp REAL,actor TEXT,competition TEXT,action TEXT,detail TEXT);
CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY,stamp REAL,count INTEGER);
"""

def connect(path):
    db=sqlite3.connect(path,timeout=15)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    return db

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def password(value):
    d.require(isinstance(value,str) and 12<=len(value)<=256, "Mot de passe : 12 à 256 caractères.")
    return generate_password_hash(value)

def text(value,label):
    d.require(isinstance(value,str) and 0<len(value.strip())<=120, label+" requis (120 caractères maximum).")
    return value.strip()

def rows(query,args=()):
    return [dict(r) for r in g.db.execute(query,args)]

def find(items,ident):
    value=next((x for x in items if x["id"]==ident),None)
    d.require(value is not None,"Élément introuvable.")
    return value

def managed(c):
    return g.user and (g.user["role"]=="admin" or (g.user["role"]=="organizer" and c["owner"]==g.user["id"]))

def manager(c):
    if not managed(c):
        abort(403)

def operator(c,t):
    if managed(c):
        return
    a=next((a for a in c["areas"] if a["id"]==t["area"]),{})
    if not (g.user["role"]=="assistant" and a.get("assistant")==g.user["id"]):
        abort(403)

def visible(c):
    return managed(c) or g.user["role"]=="club" or any(a["assistant"]==g.user["id"] for a in c["areas"])

def competition(cid):
    r=g.db.execute("SELECT * FROM competitions WHERE id=?",(cid,)).fetchone()
    if not r:
        abort(404)
    c=json.loads(r["state"])
    c["revision"]=r["revision"]
    return c

def audit(action,cid=None,detail=None):
    g.db.execute("INSERT INTO audit(stamp,actor,competition,action,detail) VALUES(?,?,?,?,?)",
                 (time.time(),g.user and g.user["id"],cid,action,json.dumps(detail or {},ensure_ascii=False)))

def throttle(key,maximum=15):
    now=time.time()
    r=g.db.execute("SELECT * FROM attempts WHERE key=?",(key,)).fetchone()
    if r and now-r["stamp"]<900:
        if r["count"]>=maximum:
            abort(429,description="Trop de tentatives. Réessayez dans quinze minutes.")
        g.db.execute("UPDATE attempts SET count=count+1 WHERE key=?",(key,))
    else:
        g.db.execute("INSERT OR REPLACE INTO attempts VALUES(?,?,1)",(key,now))
    g.db.execute("DELETE FROM attempts WHERE stamp<?",(now-86400,))
    g.db.commit()
    g.db.execute("BEGIN IMMEDIATE")

def participant(data,c,club):
    name=text(data.get("name"),"Nom")
    birth=date.fromisoformat(data.get("birth",""))
    d.require(birth<=date.today(),"Date de naissance future.")
    sex=data.get("sex")
    d.require(sex in ("F","M"),"Sexe invalide.")
    weight=float(data.get("weight",""))
    d.require(math.isfinite(weight) and 1<=weight<=350,"Poids invalide.")
    grade=d.integer(int(data.get("grade","")),0,5,"Grade")
    disciplines=data.getlist("disciplines")
    d.require(disciplines and len(set(disciplines))==len(disciplines) and all(x in d.DISCIPLINES for x in disciplines),"Disciplines invalides.")
    p=dict(name=name,birth=birth.isoformat(),sex=sex,weight=weight,grade=grade,club=club,disciplines=disciplines)
    d.age_index(p,c)
    if "Combat équipe" in disciplines:
        d.require(c["season"]-birth.year>=18,"Combat équipe réservé aux seniors.")
    return p

def mutate(c,action,data):
    if action=="register":
        if g.user["role"]!="club":
            abort(403)
        p=participant(data,c,g.user["club"])
        d.require(all(x in c["open"] for x in p["disciplines"]),"Une discipline sélectionnée est fermée.")
        d.require(not any(t["discipline"] in p["disciplines"] for t in c["tables"]),"Les tableaux de cette discipline sont déjà générés.")
        d.require(not any(x["name"].casefold()==p["name"].casefold() and x["birth"]==p["birth"] and x["club"]==p["club"] for x in c["people"]),"Participant déjà inscrit.")
        c["people"].append(dict(p,id=d.uid(),status="pending"))
        return
    operator_actions={"start_table","advance","start","pause","score","sudden","decision"}
    if action not in operator_actions:
        manager(c)
    if action in ("approve","reject","edit"):
        p=find(c["people"],data.get("person"))
        d.require(not any(p["id"] in t["members"] for t in c["tables"]),"Inscription verrouillée : participant déjà dans un tableau.")
        if action=="edit":
            new=participant(data,c,p["club"])
            d.require(not any(x["id"]!=p["id"] and x["club"]==p["club"] and x["name"].casefold()==new["name"].casefold() and x["birth"]==new["birth"] for x in c["people"]),"Inscription en double.")
            p.update(new)
        else:
            p["status"]="approved" if action=="approve" else "rejected"
    elif action=="discipline":
        name=data.get("discipline")
        d.require(name in d.DISCIPLINES,"Discipline invalide.")
        if name in c["open"]:
            c["open"].remove(name)
        else:
            d.require(not any(t["discipline"]==name for t in c["tables"]),"Tableaux déjà générés.")
            c["open"].append(name)
    elif action=="weights":
        d.require(not c["tables"],"Catégories verrouillées après génération.")
        new={}
        for sex in ("F","M"):
            new[sex]=[]
            for i in range(8):
                values=[float(v.strip()) for v in data.get(sex+str(i),"").split(",")]
                d.require(1<=len(values)<=30 and all(math.isfinite(v) and 1<v<350 for v in values) and values==sorted(set(values)),"Bornes de poids invalides : ordre strictement croissant requis.")
                new[sex].append(values)
        c["weights"]=new
    elif action=="area":
        aid=data.get("assistant")
        d.require(g.db.execute("SELECT id FROM users WHERE id=? AND role='assistant' AND active=1",(aid,)).fetchone(),"Assistant actif requis.")
        d.require(not any(a["assistant"]==aid for a in c["areas"]),"Cet assistant a déjà une aire.")
        c["areas"].append(dict(id=d.uid(),name=text(data.get("name"),"Aire"),assistant=aid))
    elif action=="official":
        c["officials"].append(dict(id=d.uid(),name=text(data.get("name"),"Nom"),qualification=text(data.get("qualification"),"Qualification")))
    elif action=="generate":
        d.generate(c)
    elif action=="merge":
        source,target=find(c["tables"],data.get("source")),find(c["tables"],data.get("target"))
        d.require(source!=target and source["status"]==target["status"]=="draft","Fusion entre deux tableaux avant tirage uniquement.")
        target["members"]+=source["members"]
        target["name"]+=" / "+source["name"]
        c["tables"].remove(source)
    elif action=="rotate_code":
        c["code"]=secrets.token_hex(6).upper()
    elif action in {"configure","draw","correct"}|operator_actions:
        t=find(c["tables"],data.get("table"))
        operator(c,t)
        if action=="configure":
            d.require(t["status"] in ("draft","ready"),"Le tableau a déjà commencé.")
            find(c["areas"],data.get("area"))
            judges=data.getlist("judges")
            referee=data.get("referee")
            d.require(len(judges)==3 and len(set(judges+[referee]))==4,"Trois juges distincts et un arbitre distinct requis.")
            for official in judges+[referee]:
                find(c["officials"],official)
            t.update(area=data["area"],judges=judges,referee=referee,
                     rounds=d.integer(int(data["rounds"]),1,20,"Rounds"),
                     seconds=d.integer(int(data["seconds"]),1,1800,"Durée"),
                     rest=d.integer(int(data["rest"]),0,600,"Pause"))
        elif action=="draw":
            d.draw(c,t)
        elif action=="start_table":
            area=find(c["areas"],t["area"])
            d.require(g.db.execute("SELECT id FROM users WHERE id=? AND active=1",(area["assistant"],)).fetchone(),"Assistant désactivé.")
            d.start_table(c,t)
        elif action=="advance":
            d.advance(c,t)
        else:
            m=find(t["matches"],data.get("match"))
            if action=="correct":
                d.require(not any(x["id"]!=t["id"] and x["status"]=="active" and x["area"]==t["area"] for x in c["tables"]),"Cette aire accueille un autre tableau.")
                count=d.integer(int(data["count"]),0,22,"Nombre de rounds")
                scores=[[[int(data[f"r{i}_{s}_{j}"]) for j in range(3)] for s in range(2)] for i in range(count)]
                d.correct(t,m,scores,data.get("winner"),data.get("reason"),data.getlist("votes"))
                return
            d.require(t["status"]=="active","Le tableau n’est pas en cours.")
            if action=="start":
                d.start_round(c,t,m)
            elif action=="pause":
                d.pause(m)
            elif action=="score":
                scores=[[int(data[f"{s}{j}"]) for j in range(3)] for s in ("a","b")]
                d.score(t,m,scores)
            elif action=="sudden":
                d.sudden(m,data.getlist("votes"))
            elif action=="decision":
                d.require(m["state"] in ("pending","running","paused","rest"),"Résultat déjà validé.")
                d.require(data.get("reason") in ("forfait","abandon","disqualification"),"Motif invalide.")
                d.finish(m,data.get("winner"),data["reason"])
    else:
        raise d.RuleError("Action inconnue.")

def public_view(c):
    out={k:c[k] for k in ("id","name","date","season","areas","tables")}
    out["areas"]=[dict(id=a["id"],name=a["name"]) for a in c["areas"]]
    out["people"]=[{k:p[k] for k in ("id","name","club")} for p in c["people"] if p["status"]=="approved"]
    out["rankings"]=d.rankings(c)
    return out

def excel(rows_data):
    def column(i):
        out=""
        while i:
            i,r=divmod(i-1,26)
            out=chr(65+r)+out
        return out
    body=[]
    for ri,row in enumerate(rows_data,1):
        cells=[]
        for ci,value in enumerate(row,1):
            value="".join(c for c in str(value) if ord(c)>=32 or c in "\t\n\r")
            cells.append(f'<c r="{column(ci)}{ri}" t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>')
        body.append(f'<row r="{ri}">'+"".join(cells)+"</row>")
    files={
        "[Content_Types].xml":'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels":'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml":'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Inscriptions" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels":'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml":'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+"".join(body)+'</sheetData></worksheet>'}
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for key,value in files.items():
            z.writestr(key,'<?xml version="1.0" encoding="UTF-8"?>'+value)
    out.seek(0)
    return out

def create_app(config=None):
    app=Flask(__name__)
    app.config.update(DATABASE=os.environ.get("DATABASE_PATH","data/compvvd.sqlite3"),
        SECRET_KEY=os.environ.get("SECRET_KEY"),SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE","true")!="false",
        SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE="Strict",MAX_CONTENT_LENGTH=200000,
        MAX_FORM_PARTS=200,PERMANENT_SESSION_LIFETIME=43200)
    if config:
        app.config.update(config)
    path=Path(app.config["DATABASE"])
    path.parent.mkdir(parents=True,exist_ok=True)
    if not app.config["SECRET_KEY"]:
        secret=path.parent/".session-secret"
        if not secret.exists():
            fd=os.open(secret,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,"w") as out:
                out.write(secrets.token_hex(32))
        app.config["SECRET_KEY"]=secret.read_text().strip()
    with closing(connect(str(path))) as db:
        db.executescript(SCHEMA)
        db.commit()

    @app.before_request
    def before():
        g.db=connect(app.config["DATABASE"])
        g.user=None
        session.setdefault("csrf",secrets.token_hex(32))
        if session.get("sid"):
            r=g.db.execute("SELECT u.id,u.name,u.username,u.role,u.club FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.id=? AND s.expires>? AND u.active=1",(digest(session["sid"]),time.time())).fetchone()
            g.user=dict(r) if r else None
        if request.method=="POST":
            supplied=request.form.get("csrf","")
            if not hmac.compare_digest(session["csrf"],supplied):
                abort(403,description="Jeton de sécurité invalide. Rechargez la page.")
            g.db.execute("BEGIN IMMEDIATE")
        if request.endpoint not in ("login","public","health","static") and not g.user:
            if request.method=="GET":
                return redirect(url_for("login"))
            abort(401)

    @app.after_request
    def after(response):
        if hasattr(g,"db"):
            if response.status_code<400:
                g.db.commit()
            else:
                g.db.rollback()
        response.headers.update({"Cache-Control":"no-store","X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY",
            "Referrer-Policy":"no-referrer","Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            "Permissions-Policy":"camera=(), microphone=(), geolocation=()"})
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"]="max-age=31536000"
        return response

    @app.teardown_request
    def teardown(exc):
        if hasattr(g,"db"):
            g.db.close()

    @app.errorhandler(Exception)
    def error(exc):
        if isinstance(exc,HTTPException):
            code,message=exc.code,exc.description
        elif isinstance(exc,d.RuleError):
            code,message=422,str(exc)
        elif isinstance(exc,sqlite3.IntegrityError):
            code,message=409,"Ce nom ou identifiant existe déjà, ou la référence est invalide."
        elif isinstance(exc,(ValueError,TypeError,KeyError)):
            code,message=400,"Données invalides. Vérifiez les champs."
        else:
            app.logger.exception("Application error")
            code,message=500,"Erreur interne. Contactez l’organisateur."
        if request.headers.get("X-Requested-With")=="fetch":
            return jsonify(error=message),code
        return render_template("error.html",message=message,code=code),code

    @app.context_processor
    def context():
        return dict(csrf=session.get("csrf",""),user=g.user,grades=d.GRADES,disciplines=d.DISCIPLINES,ages=d.AGES,
                    labels={"draft":"À préparer","ready":"Prêt","active":"En cours","closed":"Clôturé","pending":"En attente","approved":"Approuvé","rejected":"Refusé","running":"En cours","paused":"Suspendu","rest":"Pause","done":"Terminé"},
                    roles={"admin":"Administrateur","organizer":"Organisateur","club":"Responsable de club","assistant":"Assistant de table"},
                    now=time.time())

    def done(location):
        if request.headers.get("X-Requested-With")=="fetch":
            return jsonify(redirect=location)
        return redirect(location)

    @app.get("/health")
    def health():
        g.db.execute("SELECT 1 FROM competitions LIMIT 1")
        return jsonify(ok=True)

    @app.route("/login",methods=["GET","POST"])
    def login():
        if request.method=="POST":
            name=text(request.form.get("username"),"Identifiant")
            throttle("login:"+name.casefold())
            pwd=request.form.get("password","")
            d.require(len(pwd)<=256,"Mot de passe trop long.")
            u=g.db.execute("SELECT * FROM users WHERE username=? AND active=1",(name,)).fetchone()
            if not u or not check_password_hash(u["password"],pwd):
                abort(401,description="Identifiant ou mot de passe incorrect.")
            if session.get("sid"):
                g.db.execute("DELETE FROM sessions WHERE id=?",(digest(session["sid"]),))
            session.clear()
            session.update(csrf=secrets.token_hex(32),sid=secrets.token_urlsafe(32))
            session.permanent=True
            g.db.execute("DELETE FROM sessions WHERE expires<?",(time.time(),))
            g.db.execute("INSERT INTO sessions VALUES(?,?,?)",(digest(session["sid"]),u["id"],time.time()+43200))
            g.db.execute("DELETE FROM attempts WHERE key=?",("login:"+name.casefold(),))
            return done("/")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        g.db.execute("DELETE FROM sessions WHERE id=?",(digest(session.get("sid","")),))
        session.clear()
        return done("/login")

    @app.route("/",methods=["GET","POST"])
    def home():
        if request.method=="POST":
            if g.user["role"] not in ("admin","organizer"):
                abort(403)
            owner=request.form.get("owner") if g.user["role"]=="admin" else g.user["id"]
            d.require(g.db.execute("SELECT id FROM users WHERE id=? AND role IN ('admin','organizer') AND active=1",(owner,)).fetchone(),"Organisateur invalide.")
            c=d.new_competition(text(request.form.get("name"),"Nom"),request.form["date"],int(request.form["season"]),owner)
            g.db.execute("INSERT INTO competitions VALUES(?,?,0)",(c["id"],json.dumps(c)))
            audit("create_competition",c["id"])
            return done("/c/"+c["id"])
        comps=[json.loads(r["state"]) for r in g.db.execute("SELECT state FROM competitions")]
        comps=[c for c in comps if visible(c)]
        users=rows("SELECT id,name,role FROM users WHERE active=1 AND role IN ('admin','organizer')") if g.user["role"]=="admin" else []
        return render_template("home.html",comps=comps,users=users)

    @app.route("/admin",methods=["GET","POST"])
    def admin():
        if g.user["role"]!="admin":
            abort(403)
        if request.method=="POST":
            data=request.form
            action=data.get("action")
            if action=="club":
                g.db.execute("INSERT INTO clubs VALUES(?,?)",(d.uid(),text(data.get("name"),"Club")))
            elif action=="user":
                role=data.get("role")
                d.require(role in ("admin","organizer","club","assistant"),"Rôle invalide.")
                club=data.get("club") if role=="club" else None
                d.require(role!="club" or g.db.execute("SELECT id FROM clubs WHERE id=?",(club,)).fetchone(),"Club requis.")
                g.db.execute("INSERT INTO users(id,name,username,role,club,password) VALUES(?,?,?,?,?,?)",
                    (d.uid(),text(data.get("name"),"Nom"),text(data.get("username"),"Identifiant"),role,club,password(data.get("password"))))
            elif action in ("disable","reset"):
                target=data.get("user")
                d.require(target!=g.user["id"] and g.db.execute("SELECT id FROM users WHERE id=?",(target,)).fetchone(),"Compte cible invalide.")
                if action=="disable":
                    g.db.execute("UPDATE users SET active=0 WHERE id=?",(target,))
                else:
                    g.db.execute("UPDATE users SET password=? WHERE id=?",(password(data.get("password")),target))
                g.db.execute("DELETE FROM sessions WHERE user_id=?",(target,))
            else:
                abort(400)
            audit(action,detail={"user":data.get("user")})
            return done("/admin")
        return render_template("admin.html",users=rows("SELECT id,name,username,role,club,active FROM users"),clubs=rows("SELECT * FROM clubs"))

    @app.route("/account",methods=["GET","POST"])
    def account():
        if request.method=="POST":
            current=g.db.execute("SELECT password FROM users WHERE id=?",(g.user["id"],)).fetchone()[0]
            d.require(check_password_hash(current,request.form.get("current","")),"Mot de passe actuel incorrect.")
            g.db.execute("UPDATE users SET password=? WHERE id=?",(password(request.form.get("password")),g.user["id"]))
            g.db.execute("DELETE FROM sessions WHERE user_id=? AND id<>?",(g.user["id"],digest(session["sid"])))
            audit("password_changed")
            return done("/account")
        return render_template("account.html")

    @app.get("/c/<cid>")
    def view(cid):
        c=competition(cid)
        if not visible(c):
            abort(403)
        is_manager=managed(c)
        if g.user["role"]=="club":
            c["people"]=[p for p in c["people"] if p["club"]==g.user["club"]]
            c["tables"],c["areas"],c["officials"]=[],[],[]
            c.pop("code",None)
        elif not is_manager:
            c["people"]=[{k:p[k] for k in ("id","name","club")} for p in c["people"]]
            c["tables"]=[t for t in c["tables"] if any(a["id"]==t["area"] and a["assistant"]==g.user["id"] for a in c["areas"])]
            c.pop("code",None)
        return render_template("competition.html",c=c,manager=is_manager,
            clubs={r["id"]:r["name"] for r in rows("SELECT * FROM clubs")},
            assistants=rows("SELECT id,name FROM users WHERE role='assistant' AND active=1") if is_manager else [],
            rankings=d.rankings(c) if is_manager else None)

    @app.post("/c/<cid>/action")
    def action(cid):
        c=competition(cid)
        if not visible(c):
            abort(403)
        if int(request.form.get("revision",-1))!=c["revision"]:
            abort(409,description="Un autre poste a modifié la compétition. Actualisez avant de recommencer ; la saisie actuelle est conservée.")
        name=request.form.get("action")
        before=json.loads(json.dumps(c))
        mutate(c,name,request.form)
        revision=c.pop("revision")
        g.db.execute("UPDATE competitions SET state=?,revision=revision+1 WHERE id=?",(json.dumps(c,ensure_ascii=False),cid))
        detail={k:request.form.getlist(k) for k in request.form if k not in ("csrf","revision")}
        if name=="correct":
            detail["before"]=[m for t in before["tables"] for m in t["matches"] if m["id"]==request.form.get("match")]
        audit(name,cid,detail)
        dest="/c/"+cid
        if request.form.get("table"):
            dest+="/table/"+request.form["table"]
        return done(dest)

    @app.get("/c/<cid>/table/<tid>")
    def table(cid,tid):
        c=competition(cid)
        t=find(c["tables"],tid)
        operator(c,t)
        return render_template("table.html",c=c,t=t,manager=managed(c),people={p["id"]:p for p in c["people"]},
            officials={o["id"]:o["name"] for o in c["officials"]},area=next((a for a in c["areas"] if a["id"]==t["area"]),{}))

    @app.get("/c/<cid>/export")
    def export(cid):
        c=competition(cid)
        if not (managed(c) or g.user["role"]=="club"):
            abort(403)
        clubs={r["id"]:r["name"] for r in rows("SELECT * FROM clubs")}
        data=[["Nom","Date de naissance","Sexe","Poids kg","Grade","Club","Disciplines","Statut"]]
        for p in c["people"]:
            if g.user["role"]!="club" or p["club"]==g.user["club"]:
                data.append([p["name"],p["birth"],p["sex"],p["weight"],d.GRADES[p["grade"]],clubs[p["club"]],", ".join(p["disciplines"]),p["status"]])
        return send_file(excel(data),as_attachment=True,download_name="inscriptions.xlsx",mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    @app.get("/c/<cid>/audit")
    def history(cid):
        c=competition(cid)
        manager(c)
        events=rows("SELECT a.*,u.name actor_name FROM audit a LEFT JOIN users u ON a.actor=u.id WHERE competition=? ORDER BY a.id DESC LIMIT 200",(cid,))
        return render_template("audit.html",c=c,events=events)

    @app.route("/public",methods=["GET","POST"])
    def public():
        if request.method=="POST":
            code=request.form.get("code","").strip().upper()
            c=None
            for r in g.db.execute("SELECT state FROM competitions"):
                candidate=json.loads(r[0])
                if hmac.compare_digest(candidate["code"],code):
                    c=candidate
            if c is None:
                throttle("public:"+(request.remote_addr or "?"),30)
                abort(404,description="Code de compétition invalide.")
            session["public_id"],session["public_digest"]=c["id"],digest(c["code"])
            session.permanent=True
            return done("/public")
        c=None
        if session.get("public_id"):
            try:
                source=competition(session["public_id"])
                if hmac.compare_digest(digest(source["code"]),session.get("public_digest","")):
                    c=public_view(source)
            except HTTPException:
                pass
        return render_template("public.html",c=c,clubs={r["id"]:r["name"] for r in rows("SELECT * FROM clubs")})

    @app.cli.command("create-admin")
    @click.option("--username",prompt=True)
    @click.option("--name",prompt=True)
    def create_admin(username,name):
        pwd=getpass.getpass("Mot de passe (12 caractères minimum) : ")
        if pwd!=getpass.getpass("Confirmation : "):
            raise click.ClickException("Les mots de passe diffèrent.")
        with closing(connect(app.config["DATABASE"])) as db:
            db.execute("INSERT INTO users(id,name,username,role,password) VALUES(?,?,?,?,?)",
                       (d.uid(),text(name,"Nom"),text(username,"Identifiant"),"admin",password(pwd)))
            db.commit()
        click.echo("Administrateur créé.")

    @app.cli.command("backup")
    @click.argument("destination")
    def backup(destination):
        with closing(connect(app.config["DATABASE"])) as source, closing(sqlite3.connect(destination)) as target:
            source.backup(target)
        click.echo("Sauvegarde SQLite cohérente créée.")

    return app
