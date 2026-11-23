'use strict';
/* Ei, Máquina! v0.2 — interface local + IA local sob demanda (opcional). */
const app = {
  state:null, page:'home', courseId:null, noteId:null, folderId:'all', courseFilter:'all',
  calendarMonth:new Date(new Date().getFullYear(),new Date().getMonth(),1),
  calendarDay:localDate(new Date()), assistantReply:'', saveTimer:null, noteBusy:false, noteDirty:false,
  timerSnapshot:null, timerLoadedAt:0, restoring:false, aiStatus:null, aiBusy:false,
};
const LABELS={active:'Em andamento',paused:'Pausado',completed:'Concluído'};
const PAGE_LABELS={home:'Visão Geral',courses:'Cursos',agenda:'Agenda',notes:'Anotações',history:'Histórico',priorities:'Prioridades',timer:'Cronômetro',settings:'Configurações',backup:'Backup',course:'Detalhe do Curso',note:'Editor de anotação'};
const I={
  book:'<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  calendar:'<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M8 2v4M16 2v4M3 10h18"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
  notes:'<path d="M8 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/><path d="m12 15 9-9-3-3-9 9-1 4 4-1z"/>',
  history:'<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l4 2"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  mic:'<rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>',
  folder:'<path d="M3 6h6l2 3h10v11H3z"/>',
  settings:'<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9 7 7m10 10 2.1 2.1M2 12h3m14 0h3M4.9 19.1 7 17M17 7l2.1-2.1"/>',
  shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  trash:'<path d="M3 6h18M8 6V4h8v2m3 0-1 15H6L5 6M10 10v7m4-7v7"/>',
  external:'<path d="M12 5H5v14h14v-7M13 3h8v8M11 13 21 3"/>',
  copy:'<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M4 16V4h12"/>',
};
function ico(name,size=19){return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="vertical-align:middle">${I[name]||I.book}</svg>`;}
function $(s){return document.querySelector(s)}
function $$(s){return [...document.querySelectorAll(s)]}
function e(v){return String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]))}
function id(v){return Number(v)||null}
function nowLocal(){return localDate(new Date())}
function localDate(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
function formatDate(s){if(!s)return '—';const [y,m,d]=s.slice(0,10).split('-');return `${d}/${m}/${y}`}
function dateLong(s){return new Intl.DateTimeFormat('pt-BR',{month:'long',year:'numeric'}).format(s)}
function strip(html){const temp=document.createElement('div');temp.innerHTML=html||'';return temp.textContent||''}
function truncate(v,n=100){v=String(v||'');return v.length>n?v.slice(0,n-1)+'…':v}
function courseById(cid){return app.state.courses.find(c=>c.id===Number(cid))}
function courseName(cid){return courseById(cid)?.name||'Estudo livre'}
function noteById(nid){return app.state.notes.find(n=>n.id===Number(nid))}
function activeCourses(){return app.state.courses.filter(c=>c.status==='active')}
function pill(status){return `<span class="pill ${status==='completed'?'success':status==='paused'?'paused':''}">${e(LABELS[status]||status)}</span>`}
function progress(p){let n=Math.min(100,Math.max(0,Number(p||0)));return `<div class="progress-line"><div class="progress-track"><div class="progress-fill" style="width:${n}%"></div></div><span class="percent">${n}%</span></div>`}
function empty(title,desc){return `<div class="empty"><span class="empty-icon">✦</span><strong>${e(title)}</strong><div>${e(desc)}</div></div>`}
function heading(title,subtitle,action=''){return `<div class="page-heading"><div><h1 class="page-title">${e(title)}</h1><p class="page-subtitle">${e(subtitle)}</p></div>${action}</div>`}
function card(title,body,action='',cls=''){return `<section class="card ${cls}"><div class="card-title"><span>${title}</span>${action}</div>${body}</section>`}
function shortDate(s){return String(s||'').slice(0,10)}
async function api(url, method='GET', data=undefined, raw=false){
  let opts={method,headers:{}};
  if(data!==undefined){if(raw){opts.body=data;opts.headers['Content-Type']=data.type||'application/zip';}else{opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(data)}}
  const r=await fetch(url,opts);
  if(!r.ok){let x;try{x=await r.json()}catch{x={error:`Erro ${r.status}`}};throw Error(x.error||`Erro ${r.status}`)}
  return r.json();
}
function notify(message){const el=$('#toast');el.textContent=message;el.hidden=false;clearTimeout(notify.timer);notify.timer=setTimeout(()=>el.hidden=true,3400)}
async function load(){app.state=await api('/api/state');app.timerSnapshot=app.state.timer;app.timerLoadedAt=Date.now();document.documentElement.dataset.theme=app.state.settings.theme||'light';try{app.aiStatus=await api('/api/ai/status')}catch{app.aiStatus=null}}
async function refresh(){await load();render()}
function goto(page,detail=null){
  clearTimeout(app.saveTimer);
  if(app.page==='note'&&$('#note-content'))saveNote().catch(x=>notify(x.message));
  app.page=page;if(page==='course')app.courseId=detail;if(page==='note')app.noteId=detail;
  render();window.scrollTo(0,0);
}
function setNav(){const selected=['course'].includes(app.page)?'courses':['note'].includes(app.page)?'notes':app.page;
  $$('#main-nav [data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===selected));
}
function courseCard(c){return `<button class="course-card" data-action="open-course" data-id="${c.id}">
 <div class="course-line"><span class="course-icon">${ico('book',22)}</span><strong class="course-name">${e(c.name)}</strong></div>
 <div class="course-lesson">${e(c.current_lesson||'Organize suas próximas aulas')}</div>${progress(c.progress)}<div class="status">${pill(c.status)}</div></button>`}
function historyCard(h){const notes=h.note_ids||[];return `<div class="history-row"><div class="history-top"><strong>${e(h.course_name)}${h.lesson?' — '+e(h.lesson):''}</strong><span class="history-date">${formatDate(h.studied_on)}</span></div>
 <div class="history-summary">${e(h.subject)}${h.description?' · '+e(truncate(h.description,135)):''}</div>
 <div class="history-links">${h.completed?'<span class="pill success">Concluído</span>':'<span class="pill">Em andamento</span>'}${notes.length?`<button class="text-action" data-action="open-note" data-id="${notes[0]}">Abrir anotação ↗</button>`:'<span class="muted" style="font-size:12px">Sem anotação vinculada</span>'}</div></div>`}
function compactWeek(){const today=new Date(),dow=today.getDay(),monday=new Date(today);monday.setDate(today.getDate()-(dow+6)%7);
 const days=Array.from({length:7},(_,i)=>{const d=new Date(monday);d.setDate(monday.getDate()+i);return d});const tags=['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'];
 return `<div class="week">${days.map((d,i)=>{const key=localDate(d);const n=app.state.events.filter(x=>x.event_date===key).length;return `<button data-page="agenda" class="week-day ${key===nowLocal()?'selected':''}"><small>${tags[i]}</small><strong>${d.getDate()}</strong>${n?'<span class="dot"></span>':'<span style="display:block;height:8px"></span>'}</button>`}).join('')}</div>`}
function renderHome(){const c=activeCourses(), notes=app.state.notes, hist=app.state.history, priorities=app.state.priorities.filter(t=>!t.done).slice(0,3);
 const left=`<div class="stack"><div class="hero"><h1>Ei, Máquina!</h1><p>Seu organizador pessoal de estudos</p>
 <div class="assistant-status" role="status">${app.aiStatus?.configured?`<span class="pill success">IA local ${app.aiStatus.running?'ativa':'pronta'}</span> <span class="muted">${e(app.aiStatus.model||'')}</span>`:'<span class="pill paused">IA local não instalada</span> <button class="text-action" type="button" data-page="settings">Como ativar?</button>'}</div><form class="commandbar" id="command-form"><span class="sparkle">✦</span><input name="command" placeholder="Diga ou digite um comando..." aria-label="Comando por texto" autocomplete="off"><button class="command-send" type="submit" aria-label="Enviar comando">➤</button><button type="button" data-action="voice-info" title="Reconhecimento de voz ainda não está disponível" aria-label="Informações sobre voz">${ico('mic',21)}</button></form>${app.assistantReply?`<div class="assistant-reply">${e(app.assistantReply)}</div>`:''}</div>
 ${card('Cursos em andamento',c.length?`<div class="courses-grid">${c.slice(0,3).map(courseCard).join('')}</div>`:empty('Nenhum curso em andamento','Cadastre um curso para começar.'),`<button class="text-action" data-page="courses">Ver todos →</button>`)}
 ${card('Histórico de Estudos',hist.length?hist.slice(0,3).map(historyCard).join(''):empty('Seu histórico começa aqui','Registre o conteúdo estudado, não as horas.'),`<button class="text-action" data-page="history">Ver histórico completo →</button>`)}</div>`;
 const right=`<div class="stack">${card('☼ Hoje',priorities.length?priorities.map(t=>`<div class="today-task"><button class="check-button" data-action="toggle-priority" data-id="${t.id}" title="Concluir prioridade"></button><span>${e(t.title)}</span></div>`).join(''):empty('Nada pendente para hoje','Adicione prioridades quando quiser.'),`<button class="text-action" data-page="priorities">Ver prioridades →</button>`)}
 ${card('Anotações recentes',notes.length?`<div class="mini-note" data-action="open-note" data-id="${notes[0].id}" role="button" tabindex="0"><div class="mini-note-icon">${ico('notes',29)}</div><div><strong>${e(notes[0].title)}</strong><p>${e(truncate(strip(notes[0].content_html),93)||'Clique para continuar suas anotações.')}</p></div></div>`:empty('Nenhuma anotação ainda','Crie sua primeira nota com textos e prints.'),`<button class="text-action" data-page="notes">Ver todas →</button>`)}
 ${card('Agenda de Estudos',compactWeek()+`<div class="mini-agenda-next">${ico('calendar',17)} ${e(app.state.events.filter(x=>x.event_date>=nowLocal()).slice(0,1).map(x=>`Próximo estudo: ${x.title}`).join('')||'Calendário livre para organizar seus estudos.')}</div>`,`<button class="text-action" data-page="agenda">Ver agenda →</button>`)}</div>`;
 return `<div class="layout-grid">${left}${right}</div>`;
}
function renderCourses(){let courses=app.state.courses.filter(c=>app.courseFilter==='all'||c.status===app.courseFilter);
 const filter=`<div class="toolbar"><select class="select" id="course-status-filter"><option value="all">Todos os cursos</option>${Object.entries(LABELS).map(([v,l])=>`<option value="${v}" ${v===app.courseFilter?'selected':''}>${l}</option>`).join('')}</select><div class="spacer"></div></div>`;
 return heading('Meus cursos','Acompanhe aulas, links, progresso e anotações.',`<button class="primary" data-action="new-course">${ico('plus',16)} Novo curso</button>`)+filter+
 `<section class="card">${courses.length?`<div class="courses-grid">${courses.map(courseCard).join('')}</div>`:empty('Nenhum curso nesta categoria','Você pode cadastrar um curso ou mudar o filtro.')}</section>`;
}
function renderCourse(){const c=courseById(app.courseId);if(!c)return `<div class="card">Curso não encontrado.</div>`;
 const ls=c.lessons||[];
 const rows=ls.map(l=>`<div class="list-card"><button data-action="toggle-lesson" data-id="${l.id}" class="check-button ${l.completed?'checked':''}" title="Marcar aula como concluída">${l.completed?'✓':''}</button><div class="grow"><strong>${e(l.title)}</strong><p>${e(l.module_name||'Sem módulo')}</p></div><button class="text-action" data-action="delete-lesson" data-id="${l.id}" title="Excluir aula">Excluir</button></div>`).join('');
 const right=card('Acompanhamento',`<div class="info-stack"><div class="detail-item">${pill(c.status)}<p class="muted">${e(c.platform||'Plataforma não informada')}</p></div><div class="detail-item"><strong>Progresso</strong>${progress(c.progress)}</div><div class="detail-item"><strong>Última aula</strong><p>${e(c.current_lesson||'Não registrada')}</p></div><div class="detail-item"><strong>Último estudo</strong><p>${formatDate(c.last_study)}</p></div></div><div class="toolbar" style="margin-top:15px"><button class="secondary" data-action="edit-course" data-id="${c.id}">Editar curso</button>${c.url?`<a class="secondary btn" href="${e(c.url)}" target="_blank" rel="noopener noreferrer">Abrir plataforma ↗</a>`:''}</div><button class="ghost small-btn" data-action="delete-course" data-id="${c.id}">Excluir curso</button>`);
 const left=card('Módulos e aulas',c.mode==='detailed'?`${rows||empty('Sem aulas cadastradas','Cadastre as aulas e marque seu progresso.')}
 <button class="secondary" data-action="new-lesson" data-id="${c.id}" style="margin-top:13px">+ Adicionar aula</button>`:`<p class="muted">Modo simples: informe seu progresso manualmente e onde parou.</p><button class="secondary" data-action="edit-course" data-id="${c.id}">Atualizar progresso</button>`);
 return heading(c.name,`${c.mode==='simple'?'Acompanhamento simples':'Acompanhamento detalhado'} · ${e(c.platform||'Curso online')}`)+`<div class="toolbar"><button class="ghost" data-page="courses">← Voltar aos cursos</button><button class="secondary" data-action="new-note" data-course="${c.id}">+ Anotação da aula</button><button class="primary" data-action="new-history" data-course="${c.id}">Registrar estudo</button></div><div class="layout-grid"><div>${left}</div><div>${right}</div></div>`;
}
function renderPriorities(){let list=app.state.priorities;
 const sets=[{title:'Pendentes',items:list.filter(t=>!t.done)},{title:'Concluídas',items:list.filter(t=>t.done)}];
 return heading('Prioridades','Organize suas tarefas sem precisar seguir horários rígidos.',`<button class="primary" data-action="new-priority">+ Nova prioridade</button>`)+`<div class="two-col">${sets.map(group=>card(group.title,group.items.length?group.items.map(t=>`<div class="list-card"><button class="check-button ${t.done?'checked':''}" data-action="toggle-priority" data-id="${t.id}">${t.done?'✓':''}</button><div class="grow"><strong>${e(t.title)}</strong><p>${e(courseById(t.course_id)?.name||'Sem curso')}${t.due_on?' · '+formatDate(t.due_on):''}</p></div><button class="text-action" data-action="delete-priority" data-id="${t.id}">Excluir</button></div>`).join(''):empty('Nada por aqui','As tarefas aparecerão quando forem cadastradas.'))).join('')}</div>`;
}
function renderAgenda(){const month=app.calendarMonth;const year=month.getFullYear(),mon=month.getMonth();const first=new Date(year,mon,1).getDay(),daysInMonth=new Date(year,mon+1,0).getDate();
 const dates=Array.from({length:Math.ceil((first+daysInMonth)/7)*7},(_,i)=>{const day=i-first+1;if(day<1||day>daysInMonth)return `<div></div>`;const date=localDate(new Date(year,mon,day));const events=app.state.events.filter(x=>x.event_date===date);return `<button data-action="select-day" data-date="${date}" class="month-day ${date===app.calendarDay?'active':''} ${date===nowLocal()?'today':''}"><b>${day}</b>${events.length?`<div class="month-dots">${events.slice(0,3).map(()=>'<span></span>').join('')}</div>`:''}</button>`});
 const events=app.state.events.filter(x=>x.event_date===app.calendarDay);
 return heading('Agenda de Estudos','Seu calendário pessoal e flexível.',`<button class="primary" data-action="new-event">+ Agendar estudo</button>`)+`<div class="layout-grid"><section class="card"><div class="month-head"><button class="ghost" data-action="month-prev">←</button><strong>${dateLong(month)}</strong><button class="ghost" data-action="month-next">→</button></div><div class="month-grid">${['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'].map(d=>`<div class="month-weekday">${d}</div>`).join('')}${dates.join('')}</div></section><section class="card"><div class="card-title">${formatDate(app.calendarDay)}</div>${events.length?events.map(ev=>`<div class="list-card"><div class="grow"><strong>${e(ev.title)}</strong><p>${e(ev.event_time||'Horário livre')} · ${e(courseById(ev.course_id)?.name||'Estudo livre')}</p></div><button class="text-action" data-action="delete-event" data-id="${ev.id}">Excluir</button></div>`).join(''):empty('Dia livre','Não há estudos marcados para este dia.')}<button class="secondary" data-page="priorities">Ver prioridades</button></section></div>`;
}
function renderNotes(){
 const folders=app.state.folders;
 let notes=app.state.notes;
 if(app.folderId==='uncategorized') notes=notes.filter(n=>!n.folder_id&&!n.course_id);
 else if(String(app.folderId).startsWith('c')) notes=notes.filter(n=>n.course_id===Number(String(app.folderId).slice(1)));
 else if(app.folderId!=='all') {
   const selected=Number(app.folderId), descendants=new Set([selected]);
   for(let pass=0;pass<folders.length;pass++)for(const f of folders)if(descendants.has(f.parent_id))descendants.add(f.id);
   notes=notes.filter(n=>descendants.has(n.folder_id));
 }
 const nested=[];
 function walkFolders(parent,depth,seen=new Set()){
   for(const f of folders.filter(x=>x.parent_id===parent)){
     if(seen.has(f.id))continue;
     const next=new Set(seen);next.add(f.id);
     nested.push([String(f.id),f.name,depth]);
     walkFolders(f.id,depth+1,next);
   }
 }
 walkFolders(null,0);
 const nav=[['all','Todas as anotações',0],...app.state.courses.map(c=>['c'+c.id,c.name,1]),...nested,['uncategorized','Sem pasta',0]];
 const navigation=nav.map(([key,label,depth])=>`<button class="folder-button ${String(key)===String(app.folderId)?'selected':''}" data-action="note-filter" data-filter="${e(key)}" style="padding-left:${12+Number(depth||0)*14}px">${ico('folder',15)} <span>${e(label)}</span></button>`).join('');
 const cards=notes.map(n=>{
    const context=n.course_id ? courseName(n.course_id)+(n.lesson?' · '+n.lesson:'') : n.folder_id ? (folders.find(f=>f.id===n.folder_id)?.name||'Pasta') : 'Nota livre';
    const summary=truncate(strip(n.content_html),110)||'Anotação sem texto.';
    return `<button class="note-card" data-action="open-note" data-id="${n.id}"><div style="color:var(--accent)">${ico('notes',24)}</div><b>${e(n.title)}</b><small>${e(context)}</small><p>${e(summary)}</p></button>`;
 }).join('');
 const contents=notes.length?`<div class="notes-grid">${cards}</div>`:empty('Nenhuma anotação','Crie uma anotação ou escolha outra pasta.');
 return heading('Minhas anotações','Editor livre com textos, códigos, prints e imagens.',`<div class="toolbar"><button class="secondary" data-action="new-folder">+ Nova pasta</button>${/^\d+$/.test(String(app.folderId))?`<button class="ghost" data-action="delete-folder" data-id="${app.folderId}">Excluir pasta</button>`:''}<button class="primary" data-action="new-note">+ Nova anotação</button></div>`)+
 `<section class="card"><div class="notes-layout"><aside class="folder-col"><div class="card-title">Biblioteca</div>${navigation}</aside><div class="notes-main"><div class="card-title">${app.folderId==='all'?'Todas as notas':'Anotações da seleção'} <small class="muted" style="font-size:12px">${notes.length} registros</small></div>${contents}</div></div></section>`;
}
function renderNoteEditor(){const note=noteById(app.noteId);const title=note?.title||'';
 const courseOptions=app.state.courses.map(c=>`<option value="${c.id}" ${c.id===note?.course_id?'selected':''}>${e(c.name)}</option>`).join('');
 const folderOptions=app.state.folders.map(f=>`<option value="${f.id}" ${f.id===note?.folder_id?'selected':''}>${e(f.name)}</option>`).join('');
 return heading(note?'Editar anotação':'Nova anotação','Salvamento automático no HD, sem análise dos prints pela IA.',`<button class="ghost" data-page="notes">← Minhas anotações</button>`)+`<div class="editor-layout"><section class="card"><input id="note-title" class="editor-title" maxlength="200" placeholder="Título da anotação" value="${e(title)}" aria-label="Título da anotação"><div class="editor-tools"><button type="button" data-action="format" data-cmd="bold" title="Negrito"><b>B</b></button><button data-action="format" data-cmd="italic" title="Itálico"><i>I</i></button><button data-action="format" data-cmd="underline" title="Sublinhado"><u>U</u></button><button data-action="format" data-cmd="insertUnorderedList" title="Lista">☷</button><button data-action="format" data-cmd="insertOrderedList" title="Lista numerada">1.</button><button data-action="format" data-cmd="formatBlock" data-param="pre" title="Código">{ }</button><button data-action="choose-image" title="Adicionar imagem">${ico('notes',16)} Imagem</button><input type="file" id="note-file" hidden accept="image/png,image/jpeg,image/webp,image/gif"></div><div id="note-content" contenteditable="true" role="textbox" aria-label="Conteúdo da anotação" aria-multiline="true" data-placeholder="Escreva livremente, cole prints com Ctrl+V e registre suas ideias..."></div><p class="save-status" id="note-save-status">${note?'Carregada do HD.':'Nova anotação.'}</p></section><aside class="card"><div class="card-title">Organização</div><div class="form-field"><label for="note-course">Curso</label><select id="note-course"><option value="">Anotação livre</option>${courseOptions}</select></div><div class="form-field" style="margin-top:16px"><label for="note-lesson">Aula vinculada</label><input id="note-lesson" type="text" placeholder="Ex.: Aula 12" value="${e(note?.lesson||'')}"></div><div class="form-field" style="margin-top:16px"><label for="note-folder">Pasta</label><select id="note-folder"><option value="">Sem pasta</option>${folderOptions}</select></div><p class="muted" style="margin-top:21px;font-size:13px">Anotações com o mesmo curso e aula serão vinculadas ao Histórico de Estudos automaticamente.</p><div style="margin-top:25px;display:grid;gap:10px"><button class="primary" data-action="save-note">Salvar agora</button>${note?`<button class="ghost" data-action="delete-note" data-id="${note.id}">Excluir anotação</button>`:''}</div></aside></div>`;
}
function renderHistory(){const hist=app.state.history;
 return heading('Histórico de Estudos','O que você estudou, em qual aula e quando — sem contar horas.',`<button class="primary" data-action="new-history">+ Registrar estudo</button>`)+`<div class="layout-grid"><section class="card">${hist.length?hist.map(h=>`<div class="history-row"><div class="history-top"><strong>${e(h.course_name)}${h.lesson?' — '+e(h.lesson):''}</strong><span class="history-date">${formatDate(h.studied_on)}</span></div><div class="history-summary"><strong>Assunto:</strong> ${e(h.subject)}</div><p style="margin:0 0 10px">${e(h.description)}</p><div class="history-links">${h.completed?'<span class="pill success">Concluído</span>':'<span class="pill">Em andamento</span>'}${(h.note_ids||[]).map(nid=>`<button class="text-action" data-action="open-note" data-id="${nid}">Abrir anotação ↗</button>`).join('')}<button class="text-action" data-action="edit-history" data-id="${h.id}">Editar</button><button class="text-action" data-action="delete-history" data-id="${h.id}">Excluir</button></div></div>`).join(''):empty('Histórico vazio','Registre sua primeira aula por texto ou formulário.')}</section><section class="card">${card('Como registrar?','<p>Informe curso, aula, assunto e uma descrição do que aprendeu.</p><p class="muted">Quando sua anotação tiver o mesmo curso e aula, o vínculo será criado automaticamente.</p>','','tight')}<button class="secondary" data-page="notes" style="margin-top:13px">Abrir minhas anotações</button></section></div>`;
}
function formatSeconds(sec){let s=Math.floor(Math.max(0,sec));return [Math.floor(s/3600),Math.floor(s/60)%60,s%60].map(v=>String(v).padStart(2,'0')).join(':')}
function displaySeconds(){const t=app.timerSnapshot||{elapsed:0,running:false};return t.elapsed+(t.running?(Date.now()-app.timerLoadedAt)/1000:0)}
function renderTimer(){const t=app.timerSnapshot||{elapsed:0,running:false};return heading('Cronômetro','Inicie, pause e encerre uma sessão sem registrar horas no histórico.')+`<div class="layout-grid"><section class="card timer-panel"><div class="timer-caption">${t.running?'Sessão em andamento':'Cronômetro disponível'}</div><div class="timer-digits" id="timer-digits">${formatSeconds(displaySeconds())}</div><div class="timer-caption">${t.course_id?'Curso: '+e(courseName(t.course_id)):'Escolha um curso para iniciar'}</div><div class="timer-controls" style="margin-top:40px">${t.running?`<button class="primary" data-action="timer-pause">Pausar</button>`:`<button class="primary" data-action="timer-start">${t.elapsed>0?'Continuar':'Iniciar'}</button>`}<button class="ghost" data-action="timer-stop">Encerrar / zerar</button></div><p class="muted" style="margin-top:35px;font-size:13px">O cronômetro continua no servidor local ao fechar a aba, desde que o aplicativo permaneça aberto.</p></section><section class="card"><div class="card-title">Curso da sessão</div><select id="timer-course" class="select" style="width:100%"><option value="">Estudo livre</option>${app.state.courses.map(c=>`<option value="${c.id}" ${t.course_id===c.id?'selected':''}>${e(c.name)}</option>`).join('')}</select><p class="muted" style="margin-top:19px">O tempo é temporário. Nenhuma duração é salva no Histórico de Estudos.</p></section></div>`}
function renderSettings(){const settings=app.state.settings;
 return heading('Configurações','Personalize o visual e consulte os recursos previstos.')+`<div class="layout-grid"><section class="card"><div class="card-title">Aparência</div><div class="settings-list"><div class="settings-row"><div><strong>Tema do dashboard</strong><p>Claro roxo/lilás ou escuro roxo</p></div><select id="theme-select"><option value="light" ${settings.theme!=='dark'?'selected':''}>Claro lilás</option><option value="dark" ${settings.theme==='dark'?'selected':''}>Escuro</option></select></div></div><div class="card-title" style="margin-top:26px">Privacidade e dados</div><div class="settings-row"><div><strong>Memória local</strong><p>Cursos, progresso, notas, calendário e histórico.</p></div><span class="pill success">Ativada</span></div><div class="settings-row"><div><strong>Backups</strong><p>Exportação e restauração somente quando você escolher.</p></div><button data-page="backup" class="secondary">Gerenciar backup</button></div></section><section class="card"><div class="card-title">IA local e voz</div><div class="settings-row"><div><strong>IA local sob demanda</strong><p>${app.aiStatus?.configured?`Modelo: ${e(app.aiStatus.model||'')} · carregado apenas quando necessário.`:'Para instalar gratuitamente, execute no terminal <code>./configurar_ia_local.sh</code> na pasta do aplicativo.'}</p></div><span class="pill ${app.aiStatus?.configured?'success':'paused'}">${app.aiStatus?.configured?'Configurada':'Não instalada'}</span></div><div class="settings-row"><div><strong>Consumo de recursos</strong><p>O modelo é descarregado após cerca de 3 minutos sem pedidos. A primeira resposta pode ser demorada.</p></div><span class="pill">Sob demanda</span></div><div class="settings-row"><div><strong>Comandos de texto</strong><p>Exemplos: "Onde parei no curso Python?" ou "Adicionar prioridade: revisar funções".</p></div><span class="pill success">Disponíveis</span></div><div class="settings-row"><div><strong>Palavra de ativação e voz</strong><p>"Ei, Máquina!", transcrição e fala serão desenvolvidas em uma etapa específica.</p></div><span class="pill paused">Pendente</span></div><button class="secondary" data-action="voice-info" style="margin-top:15px">Saiba mais sobre a etapa de voz</button></section></div>`;
}
function renderBackup(){return heading('Backup e restauração','Cópias manuais dos seus dados locais.')+`<div class="two-col"><section class="card"><div class="card-title">Exportar uma cópia</div><p>Baixe um arquivo ZIP com banco de dados, anotações e imagens que você colou.</p><p class="muted">Escolha outro HD ou pendrive sempre que possível.</p><button class="primary" data-action="backup-export">${ico('copy',17)} Criar backup agora</button></section><section class="card"><div class="card-title">Restaurar uma cópia</div><p>Recupere seus dados a partir de um backup anterior da Ei, Máquina!.</p><p class="muted">Esta operação substitui os dados locais atuais e exige confirmação.</p><input type="file" id="restore-file" accept=".zip,application/zip" aria-label="Escolher arquivo ZIP"><button class="ghost" data-action="backup-restore" style="margin-top:14px">Restaurar backup</button></section></div>`;
}
function render(){setNav();const renderers={home:renderHome,courses:renderCourses,course:renderCourse,priorities:renderPriorities,agenda:renderAgenda,notes:renderNotes,note:renderNoteEditor,history:renderHistory,timer:renderTimer,settings:renderSettings,backup:renderBackup};
 $('#view').innerHTML=(renderers[app.page]||renderHome)();if(app.page==='note'){$('#note-content').innerHTML=noteById(app.noteId)?.content_html||'';}
}
// ---------- Formulários e janelas ----------
function field(name,label,value='',type='text',opts={}){let html='';if(type==='select')html=`<select name="${name}" ${opts.required?'required':''}>${(opts.options||[]).map(([v,l])=>`<option value="${e(v)}" ${String(v)===String(value??'')?'selected':''}>${e(l)}</option>`).join('')}</select>`;
 else if(type==='textarea')html=`<textarea name="${name}" ${opts.required?'required':''}>${e(value)}</textarea>`;
 else html=`<input name="${name}" type="${type}" value="${e(value)}" ${opts.required?'required':''} ${opts.max?'max="'+opts.max+'"':''} ${opts.min?'min="'+opts.min+'"':''}>`;
 return `<div class="form-field ${opts.full?'full':''}"><label>${e(label)}</label>${html}</div>`}
function courseOptions(first='Sem curso'){return [['',first],...app.state.courses.map(c=>[String(c.id),c.name])];}
function modal(title,formId,fields,submit='Salvar',extra=''){const dialog=$('#modal');dialog.innerHTML=`<div class="modal-panel" role="dialog" aria-modal="true" aria-label="${e(title)}"><h2 class="modal-title">${e(title)}</h2><form id="modal-form" data-form="${e(formId)}"><div class="form-grid">${fields}${extra}</div><div class="modal-actions"><button type="button" class="ghost" data-action="close-modal">Cancelar</button><button class="primary" type="submit">${e(submit)}</button></div></form></div>`;dialog.hidden=false;dialog.querySelector('input,select,textarea')?.focus()}
function closeModal(){const n=$('#modal');n.hidden=true;n.innerHTML=''}
function openCourseModal(c){modal(c?'Editar curso':'Cadastrar curso',c?'edit-course:'+c.id:'new-course',
 field('name','Nome do curso',c?.name||'','text',{required:true,full:true})+
 field('platform','Plataforma',c?.platform||'','text')+field('url','Link do curso (opcional)',c?.url||'','url')+
 field('mode','Modo de acompanhamento',c?.mode||'simple','select',{options:[['simple','Simples'],['detailed','Detalhado']]})+
 field('status','Status',c?.status||'active','select',{options:Object.entries(LABELS)})+
 field('progress','Progresso manual (%)',c?.progress||0,'number',{min:0,max:100})+
 field('current_lesson','Onde parou',c?.current_lesson||'','text',{full:true})
 )}
function openLessonModal(courseId){modal('Adicionar aula','new-lesson:'+courseId,
  field('module_name','Módulo (opcional)','')+field('title','Título da aula','Aula 01','text',{required:true})+
  field('position','Ordem',courseById(courseId)?.lessons?.length+1||1,'number',{min:0,max:9999}))}
function openFolderModal(){modal('Nova pasta','new-folder',field('name','Nome da pasta','','text',{required:true,full:true})+field('parent_id','Pasta mãe (opcional)','','select',{options:[['','Raiz'],...app.state.folders.map(f=>[f.id,f.name])],full:true}))}
function openPriorityModal(){modal('Nova prioridade','new-priority',field('title','Tarefa','','text',{required:true,full:true})+field('course_id','Curso relacionado','','select',{options:courseOptions()})+field('due_on','Data opcional','','date'))}
function openEventModal(){modal('Agendar estudo','new-event',field('title','O que vai estudar?','','text',{required:true,full:true})+
 field('event_date','Data',app.calendarDay,'date',{required:true})+field('event_time','Horário (opcional)','','time')+field('course_id','Curso','','select',{options:courseOptions(),full:true}))}
function openHistoryModal(h=null,courseId=null){const cid=h?.course_id||courseId||'';const related=app.state.notes.filter(n=>!cid||n.course_id===Number(cid));const noteOptions=related.map(n=>`<option value="${n.id}" ${(h?.note_ids||[]).includes(n.id)?'selected':''}>${e(n.title)}</option>`).join('');
 modal(h?'Editar registro':'Registrar estudo',h?'edit-history:'+h.id:'new-history',
  field('course_id','Curso',cid,'select',{options:courseOptions()})+field('lesson','Aula (ex.: Aula 12)',h?.lesson||'')+
  field('subject','Assunto estudado',h?.subject||'','text',{required:true,full:true})+field('description','O que você aprendeu?',h?.description||'','textarea',{full:true})+
  field('studied_on','Data',h?.studied_on||nowLocal(),'date',{required:true})+field('completed','Status',String(h?.completed??1),'select',{options:[['1','Concluído'],['0','Em andamento']]})+`<div class="form-field full"><label>Anotações vinculadas (Ctrl para múltiplas)</label><select name="note_ids" multiple size="4" aria-label="Vincular anotações">${noteOptions}</select><small class="muted">Se não selecionar nenhuma, serão vinculadas as anotações com mesmo curso e aula.</small></div>`
 )}
function dataObject(form){const d=Object.fromEntries(new FormData(form).entries());for(const k of ['course_id','folder_id','parent_id'])if(k in d)d[k]=id(d[k]);return d}
async function submitModal(form){const name=form.dataset.form,d=dataObject(form);const [act,arg]=name.split(':');
 if(act==='new-course')await api('/api/courses','POST',d);
 else if(act==='edit-course')await api('/api/courses/'+arg,'PATCH',d);
 else if(act==='new-lesson'){d.course_id=id(arg);await api('/api/lessons','POST',d)}
 else if(act==='new-folder')await api('/api/folders','POST',d);
 else if(act==='new-priority')await api('/api/priorities','POST',d);
 else if(act==='new-event')await api('/api/events','POST',d);
 else if(act==='new-history'||act==='edit-history'){
   d.completed=d.completed==='1';d.note_ids=[...form.querySelector('select[name="note_ids"]').selectedOptions].map(o=>Number(o.value));
   // Vínculos automáticos continuam disponíveis quando nenhuma nota foi escolhida.
   if(!d.note_ids.length)delete d.note_ids;
   await api('/api/history'+(arg?'/'+arg:''),arg?'PATCH':'POST',d);
 }
 closeModal();await refresh();notify('Salvo no seu computador.');
}
// ---------- Anotações e imagens ----------
function noteDraft(){return {title:$('#note-title')?.value||'',content_html:$('#note-content')?.innerHTML||'',course_id:id($('#note-course')?.value),lesson:$('#note-lesson')?.value||'',folder_id:id($('#note-folder')?.value)}}
async function saveNote(){
 if(app.page!=='note'||!$('#note-title'))return false;
 if(app.noteBusy){app.noteDirty=true;return false}
 const d=noteDraft();
 if(!d.title.trim()){
   const status=$('#note-save-status');if(status)status.textContent='Digite um título para salvar.';
   return false;
 }
 app.noteBusy=true;app.noteDirty=false;
 const msg=$('#note-save-status');if(msg)msg.textContent='Salvando no HD...';
 const editId=app.noteId;
 try{
   const result=await api('/api/notes'+(editId?'/'+editId:''),editId?'PATCH':'POST',d);
   if(!editId&&app.page==='note')app.noteId=result.id;
   app.state=await api('/api/state');
   if($('#note-save-status'))$('#note-save-status').textContent='✓ Salvo localmente';
   return true;
 }finally{
   app.noteBusy=false;
   if(app.noteDirty&&app.page==='note')queueSave();
 }
}
function queueSave(){
 app.noteDirty=true;
 clearTimeout(app.saveTimer);
 const status=$('#note-save-status');if(status)status.textContent='Alterações pendentes...';
 app.saveTimer=setTimeout(()=>saveNote().catch(err=>notify(err.message)),800);
}
async function saveImage(file){if(!file)return;const types=['image/png','image/jpeg','image/webp','image/gif'];if(!types.includes(file.type)){notify('Use PNG, JPG, WEBP ou GIF.');return}if(file.size>8*1024*1024){notify('Imagem maior que 8 MB.');return}
 const result=await api('/api/images','POST',file,true);$('#note-content')?.focus();document.execCommand('insertHTML',false,`<img alt="Print da anotação" src="${result.url}">`);queueSave();notify('Imagem inserida na anotação.')}
async function restoreBackup(){const f=$('#restore-file')?.files?.[0];if(!f){notify('Selecione um ZIP de backup.');return}if(!confirm('Restaurar vai SUBSTITUIR o banco de dados atual. Você criou um backup antes de continuar?'))return;
 await api('/api/restore','POST',f,true);app.page='home';app.folderId='all';app.courseId=null;await refresh();notify('Backup restaurado com sucesso.')}
function runAction(el){const a=el.dataset.action,ident=id(el.dataset.id);
 switch(a){
  case 'new-course':openCourseModal(null);break;
  case 'open-course':goto('course',ident);break;
  case 'edit-course':openCourseModal(courseById(ident));break;
  case 'delete-course':if(confirm('Excluir este curso? As anotações e o histórico serão preservados, sem o vínculo ao curso.'))api('/api/courses/'+ident,'DELETE').then(refresh).catch(err=>notify(err.message));break;
  case 'new-lesson':openLessonModal(ident);break;
  case 'toggle-lesson':{const c=app.state.courses.find(c=>c.lessons?.some(l=>l.id===ident));const l=c?.lessons.find(l=>l.id===ident);if(l)api('/api/lessons/'+ident,'PATCH',{completed:!l.completed}).then(refresh).catch(err=>notify(err.message));break}
  case 'delete-lesson':if(confirm('Excluir esta aula cadastrada?'))api('/api/lessons/'+ident,'DELETE').then(refresh).catch(err=>notify(err.message));break;
  case 'new-folder':openFolderModal();break;
  case 'delete-folder':if(confirm('Excluir esta pasta? As anotações serão mantidas, sem a pasta.'))api('/api/folders/'+ident,'DELETE').then(async()=>{app.folderId='all';await refresh()}).catch(err=>notify(err.message));break;
  case 'note-filter':app.folderId=el.dataset.filter;render();break;
  case 'new-note':{app.noteId=null;goto('note');const cid=id(el.dataset.course);if(cid)$('#note-course').value=cid;break}
  case 'open-note':goto('note',ident);break;
  case 'save-note':saveNote().then(ok=>notify(ok?'Anotação salva.':'Informe o título da anotação.')).catch(err=>notify(err.message));break;
  case 'delete-note':if(confirm('Excluir esta anotação e seus vínculos com o histórico?'))api('/api/notes/'+ident,'DELETE').then(async()=>{app.page='notes';await refresh()}).catch(err=>notify(err.message));break;
  case 'format':{const editor=$('#note-content');editor?.focus();document.execCommand(el.dataset.cmd,false,el.dataset.param||null);queueSave();break}
  case 'choose-image':$('#note-file')?.click();break;
  case 'new-history':openHistoryModal(null,id(el.dataset.course));break;
  case 'edit-history':openHistoryModal(app.state.history.find(h=>h.id===ident));break;
  case 'delete-history':if(confirm('Excluir este registro do histórico?'))api('/api/history/'+ident,'DELETE').then(refresh).catch(err=>notify(err.message));break;
  case 'new-priority':openPriorityModal();break;
  case 'toggle-priority':{const t=app.state.priorities.find(x=>x.id===ident);if(t)api('/api/priorities/'+ident,'PATCH',{...t,done:!t.done}).then(refresh).catch(err=>notify(err.message));break}
  case 'delete-priority':if(confirm('Excluir prioridade?'))api('/api/priorities/'+ident,'DELETE').then(refresh).catch(err=>notify(err.message));break;
  case 'new-event':openEventModal();break;
  case 'delete-event':if(confirm('Remover este estudo do calendário?'))api('/api/events/'+ident,'DELETE').then(refresh).catch(err=>notify(err.message));break;
  case 'month-prev':app.calendarMonth=new Date(app.calendarMonth.getFullYear(),app.calendarMonth.getMonth()-1,1);render();break;
  case 'month-next':app.calendarMonth=new Date(app.calendarMonth.getFullYear(),app.calendarMonth.getMonth()+1,1);render();break;
  case 'select-day':app.calendarDay=el.dataset.date;render();break;
  case 'timer-start':api('/api/timer/start','POST',{course_id:id($('#timer-course')?.value)||app.timerSnapshot?.course_id}).then(async t=>{app.timerSnapshot=t;app.timerLoadedAt=Date.now();render()}).catch(err=>notify(err.message));break;
  case 'timer-pause':api('/api/timer/pause','POST',{}).then(t=>{app.timerSnapshot=t;app.timerLoadedAt=Date.now();render()}).catch(err=>notify(err.message));break;
  case 'timer-stop':api('/api/timer/stop','POST',{}).then(t=>{app.timerSnapshot=t;app.timerLoadedAt=Date.now();render()}).catch(err=>notify(err.message));break;
  case 'backup-export':window.location.href='/api/backup';notify('Backup manual solicitado.');break;
  case 'backup-restore':restoreBackup().catch(err=>notify(err.message));break;
  case 'retry-load':window.location.reload();break;
  case 'voice-info':alert('Os comandos escritos já funcionam. A IA local pode ser instalada em Configurações; a ativação por voz “Ei, Máquina!” será implementada depois.');break;
  case 'close-modal':closeModal();break;
 }}
async function handleCommand(form){const text=new FormData(form).get('command');if(!String(text||'').trim()||app.aiBusy)return;
 app.aiBusy=true;app.assistantReply='Processando comando local... Se for a primeira pergunta à IA, o modelo precisa iniciar.';render();
 try{const result=await api('/api/commands','POST',{text:String(text)});app.assistantReply=result.message;if(result.changed){await load();}if(result.navigate){goto(result.navigate);notify(result.message)}else render();if(result.mode==='ai'){try{app.aiStatus=await api('/api/ai/status')}catch{}}}
 catch(err){app.assistantReply='Não consegui processar o comando: '+err.message;render();notify(err.message)}
 finally{app.aiBusy=false}
}
// ---------- Eventos de interação ----------
document.addEventListener('click',ev=>{const p=ev.target.closest('[data-page]');if(p){ev.preventDefault();goto(p.dataset.page);return}
 const b=ev.target.closest('[data-action]');if(b){ev.preventDefault();try{runAction(b)}catch(err){notify(err.message)}}});
document.addEventListener('submit',ev=>{if(ev.target.id==='command-form'){ev.preventDefault();handleCommand(ev.target)}
 else if(ev.target.id==='modal-form'){ev.preventDefault();submitModal(ev.target).catch(err=>notify(err.message))}});
document.addEventListener('change',ev=>{
 if(ev.target.id==='theme-select')api('/api/settings','POST',{theme:ev.target.value}).then(refresh).catch(err=>notify(err.message));
 if(ev.target.id==='course-status-filter'){app.courseFilter=ev.target.value;render()}
 if(ev.target.id==='note-file')saveImage(ev.target.files?.[0]).catch(err=>notify(err.message));
 if(['note-course','note-lesson','note-folder'].includes(ev.target.id))queueSave();
});
document.addEventListener('input',ev=>{if(['note-title','note-content','note-lesson'].includes(ev.target.id))queueSave()});
document.addEventListener('paste',ev=>{
 if(!ev.target.closest('#note-content'))return;
 const file=[...(ev.clipboardData?.items||[])].filter(x=>x.kind==='file'&&x.type.startsWith('image/'))[0]?.getAsFile();
 if(file){ev.preventDefault();saveImage(file).catch(err=>notify(err.message));return}
 if(ev.clipboardData?.types?.includes('text/html')){
   ev.preventDefault();
   document.execCommand('insertText',false,ev.clipboardData.getData('text/plain'));
   queueSave();
 }
});
document.addEventListener('keydown',ev=>{if(ev.key==='Escape')closeModal();if((ev.ctrlKey||ev.metaKey)&&ev.key==='s'&&app.page==='note'){ev.preventDefault();saveNote().then(ok=>notify(ok?'Anotação salva.':'Informe o título da anotação.')).catch(err=>notify(err.message))}});
$('#modal').addEventListener('click',ev=>{if(ev.target.id==='modal')closeModal()});
setInterval(()=>{if(app.page==='timer'&&$('#timer-digits'))$('#timer-digits').textContent=formatSeconds(displaySeconds())},300);
setInterval(async()=>{if(app.page!=='timer')return;try{app.timerSnapshot=await api('/api/timer');app.timerLoadedAt=Date.now()}catch{/* servidor indisponível */}},15000);
function checkReminders(){if(!app.state)return;const n=new Date(),stamp=nowLocal()+' '+String(n.getHours()).padStart(2,'0')+':'+String(n.getMinutes()).padStart(2,'0');for(const ev of app.state.events){if(ev.done||`${ev.event_date} ${ev.event_time}`!==stamp)continue;const key='reminder-'+ev.id+'-'+stamp;if(sessionStorage.getItem(key))continue;sessionStorage.setItem(key,'1');notify('Estudo agendado: '+ev.title);if('Notification' in window&&Notification.permission==='granted')new Notification('Ei, Máquina!',{body:ev.title})}}
setInterval(checkReminders,30000);
(async()=>{try{await load();render();checkReminders()}catch(err){$('#view').innerHTML=`<div class="card"><h2>Não foi possível carregar o aplicativo.</h2><p>${e(err.message)}</p><button class="primary" data-action="retry-load">Tentar novamente</button></div>`}})();
