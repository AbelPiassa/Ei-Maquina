"""Servidor 127.0.0.1 da Ei, Máquina!. Execute: python3 main.py"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from storage import Store
from local_ai import LocalAI, AIUnavailable

STATIC = Path(__file__).resolve().parent / 'static'
DEFAULT_DATA = Path.home() / '.local' / 'share' / 'ei-maquina'


def create_handler(store: Store, ai: LocalAI | None = None):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'EiMaquina/0.2'

        def log_message(self, format, *args):
            print('[Ei, Máquina!] ' + format % args)

        def _headers(self, status=200, content_type='application/json; charset=utf-8', length=None, extra=None):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            if length is not None:
                self.send_header('Content-Length', str(length))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()

        def send_json(self, payload, status=200):
            raw = json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8')
            self._headers(status, length=len(raw))
            self.wfile.write(raw)

        def fail(self, err):
            status = 404 if isinstance(err, FileNotFoundError) else (400 if isinstance(err, (ValueError, KeyError, json.JSONDecodeError)) else 500)
            self.send_json({'error': str(err) if status != 500 else 'Ocorreu um erro interno.'}, status)
            if status == 500:
                import traceback
                traceback.print_exc()

        def same_origin(self):
            # Não permita páginas de outros sites dispararem operações sobre o servidor local.
            host = self.headers.get('Host', '')
            if not re.fullmatch(r'(localhost|127\.0\.0\.1):\d+', host):
                return False
            origin = self.headers.get('Origin')
            if origin and origin != f'http://{host}':
                return False
            fetch_site = self.headers.get('Sec-Fetch-Site')
            if fetch_site and fetch_site not in {'none', 'same-origin'}:
                return False
            return True

        def body(self, max_size=1024*1024):
            n = int(self.headers.get('Content-Length', '0'))
            if n < 0 or n > max_size:
                raise ValueError('Arquivo ou solicitação muito grande.')
            return self.rfile.read(n)

        def json_body(self):
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Envie dados em JSON.')
            result = json.loads(self.body().decode('utf-8'))
            if not isinstance(result, dict):
                raise ValueError('Os dados devem ser um objeto.')
            return result

        def do_GET(self):
            if not self.same_origin():
                self.send_json({'error': 'Origem da solicitação não permitida.'}, 403)
                return
            try:
                parsed = urlparse(self.path)
                path = parsed.path
                if path == '/api/health':
                    self.send_json({'ok': True, 'app': 'Ei, Máquina!', 'version': '0.2.0'})
                    return
                if path == '/api/state':
                    self.send_json(store.snapshot())
                    return
                if path == '/api/ai/status':
                    self.send_json(ai.status() if ai else {'configured': False, 'running': False, 'mode': 'basic', 'message': 'IA não configurada.'})
                    return
                if path == '/api/timer':
                    self.send_json(store.timer_state())
                    return
                if path == '/api/backup':
                    content = store.backup_zip()
                    filename = 'ei-maquina-backup-' + datetime.now().strftime('%Y-%m-%d_%H-%M') + '.zip'
                    self._headers(200, 'application/zip', len(content), {'Content-Disposition': f'attachment; filename="{filename}"'})
                    self.wfile.write(content)
                    return
                if path.startswith('/media/'):
                    filename = path.split('/')[-1]
                    if not re.fullmatch(r'[0-9a-f]{32}\.(png|jpg|webp|gif)', filename):
                        raise FileNotFoundError('Imagem não encontrada')
                    target = store.media_dir / filename
                    if not target.is_file():
                        raise FileNotFoundError('Imagem não encontrada')
                    content = target.read_bytes()
                    self._headers(200, mimetypes.guess_type(filename)[0] or 'application/octet-stream', len(content))
                    self.wfile.write(content)
                    return
                filemap = {'/':'index.html','/index.html':'index.html','/app.js':'app.js','/styles.css':'styles.css'}
                filename = filemap.get(path)
                if filename:
                    target = STATIC / filename
                    payload = target.read_bytes()
                    self._headers(200, mimetypes.guess_type(target.name)[0] or 'text/html', len(payload))
                    self.wfile.write(payload)
                    return
                raise FileNotFoundError('Página não encontrada')
            except (ConnectionResetError, BrokenPipeError):
                pass
            except Exception as e:
                self.fail(e)

        def route_write(self, verb):
            if not self.same_origin():
                self.send_json({'error': 'Origem da solicitação não permitida.'}, 403)
                return
            path = urlparse(self.path).path
            try:
                if path == '/api/images' and verb == 'POST':
                    img = self.body(max_size=8*1024*1024)
                    url = store.save_image(img, self.headers.get('Content-Type', '').split(';')[0])
                    self.send_json({'url': url}, 201)
                    return
                if path == '/api/restore' and verb == 'POST':
                    raw = self.body(max_size=80*1024*1024)
                    store.restore_zip(raw)
                    self.send_json({'ok': True})
                    return
                data = self.json_body()
                if path == '/api/settings' and verb in {'POST', 'PATCH'}:
                    store.update_settings(data)
                    self.send_json({'ok': True})
                    return
                if path == '/api/commands' and verb == 'POST':
                    self.send_json(assistant_command(data.get('text', ''), store, ai))
                    return
                if path.startswith('/api/timer/') and verb == 'POST':
                    self.send_json(store.timer_command(path.rsplit('/',1)[-1], data.get('course_id')))
                    return
                for endpoint, method in {
                    'courses': store.create_course,
                    'lessons': store.create_lesson,
                    'folders': store.create_folder,
                    'notes': store.upsert_note,
                    'history': store.upsert_history,
                    'priorities': store.upsert_priority,
                    'events': store.upsert_event,
                }.items():
                    if path == '/api/'+endpoint and verb == 'POST':
                        ident = method(data)
                        self.send_json({'id':ident},201)
                        return
                found=re.fullmatch(r'/api/(courses|lessons|folders|notes|history|priorities|events)/(\d+)',path)
                if found:
                    kind,ident = found.group(1),int(found.group(2))
                    if verb == 'DELETE':
                        store.delete(kind,ident)
                        self.send_json({'ok':True})
                        return
                    if verb == 'PATCH':
                        updaters={
                            'courses': lambda: store.update_course(ident,data),
                            'lessons': lambda: store.update_lesson(ident,data),
                            'notes': lambda: store.upsert_note(data,ident),
                            'history': lambda: store.upsert_history(data,ident),
                            'priorities': lambda: store.upsert_priority(data,ident),
                            'events': lambda: store.upsert_event(data,ident),
                        }
                        if kind in updaters:
                            updaters[kind]()
                            self.send_json({'ok':True})
                            return
                raise FileNotFoundError('Comando não encontrado')
            except Exception as e:
                self.fail(e)

        def do_POST(self):self.route_write('POST')
        def do_PATCH(self):self.route_write('PATCH')
        def do_DELETE(self):self.route_write('DELETE')

    return Handler


def _normalize(text: str) -> str:
    import unicodedata
    return ''.join(x for x in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(x) != 'Mn')


def parse_command(text: str, state: dict) -> dict:
    """Comandos de navegação e consultas locais que não precisam carregar IA."""
    raw = str(text or '').strip()
    if not raw or len(raw) > 600:
        raise ValueError('Digite um comando de até 600 caracteres.')
    norm = _normalize(raw)
    for keys, page in [
        (('anotac', 'nota'), 'notes'), (('historico', 'o que estudei'), 'history'),
        (('calendario', 'agenda'), 'agenda'), (('prioridade', 'tarefa'), 'priorities'),
        (('cronometro', 'temporizador'), 'timer'), (('configurac', 'preferencias'), 'settings'),
        (('backup', 'copia de seguranca'), 'backup'), (('curso', 'aula'), 'courses')
    ]:
        if any(x in norm for x in keys) and any(w in norm for w in ('abrir', 'abre', 'mostra', 'mostrar', 'ir para', 'ver', 'acessar')):
            return {'message': 'Abrindo a seção solicitada.', 'navigate': page, 'mode': 'local', 'handled': True}
    if any(t in norm for t in ('o que tenho hoje', 'quais minhas prioridades', 'como estao meus estudos', 'meu resumo de estudos')):
        pending = sum(not x['done'] for x in state['priorities'])
        active = sum(c['status'] == 'active' for c in state['courses'])
        return {'message': f'Você tem {active} curso(s) em andamento e {pending} prioridade(s) pendente(s).',
                'navigate': None, 'mode': 'local', 'handled': True}
    if 'onde parei' in norm or 'qual foi minha ultima aula' in norm:
        matches = [c for c in state['courses'] if _normalize(c['name']) in norm]
        if len(matches) == 1:
            c = matches[0]
            lesson = c['current_lesson'] or 'a última aula ainda não foi registrada'
            return {'message': f"No curso {c['name']}, {lesson}.", 'navigate': None, 'mode': 'local', 'handled': True}
    if norm.startswith('o que estudei') or norm.startswith('qual foi meu ultimo estudo'):
        recent = state['history'][:3]
        msg = ('Últimos registros: ' + '; '.join(f"{h['course_name']} — {h['lesson']}: {h['subject']}" for h in recent)) if recent else 'Você ainda não registrou estudos no histórico.'
        return {'message': msg, 'navigate': None, 'mode': 'local', 'handled': True}
    return {'message': 'Posso consultar seus estudos, abrir seções e responder perguntas com a IA local quando instalada.',
            'navigate': None, 'mode': 'basic', 'handled': False}


def assistant_command(text: str, store: Store, ai: LocalAI | None) -> dict:
    """Só operações explícitas e validadas acessam gravação; modelo é somente leitura."""
    raw = str(text or '').strip()
    if not 1 <= len(raw) <= 600:
        raise ValueError('Digite um comando de até 600 caracteres.')
    norm = _normalize(raw)
    for prefix in ('adicionar prioridade:', 'criar prioridade:', 'adicionar tarefa:'):
        if norm.startswith(prefix):
            value = raw[len(prefix):].strip()
            if not value or len(value) > 200:
                raise ValueError('Informe a prioridade, com até 200 caracteres.')
            store.upsert_priority({'title': value})
            return {'message': f'Prioridade adicionada: {value}', 'navigate': 'priorities',
                    'mode': 'local', 'changed': True}
    state = store.snapshot()
    result = parse_command(raw, state)
    if result.get('handled'):
        return result
    if ai is None or not ai.status().get('configured'):
        return {**result, 'message': result['message'] + ' Para ativar a IA, execute ./configurar_ia_local.sh.'}
    try:
        answer = ai.generate(raw, state)
        return {'message': answer, 'navigate': None, 'mode': 'ai', 'changed': False}
    except AIUnavailable as exc:
        return {'message': f'{exc} O organizador continua funcionando normalmente.',
                'navigate': None, 'mode': 'basic', 'changed': False}


def main():
    ap=argparse.ArgumentParser(description='Ei, Máquina! — organizador local de estudos')
    ap.add_argument('--port',type=int,default=8765)
    ap.add_argument('--no-browser',action='store_true',help='Não abrir o navegador automaticamente')
    ap.add_argument('--data-dir',default=str(DEFAULT_DATA),help='Pasta local dos dados')
    args=ap.parse_args()
    if not 1024<=args.port<=65535:ap.error('Escolha uma porta entre 1024 e 65535')
    store=Store(args.data_dir)
    ai=LocalAI(store.root)
    url=f'http://127.0.0.1:{args.port}/'
    httpd=ThreadingHTTPServer(('127.0.0.1',args.port),create_handler(store, ai))
    print('\nEi, Máquina! — Etapa 2 (IA local opcional)\n'+'='*40)
    print('Interface: '+url)
    print('Dados: '+str(store.root))
    print('Apenas acessível neste computador (127.0.0.1).')
    print('Para encerrar: Ctrl+C\n')
    if not args.no_browser:
        threading.Timer(.8,lambda:webbrowser.open(url)).start()
    try:httpd.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:print('\nEncerrando a Ei, Máquina!')
    finally:
        httpd.server_close()
        ai.shutdown()


if __name__=='__main__':main()
