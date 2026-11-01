const $ = s => document.querySelector(s);
const metrics = {cpu_single:'CPU Single Core',cpu_multi:'CPU Multi Core',gpu_score:'GPU',opengl:'OpenGL',shading:'Shading (CINEMA 4D)',opengl_software:'OpenGL Software Lighting',opengl_hardware:'OpenGL Hardware Lighting',opengl_standard:'OpenGL Standard'};
const formatScore = value => value===null || value===undefined || value==='' ? '—' : Number(value).toLocaleString('pl-PL',{minimumFractionDigits:2,maximumFractionDigits:2});
const hardwareInfo = report => (report.system_name||'').trim() || 'brak informacji';
let pending=[],readErrors=[],selection=0,readController=null,loadGeneration=0;
const d=new Date();$('#manual-form input[type=date]').value=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
$('#include-gpu').addEventListener('change',e=>{const box=$('#manual-gpu');box.hidden=!e.target.checked;box.querySelectorAll('input,select').forEach(el=>el.disabled=!e.target.checked);});
function message(text,error=false){$('#message').textContent=text;$('#message').className=error?'error':'';}
async function api(path,options={}){const response=await fetch(path,{...options,headers:{'X-Cinebench-Client':'1',...options.headers}});const body=await response.json();if(!response.ok)throw new Error(body.error||'Błąd operacji.');return body;}
function node(tag,text,cls){const el=document.createElement(tag);el.textContent=text;if(cls)el.className=cls;return el;}
function cell(row,primary,secondary,cls){const td=node('td','',cls);td.append(node('strong',primary||'—'));if(secondary)td.append(node('small',secondary));row.append(td);}
for(const [key,label] of Object.entries(metrics)){
  const th=node('th','');const b=node('button',label,'sort-header');b.type='button';b.addEventListener('click',()=>{const f=$('#filters');f.elements.direction.value=f.elements.sort.value===key && f.elements.direction.value==='desc'?'asc':'desc';f.elements.sort.value=key;load().catch(e=>message(e.message,true));});th.append(b);$('#table-head').insertBefore(th,$('#system-head'));
  $('#filters select[name=sort]').add(new Option(label,key));
}
for(const key of ['cpu','gpu'])$('#sort-'+key).addEventListener('click',()=>{const f=$('#filters');f.elements.direction.value=f.elements.sort.value===key&&f.elements.direction.value==='asc'?'desc':'asc';f.elements.sort.value=key;load().catch(e=>message(e.message,true));});
async function load(){
  const generation=++loadGeneration;
  const params=new URLSearchParams(new FormData($('#filters')));const [rows,status]=await Promise.all([api('/api/results?'+params),api('/api/status')]);if(generation!==loadGeneration)return;const grouped=params.get('group_by')!=='none';
  $('#empty-state').hidden=status.record_count!==0;
  $('#count').textContent=`${rows.length} ${grouped?'grup':'raportów'}`;$('#export').href='/api/export.csv?'+params;
  const table=$('#results');table.replaceChildren();
  if(!rows.length){const tr=node('tr','');const td=node('td','Brak raportów lub pomiarów spełniających wybrane filtry.','empty');td.colSpan=14;tr.append(td);table.append(tr);}
  for(const r of rows){
    const tr=node('tr','');modelCell(tr,'cpu',r.cpu,grouped&&r.group_by==='gpu'?'Średnie tylko testów graficznych':grouped?'':'Informacje o sprzęcie: '+hardwareInfo(r));modelCell(tr,'gpu',r.gpu,grouped&&r.group_by==='cpu'?'Średnie tylko testów CPU':'');cell(tr,r.edition,r.benchmark_version);
    for(const key of Object.keys(metrics))cell(tr,formatScore(r[key]),r[key]===null?'':`${r[key+'_unit']||''}${grouped?' · n='+r.counts[key]:''}`,'score');
    cell(tr,[r.os_name,r.os_version,r.os_build?'build '+r.os_build:''].filter(Boolean).join(' '),grouped?'Różne konfiguracje':r.os);cell(tr,grouped?`${r.report_count} raportów`:r.source_file,grouped?'Średnia arytmetyczna':r.measured_at||'Data nieznana','notes');
    const td=node('td','');
    if(!grouped){const b=node('button','Usuń raport','delete');b.type='button';b.addEventListener('click',async()=>{if(!confirm('Usunąć cały raport wraz ze wszystkimi wynikami?'))return;try{await api('/api/results/'+r.id,{method:'DELETE'});await load();message('Raport usunięty.');}catch(e){message(e.message,true);}});td.append(b);if(r.notes){const details=node('details','');details.append(node('summary','Szczegóły'),node('p',r.notes));td.append(details);}}
    tr.append(td);table.append(tr);
  }
  await Promise.all([loadRanking('cpu'),loadRanking('gpu'),$('#hardware-dialog').open&&activeHardware?loadHardware():Promise.resolve()]);
}
async function busy(form,action){const buttons=[...form.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);try{await action();}catch(e){message(e.message,true);}finally{buttons.forEach(b=>b.disabled=false);}}
$('#filters').addEventListener('submit',e=>{e.preventDefault();load().catch(e=>message(e.message,true));});$('#filters').querySelectorAll('select').forEach(el=>el.addEventListener('change',()=>load().catch(e=>message(e.message,true))));
$('#manual-form').addEventListener('submit',e=>{e.preventDefault();busy(e.target,async()=>{await api('/api/results',{method:'POST',body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});await load();message('Zapisano jeden raport ze wszystkimi podanymi wynikami.');});});
function activity(text,value,max,reading=false){
  $('#import-activity').hidden=false;$('#import-status').textContent=text;
  $('#import-progress').max=Math.max(1,max);$('#import-progress').value=value;
  $('#cancel-reading').hidden=!reading;
}
function renderPending(){
  const preview=$('#preview');preview.replaceChildren();
  for(const r of pending){
    const entry=node('div','','preview-entry');
    entry.append(node('strong',`${r.edition||'Wersja do uzupełnienia'} / ${r.benchmark_version||'—'} · ${r.cpu||'CPU do uzupełnienia'}`));
    entry.append(node('p',Object.entries(metrics).filter(([key])=>r[key]!==undefined&&r[key]!==null&&r[key]!=='').map(([key,label])=>`${label}: ${formatScore(r[key])} ${r[key+'_unit']||''}`).join(' · ')||'Brak wykonanych testów — zapisany zostanie raport bez pomiarów.'));
    entry.append(node('p',`GPU: ${r.gpu||'nie podano (opcjonalne)'} · System: ${r.os||'nieznany'}`),node('p','Informacje o sprzęcie: '+hardwareInfo(r)),node('small',r.source_file));
    if(r._error)entry.append(node('p',r._error,'import-error'));
    preview.append(entry);
  }
  $('#import-form').hidden=!pending.length;
}
$('#first-import').addEventListener('click',()=>$('#report-file').click());
$('#report-file').addEventListener('change',async e=>{
  const generation=++selection;readController?.abort();readController=new AbortController();
  pending=[];readErrors=[];$('#import-form').hidden=true;const files=[...e.target.files];
  if(!files.length){$('#import-activity').hidden=true;return;}
  if(files.length>500){message('Wybierz do 500 plików naraz.',true);$('#import-activity').hidden=true;return;}
  $('#file-name').textContent=`Wybrano plików: ${files.length}`;const rows=[],info=[];let done=0;
  for(const file of files){
    activity(`Odczyt ${done+1}/${files.length}: ${file.name}`,done,files.length,true);
    try{
      if(file.size>2097152)throw new Error('Limit jednego pliku to 2 MB.');
      const parsed=await api('/api/parse',{method:'POST',body:file,signal:readController.signal});
      if(parsed.length!==1)throw new Error('Plik musi zawierać jeden raport.');
      const row={...parsed[0],source_file:file.name,_token:crypto.randomUUID()};rows.push(row);
      info.push(`${file.name}: odczytano 1 rekord`);
    }catch(error){if(generation!==selection)return;const issue=`${file.name}: BŁĄD — ${error.message}`;readErrors.push(issue);info.push(issue);}
    if(generation!==selection)return;done++;
  }
  pending=rows;renderPending();
  for(const key of ['edition','benchmark_version','os','cpu','gpu']){
    const input=$('#import-form').elements.namedItem(key);const values=[...new Set(pending.map(row=>String(row[key]||'')))];input.value=values.length===1?values[0]:'';
  }
  activity(`Odczyt zakończony: ${pending.length} poprawnych plików, ${files.length-pending.length} błędów.`,files.length,files.length);
  message(`Przygotowano rekordów: ${pending.length}. Jeden plik = jeden rekord. Sprawdź podgląd i zapisz.\n`+info.join('\n'));
});
function cancelImport(){selection++;readController?.abort();pending=[];readErrors=[];$('#import-form').hidden=true;$('#import-activity').hidden=true;$('#report-file').value='';message('Import anulowany. Niczego nie zapisano.');}
$('#cancel-reading').addEventListener('click',cancelImport);$('#cancel-import').addEventListener('click',cancelImport);
function chunks(items){
  const output=[];let chunk=[],bytes=2;
  for(const item of items){const size=new TextEncoder().encode(JSON.stringify(item)).length+1;
    if(chunk.length && (chunk.length>=25 || bytes+size>512000)){output.push(chunk);chunk=[];bytes=2;}
    chunk.push(item);bytes+=size;
  }
  if(chunk.length)output.push(chunk);return output;
}
$('#import-form').addEventListener('submit',e=>{
  e.preventDefault();const form=e.target;
  busy(form,async()=>{
    const defaults=Object.fromEntries(new FormData(form));
    const batches=chunks(pending.map(row=>{
      const record={...defaults};
      for(const [key,value] of Object.entries(row))if(!key.startsWith('_')&&value!==''&&value!==null)record[key]=value;
      for(const key of Object.keys(metrics))if(record[key]!==undefined&&record[key]!==null&&record[key]!==''&&!record[key+'_unit'])record[key+'_unit']=defaults.unit;
      delete record.unit;return {token:row._token,record};
    }));
    const fields=[...form.querySelectorAll('input,select')];fields.forEach(el=>el.disabled=true);$('#report-file').disabled=true;
    const total=pending.length;let done=0,saved=0,already=0,failed=0,interrupted='';const info=[];
    try{
      for(const batch of batches){
        activity(`Zapisywanie: ${done}/${total} plików`,done,total);
        let result;
        try{result=await api('/api/import-batch',{method:'POST',body:JSON.stringify(batch)});}
        catch(error){interrupted=error.message;break;}
        for(const outcome of result.items){
          const row=pending.find(r=>r._token===outcome.token);if(!row)continue;
          if(outcome.status==='error'){row._error=outcome.error;failed++;info.push(`${row.source_file}: ${outcome.error}`);}
          else{pending=pending.filter(r=>r._token!==outcome.token);if(outcome.status==='saved')saved++;else already++;}
        }
        done+=batch.length;
      }
    }finally{fields.forEach(el=>el.disabled=false);$('#report-file').disabled=false;renderPending();}
    activity(`Zapisano: ${saved}. Już zapisane: ${already}. Błędy: ${failed}. Pozostało: ${pending.length}.`,done,total);
    if(!pending.length)$('#report-file').value='';
    await load();
    message(`Zapisano raportów: ${saved}. Już zapisane: ${already}. Błędy: ${failed}.`+(interrupted?'\nPrzerwano zapis: '+interrupted+' Ponów zapis pozostałych plików.':'')+(pending.length?'\nPopraw brakujące dane i ponów zapis. Zapisane raporty nie będą powielane.':'')+(info.length?'\n'+info.join('\n'):'')+(readErrors.length?'\nPominięte pliki z błędami odczytu: '+readErrors.length+'\n'+readErrors.join('\n'):''),Boolean(failed||interrupted||readErrors.length));
  });
});
$('#csv-file').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>2097152)throw new Error('Limit pliku to 2 MB.');const result=await api('/api/import',{method:'POST',body:file});await load();message(`Zaimportowano raportów: ${result.added}.`);}catch(e){message(e.message,true);}finally{e.target.value='';}});

