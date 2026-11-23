import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
from main import create_handler
from storage import Store


@pytest.fixture
def server(tmp_path):
    db=Store(tmp_path/'app')
    http=ThreadingHTTPServer(('127.0.0.1',0),create_handler(db))
    thread=threading.Thread(target=http.serve_forever,daemon=True)
    thread.start()
    yield 'http://127.0.0.1:'+str(http.server_port),db
    http.shutdown();http.server_close();thread.join(timeout=3)


def request(base,path,method='GET',payload=None,headers=None):
    req=urllib.request.Request(base+path,method=method,headers=headers or {})
    if payload is not None:
        req.add_header('Content-Type','application/json')
        req.data=json.dumps(payload).encode()
    with urllib.request.urlopen(req,timeout=5) as resp:
        return json.load(resp)


def test_server_crud_and_local_pages(server):
    base,db=server
    assert request(base,'/api/health')['ok']
    c=request(base,'/api/courses','POST',{'name':'Curso Linux','mode':'simple','progress':42})['id']
    assert request(base,'/api/state')['courses'][0]['progress']==42
    request(base,f'/api/courses/{c}','PATCH',{'status':'paused'})
    assert request(base,'/api/state')['courses'][0]['status']=='paused'
    with urllib.request.urlopen(base+'/') as resp:
        assert b'<!doctype html>' in resp.read()


def test_reject_cross_origin_request(server):
    base,db=server
    with pytest.raises(urllib.error.HTTPError) as exc:
        request(base,'/api/courses','POST',{'name':'injetado'},{'Origin':'https://site-malicioso.example'})
    assert exc.value.code==403
    assert request(base,'/api/state')['courses']==[]


def test_local_commands(server):
    base,_=server
    assert request(base,'/api/commands','POST',{'text':'Abre minhas anotações'})['navigate']=='notes'
    assert 'curso' in request(base,'/api/commands','POST',{'text':'O que tenho hoje?'})['message']
