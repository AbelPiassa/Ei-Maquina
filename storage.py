"""Persistência local da Ei, Máquina! (somente biblioteca padrão)."""
from __future__ import annotations

import html
import io
import json
import re
import sqlite3
import tempfile
import threading
import time
import uuid
import zipfile
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

ALLOWED_STATUSES = {"active", "paused", "completed"}
ALLOWED_MODES = {"simple", "detailed"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_BACKUP_BYTES = 80 * 1024 * 1024


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def valid_date(value: str | None) -> str | None:
    if not value:
        return None
    date.fromisoformat(value)
    return value


def number(value, default=0, low=0, high=100) -> int:
    try:
        return min(high, max(low, int(value)))
    except (ValueError, TypeError):
        return default


def required(value, field: str, max_length: int = 200) -> str:
    value = str(value or "").strip()
    if not value:
        raise ValueError(f"Preencha o campo {field}.")
    if len(value) > max_length:
        raise ValueError(f"O campo {field} ultrapassa {max_length} caracteres.")
    return value


def safe_optional(value, length=300) -> str:
    return str(value or "").strip()[:length]


def safe_url(value) -> str:
    value = safe_optional(value, 1500)
    if value and not re.match(r"^https?://", value, re.I):
        raise ValueError("O link do curso deve começar com https:// ou http://.")
    return value


class SafeNotesHTML(HTMLParser):
    TAGS = {"div", "p", "br", "strong", "b", "em", "i", "u", "s", "strike", "ul", "ol", "li", "pre", "code", "blockquote", "h1", "h2", "h3", "span", "img"}
    SKIP = {"script", "style", "iframe", "object", "svg", "math", "template", "form"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
            return
        if self.skip_depth or tag not in self.TAGS:
            return
        attr = {}
        for k, v in attrs:
            if k == "src" and tag == "img" and v and re.fullmatch(r"/media/[0-9a-f]{32}\.(png|jpg|jpeg|webp|gif)", v):
                attr["src"] = v
            elif k == "alt" and tag == "img":
                attr["alt"] = safe_optional(v, 140)
            elif k == "style" and tag != "img" and v:
                styles = []
                for stmt in v.split(";"):
                    if ":" not in stmt:
                        continue
                    key, val = [x.strip().lower() for x in stmt.split(":", 1)]
                    if key == "text-align" and val in {"left", "center", "right", "justify"}:
                        styles.append(f"text-align:{val}")
                    if key == "color" and re.fullmatch(r"#[0-9a-f]{3,8}", val):
                        styles.append(f"color:{val}")
                if styles:
                    attr["style"] = ";".join(styles)
        if tag == "img" and "src" not in attr:
            return
        attrs_str = "".join(f' {k}="{html.escape(str(v), quote=True)}"' for k, v in attr.items())
        self.parts.append(f"<{tag}{attrs_str}>")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag in self.TAGS - {"img", "br"} and not self.skip_depth:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(html.escape(data))

    def handle_entityref(self, name):
        if not self.skip_depth:
            self.parts.append(f"&{name};")


def sanitize_note(content: str) -> str:
    if len(content) > 200000:
        raise ValueError("Esta anotação é muito extensa (limite: 200 mil caracteres).")
    parser = SafeNotesHTML()
    parser.feed(content)
    return "".join(parser.parts)


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class Store:
    def __init__(self, data_dir: str | Path):
        self.root = Path(data_dir).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.media_dir = self.root / "media"
        self.media_dir.mkdir(exist_ok=True)
        self.db_path = self.root / "estudos.sqlite3"
        self._lock = threading.RLock()
        self._timer = {"running": False, "elapsed": 0.0, "start": None, "course_id": None}
        self.init_schema()

    def connection(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path, timeout=12, factory=ClosingConnection)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("PRAGMA busy_timeout = 12000")
        return c

    def init_schema(self):
        with self._lock, self.connection() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS courses (
              id INTEGER PRIMARY KEY, name TEXT NOT NULL, platform TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '',
              mode TEXT NOT NULL DEFAULT 'simple', status TEXT NOT NULL DEFAULT 'active',
              progress INTEGER NOT NULL DEFAULT 0, current_lesson TEXT NOT NULL DEFAULT '',
              last_study TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lessons (
              id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
              module_name TEXT NOT NULL DEFAULT '', title TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0,
              position INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS folders (
              id INTEGER PRIMARY KEY, name TEXT NOT NULL, parent_id INTEGER REFERENCES folders(id) ON DELETE SET NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notes (
              id INTEGER PRIMARY KEY, title TEXT NOT NULL, content_html TEXT NOT NULL DEFAULT '',
              course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL,
              lesson TEXT NOT NULL DEFAULT '', folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS study_history (
              id INTEGER PRIMARY KEY, course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL,
              course_name TEXT NOT NULL DEFAULT '', lesson TEXT NOT NULL DEFAULT '', subject TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '', studied_on TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS history_notes (
              history_id INTEGER NOT NULL REFERENCES study_history(id) ON DELETE CASCADE,
              note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
              PRIMARY KEY(history_id,note_id)
            );
            CREATE TABLE IF NOT EXISTS priorities (
              id INTEGER PRIMARY KEY, title TEXT NOT NULL, course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL,
              due_on TEXT, done INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS study_events (
              id INTEGER PRIMARY KEY, title TEXT NOT NULL, course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL,
              event_date TEXT NOT NULL, event_time TEXT NOT NULL DEFAULT '', done INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_notes_course_lesson ON notes(course_id,lesson);
            CREATE INDEX IF NOT EXISTS idx_hist_course_lesson ON study_history(course_id,lesson);
            """)

    def _rows(self, c, sql, args=()):
        return [dict(r) for r in c.execute(sql, args).fetchall()]

    def snapshot(self):
        with self._lock, self.connection() as c:
            courses = self._rows(c, "SELECT * FROM courses ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'paused' THEN 1 ELSE 2 END, updated_at DESC, id DESC")
            lessons = self._rows(c, "SELECT * FROM lessons ORDER BY course_id,position,id")
            for course in courses:
                ls = [l for l in lessons if l["course_id"] == course["id"]]
                course["lessons"] = ls
                if course["mode"] == "detailed" and ls:
                    course["progress"] = round(100 * sum(bool(l["completed"]) for l in ls) / len(ls))
            notes = self._rows(c, "SELECT * FROM notes ORDER BY updated_at DESC,id DESC")
            history = self._rows(c, "SELECT * FROM study_history ORDER BY studied_on DESC,id DESC")
            for row in history:
                row["note_ids"] = [x[0] for x in c.execute("SELECT note_id FROM history_notes WHERE history_id=? ORDER BY note_id", (row["id"],))]
            settings = {r["key"]: r["value"] for r in self._rows(c, "SELECT key,value FROM settings")}
            return {"courses": courses, "notes": notes, "folders": self._rows(c, "SELECT * FROM folders ORDER BY name"),
                    "history": history, "priorities": self._rows(c, "SELECT * FROM priorities ORDER BY done, due_on IS NULL,due_on,id DESC"),
                    "events": self._rows(c, "SELECT * FROM study_events ORDER BY event_date,event_time,id"),
                    "settings": settings, "timer": self.timer_state()}

    def _exists(self, c, table, key):
        if key is None or key == "":
            return None
        key = int(key)
        if not c.execute(f"SELECT 1 FROM {table} WHERE id=?", (key,)).fetchone():
            raise ValueError("Registro relacionado não encontrado.")
        return key

    def create_course(self, d):
        name = required(d.get("name"), "nome do curso")
        mode = d.get("mode", "simple")
        status = d.get("status", "active")
        if mode not in ALLOWED_MODES or status not in ALLOWED_STATUSES:
            raise ValueError("Modo ou situação do curso inválido.")
        with self._lock, self.connection() as c:
            cur = c.execute("INSERT INTO courses(name,platform,url,mode,status,progress,current_lesson,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
              (name, safe_optional(d.get("platform")), safe_url(d.get("url")), mode, status, number(d.get("progress")),safe_optional(d.get("current_lesson")),now(),now()))
            return cur.lastrowid

    def update_course(self, ident, d):
        allowed = {"name", "platform", "url", "mode", "status", "progress", "current_lesson"}
        upd = {k: v for k, v in d.items() if k in allowed}
        if "name" in upd: upd["name"] = required(upd["name"], "nome do curso")
        if "url" in upd: upd["url"] = safe_url(upd["url"])
        for k in ("platform", "current_lesson"):
            if k in upd: upd[k] = safe_optional(upd[k])
        if "progress" in upd: upd["progress"] = number(upd["progress"])
        if "mode" in upd and upd["mode"] not in ALLOWED_MODES: raise ValueError("Modo inválido")
        if "status" in upd and upd["status"] not in ALLOWED_STATUSES: raise ValueError("Status inválido")
        if not upd: return
        upd["updated_at"] = now()
        with self._lock, self.connection() as c:
            self._exists(c, "courses", ident)
            c.execute(f"UPDATE courses SET {', '.join(k+'=?' for k in upd)} WHERE id=?", list(upd.values())+[ident])

    def delete(self, kind, ident):
        tables = {"courses": "courses", "notes": "notes", "folders": "folders", "history": "study_history",
                  "priorities": "priorities", "events": "study_events", "lessons": "lessons"}
        if kind not in tables: raise ValueError("Tipo de registro inválido")
        with self._lock, self.connection() as c:
            self._exists(c, tables[kind], ident)
            c.execute(f"DELETE FROM {tables[kind]} WHERE id=?", (ident,))

    def create_lesson(self, d):
        with self._lock, self.connection() as c:
            course_id = self._exists(c, "courses", d.get("course_id"))
            if not course_id: raise ValueError("Escolha um curso")
            cur=c.execute("INSERT INTO lessons(course_id,module_name,title,position) VALUES(?,?,?,?)",
              (course_id,safe_optional(d.get("module_name")),required(d.get("title"),"título da aula"),
               number(d.get("position"),0,0,9999)))
            return cur.lastrowid

    def update_lesson(self, ident, d):
        fields={k:d[k] for k in ("completed","title","module_name","position") if k in d}
        if "completed" in fields: fields["completed"]=int(bool(fields["completed"]))
        if "title" in fields: fields["title"]=required(fields["title"],"aula")
        if "module_name" in fields: fields["module_name"]=safe_optional(fields["module_name"])
        if "position" in fields: fields["position"]=number(fields["position"],0,0,9999)
        if not fields:return
        with self._lock,self.connection() as c:
            self._exists(c,"lessons",ident)
            c.execute(f"UPDATE lessons SET {', '.join(k+'=?' for k in fields)} WHERE id=?",list(fields.values())+[ident])

    def create_folder(self, d):
        with self._lock,self.connection() as c:
            parent=self._exists(c,"folders",d.get("parent_id"))
            cur=c.execute("INSERT INTO folders(name,parent_id,created_at) VALUES(?,?,?)",(required(d.get("name"),"nome da pasta"),parent,now()))
            return cur.lastrowid

    def upsert_note(self, d, ident=None):
        title=required(d.get("title"),"título da anotação")
        body=sanitize_note(str(d.get("content_html") or ""))
        lesson=safe_optional(d.get("lesson"))
        with self._lock,self.connection() as c:
            course=self._exists(c,"courses",d.get("course_id"))
            folder=self._exists(c,"folders",d.get("folder_id"))
            if ident:
                self._exists(c,"notes",ident)
                c.execute("UPDATE notes SET title=?,content_html=?,course_id=?,lesson=?,folder_id=?,updated_at=? WHERE id=?",
                   (title,body,course,lesson,folder,now(),ident))
            else:
                cur=c.execute("INSERT INTO notes(title,content_html,course_id,lesson,folder_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                      (title,body,course,lesson,folder,now(),now()))
                ident=cur.lastrowid
            if course and lesson:
                c.execute("INSERT OR IGNORE INTO history_notes(history_id,note_id) SELECT id,? FROM study_history WHERE course_id=? AND lesson=?",(ident,course,lesson))
            return ident

    def upsert_history(self,d,ident=None):
        subject=required(d.get("subject"),"assunto")
        studied_on=valid_date(d.get("studied_on")) or date.today().isoformat()
        with self._lock,self.connection() as c:
            course=self._exists(c,"courses",d.get("course_id"))
            cname=c.execute("SELECT name FROM courses WHERE id=?",(course,)).fetchone()[0] if course else "Estudo livre"
            lesson=safe_optional(d.get("lesson"))
            description=safe_optional(d.get("description"),3000)
            completed=int(bool(d.get("completed",True)))
            if ident:
                self._exists(c,"study_history",ident)
                c.execute("UPDATE study_history SET course_id=?,course_name=?,lesson=?,subject=?,description=?,studied_on=?,completed=? WHERE id=?",
                  (course,cname,lesson,subject,description,studied_on,completed,ident))
                c.execute("DELETE FROM history_notes WHERE history_id=?",(ident,))
            else:
                cur=c.execute("INSERT INTO study_history(course_id,course_name,lesson,subject,description,studied_on,completed,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (course,cname,lesson,subject,description,studied_on,completed,now()))
                ident=cur.lastrowid
            if course:
                c.execute("UPDATE courses SET last_study=?,current_lesson=?,updated_at=? WHERE id=?",(studied_on,lesson,now(),course))
            if "note_ids" in d:
                for n in d.get("note_ids") or []:
                    note_id=self._exists(c,"notes",n)
                    if note_id:
                        c.execute("INSERT OR IGNORE INTO history_notes(history_id,note_id) VALUES(?,?)",(ident,note_id))
            elif course and lesson:
                c.execute("INSERT OR IGNORE INTO history_notes(history_id,note_id) SELECT ?,id FROM notes WHERE course_id=? AND lesson=?",(ident,course,lesson))
            return ident

    def upsert_priority(self,d,ident=None):
        title=required(d.get("title"),"prioridade")
        due=valid_date(d.get("due_on"))
        with self._lock,self.connection() as c:
            course=self._exists(c,"courses",d.get("course_id"))
            done=int(bool(d.get("done",False)))
            if ident:
                self._exists(c,"priorities",ident)
                c.execute("UPDATE priorities SET title=?,course_id=?,due_on=?,done=? WHERE id=?",(title,course,due,done,ident))
            else:
                ident=c.execute("INSERT INTO priorities(title,course_id,due_on,done,created_at) VALUES(?,?,?,?,?)",(title,course,due,done,now())).lastrowid
            return ident

    def upsert_event(self,d,ident=None):
        title=required(d.get("title"),"evento")
        on=valid_date(d.get("event_date"))
        if not on: raise ValueError("A data do evento é obrigatória")
        t=safe_optional(d.get("event_time"),5)
        if t and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",t): raise ValueError("Horário inválido")
        with self._lock,self.connection() as c:
            course=self._exists(c,"courses",d.get("course_id"))
            done=int(bool(d.get("done",False)))
            if ident:
                self._exists(c,"study_events",ident)
                c.execute("UPDATE study_events SET title=?,course_id=?,event_date=?,event_time=?,done=? WHERE id=?",(title,course,on,t,done,ident))
            else:
                ident=c.execute("INSERT INTO study_events(title,course_id,event_date,event_time,done,created_at) VALUES(?,?,?,?,?,?)",(title,course,on,t,done,now())).lastrowid
            return ident

    def update_settings(self,d):
        allowed={"theme","voice_mode","silence_timeout"}
        with self._lock,self.connection() as c:
            for key,value in d.items():
                if key not in allowed:continue
                if key=="theme" and value not in {"light","dark"}:raise ValueError("Tema inválido")
                if key=="voice_mode" and value not in {"text","voice-and-text"}:raise ValueError("Modo de resposta inválido")
                if key=="silence_timeout": value=str(number(value,30,10,120))
                c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value)))

    def save_image(self,content,mime):
        types={"image/png":"png","image/jpeg":"jpg","image/webp":"webp","image/gif":"gif"}
        if mime not in types:raise ValueError("Formato permitido: PNG, JPG, WEBP ou GIF")
        if not content or len(content)>MAX_IMAGE_BYTES:raise ValueError("Imagem vazia ou maior que 8 MB")
        valid={"png":b"\x89PNG\r\n\x1a\n","jpg":b"\xff\xd8\xff","webp":b"RIFF","gif":b"GIF8"}
        ext=types[mime]
        if not content.startswith(valid[ext]):raise ValueError("Assinatura de imagem inválida")
        if ext=="webp" and content[8:12]!=b"WEBP":raise ValueError("Arquivo WEBP inválido")
        name=uuid.uuid4().hex+"."+ext
        (self.media_dir/name).write_bytes(content)
        return "/media/"+name

    def timer_state(self):
        t=self._timer
        elapsed=t["elapsed"] + (time.monotonic()-t["start"] if t["running"] and t["start"] else 0)
        return {"running":t["running"],"elapsed":round(elapsed,1),"course_id":t["course_id"]}

    def timer_command(self,action,course_id=None):
        with self._lock:
            t=self._timer
            if action=="start":
                if t["running"]:return self.timer_state()
                if course_id is not None:
                    with self.connection() as c: t["course_id"]=self._exists(c,"courses",course_id)
                t["running"]=True;t["start"]=time.monotonic()
            elif action=="pause":
                if t["running"]:t["elapsed"]+=time.monotonic()-t["start"]
                t["running"]=False;t["start"]=None
            elif action=="stop":
                t.update(running=False,elapsed=0.0,start=None,course_id=None)
            elif action!="state":raise ValueError("Comando de cronômetro inválido")
            return self.timer_state()

    def backup_zip(self):
        with self._lock:
            stream=io.BytesIO()
            with tempfile.TemporaryDirectory() as t:
                clone=Path(t)/"estudos.sqlite3"
                with self.connection() as source, sqlite3.connect(clone) as target:source.backup(target)
                with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
                    z.write(clone,"estudos.sqlite3")
                    for f in self.media_dir.iterdir():
                        if f.is_file() and re.fullmatch(r"[0-9a-f]{32}\.(png|jpg|webp|gif)",f.name):z.write(f,"media/"+f.name)
                    z.writestr("manifest.json",json.dumps({"application":"Ei, Máquina!","version":1,"created_at":now()},ensure_ascii=False))
            return stream.getvalue()

    def restore_zip(self,blob):
        if not blob or len(blob)>MAX_BACKUP_BYTES:raise ValueError("O arquivo deve ter até 80 MB")
        if not zipfile.is_zipfile(io.BytesIO(blob)):
            raise ValueError("O arquivo selecionado não é um ZIP de backup válido.")
        with self._lock, tempfile.TemporaryDirectory() as t:
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                names=set(z.namelist())
                if "estudos.sqlite3" not in names or "manifest.json" not in names:raise ValueError("Este não é um backup válido da Ei, Máquina!")
                if sum(info.file_size for info in z.infolist())>350*1024*1024:raise ValueError("Backup muito grande")
                for name in names:
                    if name not in {"estudos.sqlite3","manifest.json"} and not re.fullmatch(r"media/[0-9a-f]{32}\.(png|jpg|webp|gif)",name):raise ValueError("Arquivo inesperado no backup")
                manifest=json.loads(z.read("manifest.json"))
                if manifest.get("application")!="Ei, Máquina!":raise ValueError("Backup de outro aplicativo")
                candidate=Path(t)/"incoming.sqlite3"
                candidate.write_bytes(z.read("estudos.sqlite3"))
                with sqlite3.connect(candidate) as c:
                    if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValueError("Banco inválido")
                    tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if not {"courses","notes","study_history","settings"}.issubset(tables):raise ValueError("Backup incompleto")
                # Substitui o banco usando a API nativa de backup, evitando copiar um banco aberto.
                with sqlite3.connect(candidate) as src, self.connection() as dst:src.backup(dst)
                for name in sorted(names):
                    if name.startswith("media/"):
                        (self.media_dir/Path(name).name).write_bytes(z.read(name))
            self._timer.update(running=False,elapsed=0.0,start=None,course_id=None)
            self.init_schema()
            return True
