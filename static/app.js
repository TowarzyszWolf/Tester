const $ = s => document.querySelector(s);
let pending = [];
const localDate = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
$('#manual-form input[type=date]').value = localDate();
const extraTests = ['OpenGL', 'Shading (CINEMA 4D)', 'OpenGL Software Lighting', 'OpenGL Hardware Lighting', 'OpenGL Standard'];
for (const select of document.querySelectorAll('select[name=test]')) for (const value of extraTests) select.add(new Option(value, value));
for (const select of document.querySelectorAll('select[name=unit]')) for (const value of ['CB-CPU','CB-GFX']) select.add(new Option(value, value));
function message(text, error=false) { $('#message').textContent=text; $('#message').className=error?'error':''; }
async function api(path, options={}) {
  const response=await fetch(path,{...options,headers:{'X-Cinebench-Client':'1',...options.headers}});
  const body=await response.json(); if(!response.ok) throw new Error(body.error||'Błąd zapisu.'); return body;
}
function node(tag, text, className) {const el=document.createElement(tag);el.textContent=text;if(className)el.className=className;return el;}
function cell(row, primary, secondary, cls) {const td=node('td','',cls);td.append(node('strong',primary));if(secondary)td.append(node('small',secondary));row.append(td);}
async function load() {
  const params=new URLSearchParams(new FormData($('#filters')));
  const rows=await api('/api/results?'+params);$('#count').textContent=rows.length;$('#export').href='/api/export.csv?'+params;
  const table=$('#results');table.replaceChildren();
  if(!rows.length){const tr=node('tr','');const td=node('td','Brak wyników. Zaimportuj plik lub dodaj pierwszy pomiar.','empty');td.colSpan=6;tr.append(td);table.append(tr);}
  for(const r of rows){const tr=node('tr','');cell(tr,r.edition,[r.test,r.benchmark_version].filter(Boolean).join(' · '));cell(tr,Number(r.score).toLocaleString('pl-PL',{maximumFractionDigits:6}),r.unit,'score');cell(tr,r.cpu,[r.system_name,r.gpu,r.cores?`${r.cores} rdzeni`:'',r.threads?`${r.threads} wątków`:'',r.clock_mhz?`${r.clock_mhz} MHz`:'',r.architecture].filter(Boolean).join(' · '));cell(tr,r.measured_at||'Data nieznana',r.os);cell(tr,r.source_file,r.notes,'notes');const td=node('td','');const b=node('button','Usuń','delete');b.type='button';b.addEventListener('click',async()=>{if(!confirm(`Usunąć wynik ${r.edition}: ${r.score} ${r.unit}?`))return;try{await api('/api/results/'+r.id,{method:'DELETE'});await load();message('Wynik usunięty.');}catch(e){message(e.message,true);}});td.append(b);tr.append(td);table.append(tr);}
}
async function busy(form, action) {const buttons=[...form.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);try{await action();}catch(e){message(e.message,true);}finally{buttons.forEach(b=>b.disabled=false);}}
$('#filters').addEventListener('submit',e=>{e.preventDefault();load().catch(e=>message(e.message,true));});
$('#manual-form').addEventListener('submit',e=>{e.preventDefault();busy(e.target,async()=>{await api('/api/results',{method:'POST',body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});await load();message('Wynik zapisany.');});});
let selection = 0;
$('#report-file').addEventListener('change',async e=>{
  const generation = ++selection;
  pending=[];$('#import-form').hidden=true;
  const files=[...e.target.files];if(!files.length)return;
  if(files.length>100){message('Wybierz maksymalnie 100 plików jednocześnie.',true);return;}
  $('#file-name').textContent=`Wybrano plików: ${files.length}`;
  const rows=[], info=[];
  for(const file of files){
    try{
      if(file.size>2097152)throw new Error('Limit pliku to 2 MB.');
      const parsed=await api('/api/parse',{method:'POST',body:file});
      rows.push(...parsed.map(row=>({...row,source_file:file.name})));
      info.push(`${file.name}: ${parsed.length ? parsed.length+' wyników' : 'brak wykonanych pomiarów — pominięto'}`);
    }catch(error){info.push(`${file.name}: BŁĄD — ${error.message}`);}
    if(generation!==selection)return;
  }
  pending=rows;
  const preview=$('#preview');preview.replaceChildren();
  for(const r of pending)preview.append(node('p',`${r.source_file} · ${r.edition||'Wersja do uzupełnienia'} · ${r.test} · ${r.score} ${r.unit||'(jednostka do uzupełnienia)'} · ${r.cpu||'procesor do uzupełnienia'}`));
  $('#import-form').hidden=!pending.length;
  message(`Odczytano wyników: ${pending.length}. Sprawdź podgląd. Brak daty w pliku oznacza datę nieznaną, chyba że ją uzupełnisz.\n`+info.join('\n'));
});
$('#cancel-import').addEventListener('click',()=>{selection++;pending=[];$('#import-form').hidden=true;$('#report-file').value='';message('Import anulowany.');});
$('#import-form').addEventListener('submit',e=>{e.preventDefault();busy(e.target,async()=>{const defaults=Object.fromEntries(new FormData(e.target));const rows=pending.map(row=>{const merged={...defaults};for(const [k,v] of Object.entries(row))if(v!==''&&v!==null)merged[k]=v;return merged;});const result=await api('/api/import-results',{method:'POST',body:JSON.stringify(rows)});pending=[];e.target.hidden=true;$('#report-file').value='';await load();message(`Zapisano wyników: ${result.added}.`);});});
$('#csv-file').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>2097152)throw new Error('Limit pliku to 2 MB.');const result=await api('/api/import',{method:'POST',body:file});await load();message(`Zaimportowano wyników: ${result.added}.`);}catch(e){message(e.message,true);}finally{e.target.value='';}});
load().catch(e=>message(e.message,true));
