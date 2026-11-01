const $ = s => document.querySelector(s);
const metrics = {cpu_single:'CPU Single Core',cpu_multi:'CPU Multi Core',gpu_score:'GPU',opengl:'OpenGL',shading:'Shading (CINEMA 4D)',opengl_software:'OpenGL Software Lighting',opengl_hardware:'OpenGL Hardware Lighting',opengl_standard:'OpenGL Standard'};
const formatScore = value => value===null || value===undefined || value==='' ? '—' : Number(value).toLocaleString('pl-PL',{minimumFractionDigits:2,maximumFractionDigits:2});
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
    const tr=node('tr','');cell(tr,r.cpu,grouped&&r.group_by==='gpu'?'Średnie tylko testów graficznych':r.system_name);cell(tr,r.gpu,grouped&&r.group_by==='cpu'?'Średnie tylko testów CPU':'');cell(tr,r.edition,r.benchmark_version);
    for(const key of Object.keys(metrics))cell(tr,formatScore(r[key]),r[key]===null?'':`${r[key+'_unit']||''}${grouped?' · n='+r.counts[key]:''}`,'score');
    cell(tr,[r.os_name,r.os_version,r.os_build?'build '+r.os_build:''].filter(Boolean).join(' '),grouped?'Różne konfiguracje':r.os);cell(tr,grouped?`${r.report_count} raportów`:r.source_file,grouped?'Średnia arytmetyczna':r.measured_at||'Data nieznana','notes');
    const td=node('td','');
    if(!grouped){const b=node('button','Usuń raport','delete');b.type='button';b.addEventListener('click',async()=>{if(!confirm('Usunąć cały raport wraz ze wszystkimi wynikami?'))return;try{await api('/api/results/'+r.id,{method:'DELETE'});await load();message('Raport usunięty.');}catch(e){message(e.message,true);}});td.append(b);if(r.notes){const details=node('details','');details.append(node('summary','Szczegóły'),node('p',r.notes));td.append(details);}}
    tr.append(td);table.append(tr);
  }
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
    entry.append(node('p',`GPU: ${r.gpu||'nie podano (opcjonalne)'} · System: ${r.os||'nieznany'}`),node('small',r.source_file));
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
load().catch(e=>message(e.message,true));
