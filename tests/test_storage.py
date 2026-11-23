import io
import json
from pathlib import Path

import pytest

from storage import Store, sanitize_note


@pytest.fixture
def db(tmp_path):
    return Store(tmp_path / 'db')


def test_save_course_simple_and_detailed(db):
    c = db.create_course({'name':'Python', 'mode':'simple','progress':35,'status':'active'})
    assert db.snapshot()['courses'][0]['progress'] == 35
    db.update_course(c, {'mode':'detailed'})
    l1 = db.create_lesson({'course_id':c,'title':'Aula 1','position':1})
    db.create_lesson({'course_id':c,'title':'Aula 2','position':2})
    db.update_lesson(l1, {'completed':True})
    assert db.snapshot()['courses'][0]['progress'] == 50
    db.update_course(c, {'mode':'simple'})
    assert db.snapshot()['courses'][0]['progress'] == 35  # Sem perder o valor manual
    assert len(db.snapshot()['courses'][0]['lessons']) == 2


def test_history_links_note_both_creation_orders(db):
    c=db.create_course({'name':'Pentest Web'})
    n=db.upsert_note({'course_id':c,'lesson':'Aula 05','title':'HTTP','content_html':'<b>GET</b> &amp; POST'})
    h=db.upsert_history({'course_id':c,'lesson':'Aula 05','subject':'HTTP','description':'Pratiquei GET e POST'})
    assert db.snapshot()['history'][0]['note_ids']==[n]
    h2=db.upsert_history({'course_id':c,'lesson':'Aula 06','subject':'Headers'})
    n2=db.upsert_note({'course_id':c,'lesson':'Aula 06','title':'Cabeçalhos','content_html':'<p>Content-Type</p>'})
    rows={x['id']:x for x in db.snapshot()['history']}
    assert rows[h2]['note_ids']==[n2]
    db.upsert_history({'course_id':c,'lesson':'Aula 06','subject':'Headers','note_ids':[n,n2]},h2)
    assert set(next(x for x in db.snapshot()['history'] if x['id']==h2)['note_ids'])=={n,n2}


def test_html_sanitizer_rejects_scripts_and_remote_images():
    s=sanitize_note('<b>Seguro</b><script>alert(1)</script><img src="https://evil.test/x" onerror="alert(2)"><div onclick="bad()">Oi</div>')
    assert '<script' not in s and 'alert(' not in s and '<img' not in s and 'onclick' not in s
    assert '<b>Seguro</b>' in s and 'Oi' in s
    assert '<img src="/media/' in sanitize_note('<img src="/media/'+('a'*32)+'.png">')


def test_backup_restore_roundtrip(db,tmp_path):
    course=db.create_course({'name':'React Native'})
    db.upsert_note({'course_id':course,'title':'Hooks','content_html':'<p>useState</p>'})
    db.upsert_priority({'title':'Revisar', 'course_id':course})
    db.upsert_event({'title':'Estudar', 'event_date':'2026-11-22','course_id':course})
    db.update_settings({'theme':'dark'})
    archive=db.backup_zip()
    new=Store(tmp_path/'restored')
    new.restore_zip(archive)
    snapshot=new.snapshot()
    assert snapshot['courses'][0]['name']=='React Native'
    assert snapshot['notes'][0]['title']=='Hooks'
    assert snapshot['settings']['theme']=='dark'
    assert snapshot['events'][0]['event_date']=='2026-11-22'
    with pytest.raises(ValueError):new.restore_zip(b'not a zip')


def test_timer_not_saved_to_history(db):
    db.timer_command('start')
    db.timer_command('pause')
    assert db.snapshot()['history']==[]
    db.timer_command('stop')
    assert db.timer_state()['elapsed']==0


def test_validations(db):
    with pytest.raises(ValueError):db.create_course({'name':''})
    with pytest.raises(ValueError):db.create_course({'name':'x','url':'file:///etc/passwd'})
    with pytest.raises(ValueError):db.upsert_event({'title':'x','event_date':'2026-02-30'})
    with pytest.raises(ValueError):db.upsert_note({'title':'x','course_id':999})


def test_local_image_inside_note_and_backup(db,tmp_path):
    # PNG mínimo 1x1 criado sem dependências externas.
    import base64
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/gXsAAAAASUVORK5CYII=')
    path=db.save_image(png,'image/png')
    assert path.startswith('/media/')
    note_id=db.upsert_note({'title':'Print da aula','content_html':f'<p>Exemplo</p><img src="{path}" alt="Print">'})
    assert path in db.snapshot()['notes'][0]['content_html']
    new=Store(tmp_path/'restored_images')
    new.restore_zip(db.backup_zip())
    assert (new.media_dir/path.rsplit('/',1)[-1]).read_bytes()==png
    assert new.snapshot()['notes'][0]['id']==note_id
