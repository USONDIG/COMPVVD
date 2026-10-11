"""Parcours réel Chromium desktop/mobile et captures de contrôle en CI."""
from contextlib import closing
import json
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from app.web import create_app,connect
from app import domain as d
from tests.test_web import seed,TEST_PASSWORD
from tests.test_import import file_bytes

with tempfile.TemporaryDirectory() as tmp:
    app=create_app(dict(DATABASE=str(Path(tmp)/"browser.sqlite3"),SECRET_KEY="browser-test",SESSION_COOKIE_SECURE=False))
    c=seed(app)
    c["open"]=[]
    d.generate(c)
    t=c["tables"][0]
    t.update(area="aire",judges=["0","1","2"],referee="3",seconds=5)
    d.draw(c,t)
    for i,p in enumerate(list(c['people'])):
        c['people'].append(dict(p,id=f'vat-{i}',name=f'Vat {i}',disciplines=['Vat']))
    c['areas'].append(dict(id='vat-area',name='Aire Vat',assistant='assistant2'))
    c['officials'].append(dict(id='ref-vat',name='Arbitre Vat',qualification='Arbitre'))
    d.generate(c,'Vat')
    lt=c['tables'][-1]
    lt.update(area='vat-area',judges=[],referee='ref-vat',rounds=1,seconds=5,rest=2)
    d.draw(c,lt)
    with closing(connect(app.config["DATABASE"])) as db:
        db.execute("UPDATE competitions SET state=? WHERE id=?",(json.dumps(c),c["id"]))
        registrations=d.new_competition('Inscriptions Excel','2026-11-01',2026,'organizer')
        db.execute('INSERT INTO competitions VALUES(?,?,0)',(registrations['id'],json.dumps(registrations)))
        db.commit()
    server=make_server("127.0.0.1",0,app,threaded=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{server.server_port}"
    Path("test-results").mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page(viewport={"width":1440,"height":1000})
        errors=[];page.on("pageerror",lambda err:errors.append(str(err)))
        page.on("dialog",lambda dialog:dialog.accept())
        page.goto(base+"/login")
        page.get_by_label("Identifiant").fill("assistant")
        page.get_by_label("Mot de passe",exact=True).fill(TEST_PASSWORD)
        page.get_by_role("button",name="Se connecter").click()
        page.wait_for_url(base+"/")
        page.goto(base+f'/c/{c["id"]}/table/{t["id"]}')
        page.get_by_role("button",name="Lancer le tableau").click()
        page.get_by_role("button",name="Lancer le dau").wait_for()
        page.get_by_role("button",name="Lancer le dau").click()
        page.get_by_role("button",name="Suspendre le chronomètre").wait_for()
        assert page.locator('input[name="a0"]').count()==1
        page.locator('input[name="a0"]').fill("4")
        validate=page.get_by_role("button",name="Valider les six scores")
        expect(validate).to_be_disabled()
        page.get_by_role("button",name="Suspendre le chronomètre").click()
        page.get_by_role("button",name="Reprendre le chronomètre").wait_for()
        expect(validate).to_be_disabled()
        page.get_by_role("button",name="Reprendre le chronomètre").click()
        page.get_by_role("button",name="Suspendre le chronomètre").wait_for()
        page.locator('input[name="a0"]').fill("4")
        expect(validate).to_be_enabled(timeout=10000)
        expect(page.locator(".clock")).to_have_class("clock clock-ended")
        expect(page.locator("[data-round-ended]")).to_be_visible()
        assert page.locator('input[name="a0"]').input_value()=="4"
        page.screenshot(path="test-results/table-desktop.png",full_page=True)
        page.set_viewport_size({"width":390,"height":844})
        page.screenshot(path="test-results/table-mobile.png",full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
        validate.click()
        page.get_by_role("button",name="Lancer le prochain round").wait_for()
        viewer=browser.new_page(viewport={"width":1024,"height":768})
        viewer.goto(base+"/public")
        viewer.get_by_label("Code de compétition").fill(c["code"])
        viewer.get_by_role("button",name="Voir les résultats").click()
        viewer.get_by_role("heading",name="Coupe de test").wait_for()
        assert "2000-04-12" not in viewer.content()
        viewer.get_by_label("Aire à suivre").select_option("aire")
        viewer.get_by_label("Tableau à suivre").select_option(t["id"])
        viewer.reload()
        expect(viewer.get_by_label("Tableau à suivre")).to_have_value(t["id"])
        expect(viewer.locator(f'[data-tree="{t["id"]}"]')).to_be_visible()
        expect(viewer.locator(f'[data-tree="{lt["id"]}"]')).to_be_hidden()
        viewer.screenshot(path="test-results/public-tablet.png",full_page=True)
        wrestler=browser.new_page(viewport={'width':390,'height':844})
        wrestler.on('pageerror',lambda err:errors.append(str(err)))
        wrestler.on('dialog',lambda dialog:dialog.accept())
        wrestler.goto(base+'/login')
        wrestler.get_by_label('Identifiant').fill('assistant2')
        wrestler.get_by_label('Mot de passe',exact=True).fill(TEST_PASSWORD)
        wrestler.get_by_role('button',name='Se connecter').click()
        wrestler.wait_for_url(base+'/')
        wrestler.goto(base+f'/c/{c["id"]}/table/{lt["id"]}')
        wrestler.get_by_role('button',name='Lancer le tableau').click()
        wrestler.get_by_role('button',name='Lancer le dau').click()
        wrestler.get_by_role('button',name='Suspendre le chronomètre').wait_for()
        expect(wrestler.locator('.clock')).not_to_have_class('clock clock-ended')
        validation=wrestler.get_by_role('button',name='Valider les scores du round')
        expect(validation).to_be_disabled()
        wrestler.locator('input[name="a0"]').fill('2')
        expect(validation).to_be_enabled(timeout=10000)
        expect(wrestler.locator('.clock')).to_have_class('clock clock-ended')
        wrestler.screenshot(path='test-results/vat-mobile.png',full_page=True)
        assert wrestler.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
        validation.click()
        wrestler.get_by_role('button',name='Valider le tour / clôturer').wait_for()
        importer=browser.new_page(viewport={'width':1024,'height':768})
        importer.on('pageerror',lambda err:errors.append(str(err)))
        importer.goto(base+'/login')
        importer.get_by_label('Identifiant').fill('club')
        importer.get_by_label('Mot de passe',exact=True).fill(TEST_PASSWORD)
        importer.get_by_role('button',name='Se connecter').click()
        importer.wait_for_url(base+'/')
        importer.goto(base+f'/c/{registrations["id"]}')
        importer.get_by_role('link',name='Importer un fichier Excel').click()
        importer.get_by_label('Fichier Excel').set_input_files({'name':'inscriptions.xlsx','mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','buffer':file_bytes([['Import Navigateur','12/04/2001','F',52,'Premier cap','Oui','','','','','']])})
        importer.get_by_role('button',name='Prévisualiser et vérifier').click()
        importer.get_by_role('button',name='Confirmer les 1 inscriptions').wait_for()
        importer.screenshot(path='test-results/import-preview.png',full_page=True)
        importer.get_by_role('button',name='Confirmer les 1 inscriptions').click()
        importer.get_by_role('heading',name='1 inscription envoyée').wait_for()
        assert not errors,errors
        browser.close()
    server.shutdown()
print("Parcours navigateur desktop/mobile/tablette validé.")

