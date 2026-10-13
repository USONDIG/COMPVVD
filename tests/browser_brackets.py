"""Verify public updates without reload, SVG trees and printable vector PDFs."""
from contextlib import closing
from io import BytesIO
import json
from pathlib import Path
import sys,tempfile,threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright,expect
from pypdf import PdfReader
from werkzeug.serving import make_server
from app.web import create_app,connect
from app import domain as d
from tests.test_web import seed

with tempfile.TemporaryDirectory() as tmp:
    app=create_app(dict(DATABASE=str(Path(tmp)/'browser.sqlite3'),SECRET_KEY='test',SESSION_COOKIE_SECURE=False))
    c=seed(app);c['open']=[]
    original=c['people'][0]
    c['people']=[dict(original,id=f'p{i}',name=f'Concurrent {i}',club='club-a' if i%2 else 'club-b') for i in range(8)]
    d.generate(c);t=c['tables'][0];t.update(area='aire',judges=['0','1','2'],referee='3');d.draw(c,t);d.start_table(c,t)
    c['people'] += [dict(p,id='v'+p['id'],disciplines=['Vat']) for p in list(c['people'])]
    d.generate(c,'Vat');vt=c['tables'][-1];vt.update(area='aire',judges=[],referee='3');d.draw(c,vt)
    def save():
        with closing(connect(app.config['DATABASE'])) as db:
            db.execute('UPDATE competitions SET state=?,revision=revision+1 WHERE id=?',(json.dumps(c),c['id']));db.commit()
    save()
    server=make_server('127.0.0.1',0,app,threaded=True);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';Path('test-results').mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base+'/public');page.get_by_label('Code de compétition').fill(c['code']);page.get_by_role('button',name='Voir les résultats').click()
        page.get_by_label('Tableau à suivre').select_option(t['id']);page.get_by_label('Tableau à suivre').focus()
        tree=page.locator(f'[data-tree="{t["id"]}"]')
        expect(tree.locator('[data-bout]')).to_have_count(8)
        expect(page.locator(f'[data-tree="{vt["id"]}"]')).to_be_hidden()
        page.evaluate('window.samePublicDocument = true')
        m=t['matches'][0];m.update(sa=9,sb=2);d.finish(m,m['a'],'points');save()
        expect(tree.locator('.diagram-winner')).to_have_count(1,timeout=12000)
        assert page.evaluate('window.samePublicDocument === true')
        expect(page.get_by_label('Tableau à suivre')).to_have_value(t['id'])
        expect(page.locator('#connection')).to_contain_text('À jour')
        page.screenshot(path='test-results/arbre-public-desktop.png',full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
        tree.locator('xpath=..').evaluate('(el)=>{el.scrollLeft=150}')
        page.screenshot(path='test-results/arbre-public-mobile.png',full_page=True)
        print_page=page.context.new_page()
        print_page.set_viewport_size({'width':1400,'height':1000})
        for table in (t,vt):
            print_page.goto(base+f'/public/print?kind=tree&table={table["id"]}')
            expect(print_page.locator('svg')).to_be_visible()
            pdf=print_page.pdf(prefer_css_page_size=True,print_background=True,path=f'test-results/arbre-{table["discipline"]}.pdf')
            reader=PdfReader(BytesIO(pdf));assert len(reader.pages)==1,len(reader.pages)
            assert 'Finale' in reader.pages[0].extract_text()
            assert 'Concurrent' in reader.pages[0].extract_text()
        print_page.goto(base+f'/public/print?kind=tree&table={t["id"]}&paper=a3')
        pdf=print_page.pdf(prefer_css_page_size=True,print_background=True,path='test-results/arbre-a3.pdf')
        assert len(PdfReader(BytesIO(pdf)).pages)==1
        print_page.goto(base+'/public/print?kind=rankings')
        pdf=print_page.pdf(prefer_css_page_size=True,print_background=True,path='test-results/classements.pdf')
        assert 'Clubs' in ''.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        assert not errors,errors
        browser.close()
    server.shutdown()
print('Arbres Dau/Vat, actualisation publique sans rechargement et impressions PDF validés.')
