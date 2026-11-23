import json
from pathlib import Path

import pytest
from main import assistant_command, create_handler
from local_ai import AIUnavailable, LocalAI, compact_study_context
from storage import Store


def test_context_only_studies_no_html_or_image(tmp_path):
    store=Store(tmp_path)
    cid=store.create_course({'name':'Python'})
    store.upsert_note({'title':'Nota sobre funções','course_id':cid,'content_html':'<p>CHAVE_SECRETA_EXEMPLO</p><img src="/media/abc.png">'})
    store.upsert_history({'course_id':cid,'lesson':'Aula 1','subject':'Funções em Python'})
    content=compact_study_context(store.snapshot())
    data=json.loads(content)
    assert 'CHAVE_SECRETA_EXEMPLO' not in content
    assert '<img' not in content
    assert data['titulos_de_anotacoes'][0]['titulo']=='Nota sobre funções'


def test_local_ai_absent_does_not_break_commands(tmp_path):
    store=Store(tmp_path)
    engine=LocalAI(tmp_path)
    try:
        assert not engine.status()['configured']
        r=assistant_command('Abre minhas anotações',store,engine)
        assert r['navigate']=='notes' and r['mode']=='local'
        r=assistant_command('Explique o que é uma função',store,engine)
        assert r['mode']=='basic' and 'configurar_ia_local' in r['message']
    finally:
        engine.shutdown()


def test_explicit_priority_command_no_model(tmp_path):
    store=Store(tmp_path)
    r=assistant_command('Adicionar prioridade: Revisar aula 12',store,None)
    assert r['changed'] and r['navigate']=='priorities'
    assert store.snapshot()['priorities'][0]['title']=='Revisar aula 12'
    with pytest.raises(ValueError):
        assistant_command('Criar prioridade: ',store,None)


def test_ai_mocked_read_only_and_no_fake_confirmation(tmp_path, monkeypatch):
    store=Store(tmp_path)
    cid=store.create_course({'name':'Pentest Web','current_lesson':'Aula 05'})
    engine=LocalAI(tmp_path)
    binary=tmp_path/'llama-server';binary.write_text('script');binary.chmod(0o755)
    model=tmp_path/'modelo.gguf';model.write_bytes(b'modelo')
    engine.config_path.write_text(json.dumps({'llama_server':str(binary),'model':str(model)}))
    def fake_start():
        return None
    def fake_call(path,data=None,timeout=0):
        assert path=='/v1/chat/completions'
        content=data['messages'][0]['content']
        assert 'Pentest Web' in content and 'Aula 05' in content
        return {'choices':[{'message':{'content':'Você está na aula 5 de Pentest Web.'}}]}
    monkeypatch.setattr(engine,'_start',fake_start)
    monkeypatch.setattr(engine,'_call',fake_call)
    try:
        r=assistant_command('Qual é a próxima atividade de segurança?',store,engine)
        assert r['mode']=='ai' and r['changed'] is False
        assert 'Pentest Web' in r['message']
        assert len(store.snapshot()['history'])==0
    finally:
        engine.shutdown()


def test_conflict_port_refuses_untrusted_process(tmp_path, monkeypatch):
    engine=LocalAI(tmp_path)
    binary=tmp_path/'llama-server';binary.write_text('abc');binary.chmod(0o755)
    model=tmp_path/'local.gguf';model.write_bytes(b'123')
    engine.config_path.write_text(json.dumps({'llama_server':str(binary),'model':str(model),'port':18765}))
    monkeypatch.setattr(engine,'_port_in_use',lambda port: True)
    try:
        with pytest.raises(AIUnavailable,match='ocupada'):
            engine._start()
    finally:
        engine.shutdown()


def test_llama_http_lifecycle_with_mock_engine(tmp_path):
    """Teste do protocolo e subprocesso com engine falsa (sem afirmar inferência real)."""
    import socket
    from textwrap import dedent

    sock=socket.socket()
    sock.bind(('127.0.0.1',0))
    port=sock.getsockname()[1]
    sock.close()
    binary=tmp_path/'llama-server'
    binary.write_text(dedent('''\
        #!/usr/bin/env python3
        import json, sys
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        port=int(sys.argv[sys.argv.index('--port')+1])
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                payload=b'{"status":"ok"}'
                self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
            def do_POST(self):
                size=int(self.headers.get('Content-Length','0'))
                req=json.loads(self.rfile.read(size))
                assert req['model']=='ei-maquina-local'
                answer={'choices':[{'message':{'content':'Resposta de teste da IA local.'}}]}
                payload=json.dumps(answer).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
            def log_message(self,*args):pass
        ThreadingHTTPServer(('127.0.0.1',port),H).serve_forever()
    '''))
    binary.chmod(0o755)
    model=tmp_path/'modelo.gguf'
    model.write_bytes(b'teste')
    manager=LocalAI(tmp_path)
    manager.config_path.write_text(json.dumps({'llama_server':str(binary),'model':str(model),'port':port}))
    try:
        result=manager.generate('Qual aula eu estudei?',Store(tmp_path).snapshot())
        assert 'Resposta de teste' in result
        assert manager.status()['running']
    finally:
        manager.shutdown()
    assert not manager.status()['running']