const rankingViews={cpu:{params:{},generation:0},gpu:{params:{},generation:0}};
let activeHardware=null,hardwareGeneration=0;
function hardwareButton(device,model){
  const button=node('button',model,'model-link');button.type='button';button.title='Wszystkie zapisane raporty tego modelu ze wszystkich wersji Cinebench';
  button.addEventListener('click',()=>openHardware(device,model));return button;
}
function modelCell(row,device,model,secondary){const td=node('td','');if(model)td.append(hardwareButton(device,model));else td.append(node('strong','—'));if(secondary)td.append(node('small',secondary));row.append(td);}
for(const device of ['cpu','gpu']){
  const form=$('#ranking-'+device+'-filters');
  for(const [key,title] of [['edition','Edycja Cinebench'],['metric','Rodzaj testu'],['manufacturer','Producent'],['sort','Sortowanie']]){
    const label=node('label',title);const select=document.createElement('select');select.name=key;label.append(select);form.append(label);
    select.addEventListener('change',()=>{
      const state=rankingViews[device];state.params={...state.params,[key]:select.value};
      if(key==='edition')delete state.params.metric;
      loadRanking(device);
    });
  }
  form.addEventListener('submit',e=>e.preventDefault());
}
function rankingOptions(select,values,selected,label){
  select.replaceChildren();
  if(!values.length)select.add(new Option('Brak pomiarów',''));
  for(const value of values)select.add(new Option(label?label(value):(value||'Nie podano'),value));
  if(values.length && !values.includes(selected))select.add(new Option((label?label(selected):selected||'Nie podano')+' — brak wyników',selected));
  select.value=selected;select.disabled=!values.length;
}
async function loadRanking(device){
  const state=rankingViews[device],generation=++state.generation;
  const status=$('#ranking-'+device+'-status');
  try{
    const data=await api('/api/rankings?'+new URLSearchParams({device,...state.params}));if(generation!==state.generation)return;
    state.params=data.editions.length?{...data.selected}:{sort:data.selected.sort,manufacturer:data.selected.manufacturer};
    const form=$('#ranking-'+device+'-filters');
    rankingOptions(form.elements.edition,data.editions,data.selected.edition);
    rankingOptions(form.elements.metric,data.metrics,data.selected.metric,key=>metrics[key]||key);
    const brand=form.elements.manufacturer;brand.replaceChildren(new Option('Wszyscy producenci',''));
    for(const name of data.manufacturers)brand.add(new Option(name,name));
    if(data.selected.manufacturer&&!data.manufacturers.includes(data.selected.manufacturer))brand.add(new Option(data.selected.manufacturer+' — brak wyników',data.selected.manufacturer));
    brand.value=data.selected.manufacturer;
    const sort=form.elements.sort;sort.replaceChildren();
    for(const [value,label] of [['score','Wynik malejąco'],['manufacturer_asc','Producent A–Z'],['manufacturer_desc','Producent Z–A']])sort.add(new Option(label,value));
    sort.value=data.selected.sort;
    const n=data.rows.length;$('#ranking-'+device+'-count').textContent=n+' '+(n===1?'model':n%10>=2&&n%10<=4&&(n%100<12||n%100>14)?'modele':'modeli');
    status.textContent=(data.rows.length?'Średnia z pomiarów całej edycji. Kliknij model, aby zobaczyć historię.':'Brak pomiarów w tym rankingu. Zaimportuj raport lub wybierz inną edycję/test/producenta.')+(data.excluded_unit_count?' Pominięto pomiary z niezgodną jednostką: '+data.excluded_unit_count+'.':'');
    const body=$('#ranking-'+device+'-rows');body.replaceChildren();
    for(const row of data.rows){const tr=node('tr','');cell(tr,String(row.rank));cell(tr,row.manufacturer,'','manufacturer');const model=node('td','');model.append(hardwareButton(device,row.model));tr.append(model);cell(tr,formatScore(row.score),data.unit,'score');cell(tr,String(row.count));body.append(tr);}
  }catch(error){if(generation===state.generation){status.textContent='Nie można odczytać rankingu: '+error.message;$('#ranking-'+device+'-rows').replaceChildren();}}
}
function openHardware(device,model){
  activeHardware={device,model};if(!$('#hardware-dialog').open)$('#hardware-dialog').showModal();loadHardware();
}
$('#close-hardware').addEventListener('click',()=>$('#hardware-dialog').close());
$('#hardware-dialog').addEventListener('close',()=>{activeHardware=null;hardwareGeneration++;});
async function loadHardware(){
  if(!activeHardware)return;
  const generation=++hardwareGeneration;const requested={...activeHardware};
  $('#hardware-title').textContent=requested.model;$('#hardware-kind').textContent=requested.device.toUpperCase()+' / WSZYSTKIE WERSJE CINEBENCH';
  $('#hardware-status').textContent='Wczytywanie zapisanych raportów…';$('#hardware-content').replaceChildren();
  try{
    const data=await api('/api/hardware?'+new URLSearchParams(requested));if(generation!==hardwareGeneration)return;
    $('#hardware-title').textContent=data.model;$('#hardware-status').textContent=`Raporty: ${data.record_count}. Producent: ${data.manufacturer}. Edycje: ${data.editions.join(', ')||'brak'}. Historia obejmuje wszystkie zapisane wersje, niezależnie od filtrów rankingu i archiwum.`;
    const content=$('#hardware-content');
    if(!data.reports.length){content.append(node('p','Nie ma już raportów tego modelu w bazie.'));return;}
    for(const edition of data.editions){
      const section=document.createElement('section');section.append(node('h3','Cinebench '+edition));
      const summaries=data.summaries.filter(r=>r.edition===edition);
      for(const summary of summaries)section.append(node('p',`${summary.benchmark_version||'Pełna wersja nieznana'} · ${metrics[summary.metric]}: średnio ${formatScore(summary.score)} ${summary.unit} · n=${summary.count}`));
      const wrap=node('div','','table-wrap'),table=document.createElement('table'),head=document.createElement('thead'),header=document.createElement('tr');
      for(const label of ['Pełna wersja',...Object.values(metrics),'CPU','GPU','Informacje o sprzęcie','System / data','Plik źródłowy'])header.append(node('th',label));
      head.append(header);table.append(head);const body=document.createElement('tbody');
      for(const report of data.reports.filter(r=>r.edition===edition)){
        const tr=node('tr','');cell(tr,report.benchmark_version);
        for(const key of Object.keys(metrics))cell(tr,formatScore(report[key]),report[key]===null?'':report[key+'_unit'],'score');
        cell(tr,report.cpu);cell(tr,report.gpu);cell(tr,hardwareInfo(report),'','notes');cell(tr,report.os,report.measured_at||'Data nieznana');
        const source=node('td','','notes');source.append(node('strong',report.source_file||'Raport ręczny'));
        if(report.notes){const details=node('details','');details.append(node('summary','Szczegóły'),node('p',report.notes));source.append(details);}tr.append(source);body.append(tr);
      }
      table.append(body);wrap.append(table);section.append(wrap);content.append(section);
    }
  }catch(error){if(generation===hardwareGeneration)$('#hardware-status').textContent='Nie można odczytać historii: '+error.message;}
}

load().catch(e=>message(e.message,true));
