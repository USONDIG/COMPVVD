"""Recette navigateur des quatre nouvelles disciplines et de leurs vues publiques."""
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
from app import disciplines as x
from tests.test_web import seed,TEST_PASSWORD
from tests.test_disciplines import teams

with tempfile.TemporaryDirectory() as tmp:
    app=create_app(dict(DATABASE=str(Path(tmp)/'browser.sqlite3'),SECRET_KEY='test',SESSION_COOKIE_SECURE=False))
    c=seed(app);c['open']=[]
    for p in c['people']:p['disciplines']=['Quyen','Quyen Arme']
    for discipline in ('Quyen','Quyen Arme'):
        d.generate(c,discipline);t=c['tables'][-1];t.update(area='aire',judges=['0','1','2']);d.draw(c,t)
    quyen,arme=c['tables']
    for discipline,sizes in (('Quyen synchro',(2,2)),('Dau équipe',(3,3))):
        fixture=teams(sizes,discipline)
        prefix='sync-' if discipline=='Quyen synchro' else 'team-'
        for p in fixture['people']:p.update(id=prefix+p['id'],name=prefix+p['name'],club='club-a')
        for team in fixture['teams']:team['members']=[prefix+pid for pid in team['members']]
        c['people']+=fixture['people'];c['teams']+=fixture['teams']
        d.generate(c,discipline);t=c['tables'][-1];t.update(area='aire',judges=['0','1','2'],referee='3' if discipline=='Dau équipe' else None,rounds=1,seconds=2,rest=0);d.draw(c,t)
    synchro,pool=c['tables'][-2:]
    with closing(connect(app.config['DATABASE'])) as db:
        db.execute('UPDATE competitions SET state=? WHERE id=?',(json.dumps(c),c['id']));db.commit()
    server=make_server('127.0.0.1',0,app,threaded=True)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    Path('test-results').mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda err:errors.append(str(err)));page.on('dialog',lambda dialog:dialog.accept())
        page.goto(base+'/login');page.get_by_label('Identifiant').fill('organizer');page.get_by_label('Mot de passe',exact=True).fill(TEST_PASSWORD);page.get_by_role('button',name='Se connecter').click();page.wait_for_url(base+'/')
        page.goto(base+'/c/'+c['id']);page.get_by_role('heading',name='Équipes',exact=True).wait_for()
        page.screenshot(path='test-results/equipes-mobile.png',full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
        for table in (quyen,arme,synchro):
            page.goto(base+f'/c/{c["id"]}/table/{table["id"]}')
            page.get_by_role('button',name='Lancer le tableau').click()
            for tour in range(2):
                for i in range(2):
                    page.get_by_role('button',name='Lancer le passage',exact=True).first.click()
                    inputs=page.locator('form:has(input[value="quyen_score"]) input[name="notes"]')
                    for j in range(3):inputs.nth(j).fill(str(8+i*.5))
                    if table is quyen and tour==0 and i==0:
                        page.screenshot(path='test-results/quyen-mobile.png',full_page=True)
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
                    page.get_by_role('button',name='Valider les trois notes',exact=True).click()
                with page.expect_navigation():
                    page.get_by_role('button',name='Valider le tour / calculer la suite',exact=True).click()
            page.wait_for_function("document.querySelector('input[value=quyen_start]') || [...document.querySelectorAll('h3')].some(x=>x.textContent==='Classement final')")
            # First-round draw order can differ from second-round order, creating a tie.
            for _ in range(2):
                if page.get_by_role('heading',name='Classement final',exact=True).count():break
                for i in range(2):
                    page.get_by_role('button',name='Lancer le passage',exact=True).first.click()
                    for field in page.locator('form:has(input[value="quyen_score"]) input[name="notes"]').all():field.fill(str(7+i))
                    page.get_by_role('button',name='Valider les trois notes',exact=True).click()
                with page.expect_navigation():
                    page.get_by_role('button',name='Valider le tour / calculer la suite',exact=True).click()
            page.get_by_role('heading',name='Classement final',exact=True).wait_for()
        page.goto(base+f'/c/{c["id"]}/table/{pool["id"]}')
        page.get_by_role('button',name='Lancer le tableau').click();page.get_by_role('button',name='Lancer la rencontre',exact=True).click()
        for _ in range(3):
            page.get_by_role('button',name='Lancer le dau',exact=True).click()
            page.locator('input[name="a0"]').fill('2')
            validation=page.get_by_role('button',name='Valider les six scores',exact=True)
            expect(validation).to_be_enabled(timeout=10000);validation.click()
        page.get_by_role('button',name='Valider la rencontre',exact=True).click()
        page.get_by_text('Classement définitif',exact=False).wait_for()
        page.screenshot(path='test-results/dau-equipe-mobile.png',full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
        viewer=browser.new_page(viewport={'width':1280,'height':900});viewer.on('pageerror',lambda err:errors.append(str(err)))
        viewer.goto(base+'/public');viewer.get_by_label('Code de compétition').fill(c['code']);viewer.get_by_role('button',name='Voir les résultats').click()
        viewer.get_by_role('heading',name='Coupe de test',exact=True).wait_for()
        viewer.get_by_label('Tableau à suivre').select_option(pool['id']);expect(viewer.locator('#poule-'+pool['id'])).to_be_visible()
        viewer.screenshot(path='test-results/poule-public.png',full_page=True)
        viewer.get_by_label('Tableau à suivre').select_option(quyen['id']);expect(viewer.locator('#resultats-'+quyen['id'])).to_be_visible();expect(viewer.locator('#poule-'+pool['id'])).to_be_hidden()
        viewer.screenshot(path='test-results/quyen-public.png',full_page=True)
        assert '2000-04-12' not in viewer.content()
        assert not errors,errors
        browser.close()
    server.shutdown()
print('Quyen, Quyen Arme, Quyen synchro, Dau équipe et suivi public validés dans Chromium.')
