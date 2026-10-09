"""Parcours réel Chromium desktop/mobile et captures de contrôle en CI."""
from contextlib import closing
import json
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from app.web import create_app,connect
from app import domain as d
from tests.test_web import seed,TEST_PASSWORD

with tempfile.TemporaryDirectory() as tmp:
    app=create_app(dict(DATABASE=str(Path(tmp)/"browser.sqlite3"),SECRET_KEY="browser-test",SESSION_COOKIE_SECURE=False))
    c=seed(app)
    c["open"]=[]
    d.generate(c)
    t=c["tables"][0]
    t.update(area="aire",judges=["0","1","2"],referee="3")
    d.draw(c,t)
    with closing(connect(app.config["DATABASE"])) as db:
        db.execute("UPDATE competitions SET state=? WHERE id=?",(json.dumps(c),c["id"]))
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
        page.get_by_role("button",name="Lancer le combat").wait_for()
        page.get_by_role("button",name="Lancer le combat").click()
        page.get_by_role("button",name="Suspendre le chronomètre").wait_for()
        assert page.locator('input[name="a0"]').count()==1
        page.locator('input[name="a0"]').fill("4")
        page.get_by_role("button",name="Valider les six scores").click()
        page.locator("#notice.show").wait_for()
        assert page.locator('input[name="a0"]').input_value()=="4"
        page.screenshot(path="test-results/table-desktop.png",full_page=True)
        page.set_viewport_size({"width":390,"height":844})
        page.screenshot(path="test-results/table-mobile.png",full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
        viewer=browser.new_page(viewport={"width":1024,"height":768})
        viewer.goto(base+"/public")
        viewer.get_by_label("Code de compétition").fill(c["code"])
        viewer.get_by_role("button",name="Voir les résultats").click()
        viewer.get_by_role("heading",name="Coupe de test").wait_for()
        assert "2000-04-12" not in viewer.content()
        viewer.screenshot(path="test-results/public-tablet.png",full_page=True)
        assert not errors,errors
        browser.close()
    server.shutdown()
print("Parcours navigateur desktop/mobile/tablette validé.")
