"""Run the real browser export function with isolated DOM/network doubles."""
from pathlib import Path
import subprocess
import pytest

PAGE=Path(__file__).resolve().parents[1]/'docs/data-manager.html'


@pytest.mark.parametrize('scenario',['success','unauthorized','storage','invalid','partial','network','timeout','missing_token','not_installed','cancel'])
def test_browser_download_and_portuguese_errors(scenario):
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[1],'utf8'),scenario=process.argv[2];
assert(html.includes('Exportar inventário salarial'));
assert(html.includes('id="deployApi"') && html.includes('id="backup"'));
const code='async function exportSalaryInventory(){'+html.split('async function exportSalaryInventory(){')[1].split('$("salaryInventory").onclick=')[0];
const elements={token:{value:'isolated-ui-administrator-'+'x'.repeat(32)},salaryInventoryResult:{textContent:''},salaryInventory:{}};
if(scenario==='missing_token')elements.token.value='';
let clicks=0,requests=0,logs=[],revoked=0;
const headers={'Content-Type':'application/zip','Content-Length':'30',
 'X-EarnWage-Inventory-SHA256':'a'.repeat(64),
 'Content-Disposition':'attachment; filename="earnwage-salary-inventory-20261003T000000Z.zip"'};
const response={ok:true,headers:{get:n=>headers[n]||null},blob:async()=>({size:30})};
if(scenario==='unauthorized'){response.ok=false;response.status=401;response.json=async()=>({error:'unauthorized'});}
if(scenario==='not_installed'){response.ok=false;response.status=404;response.json=async()=>({});}
if(scenario==='storage'){response.ok=false;response.status=503;response.json=async()=>({message:'Sem espaço para o inventário privado.'});}
if(scenario==='invalid')headers['Content-Type']='application/json';
if(scenario==='partial')response.blob=async()=>({size:29});
const context={API:'https://earnwage-api.example.test',$:id=>elements[id],
 working:false,confirm:()=>scenario!=='cancel',standalone:work=>work(),
 AbortController,setTimeout:()=>1,clearTimeout:()=>{},
 URL:{createObjectURL:()=> 'blob:private-inventory',revokeObjectURL:()=>revoked++},
 document:{body:{append:()=>{}},createElement:()=>({click:()=>clicks++,remove:()=>{}})},
 log:t=>logs.push(t),report:()=>{},fetch:async(url,options)=>{
 requests++;assert(url.endsWith('/v1/admin/data-manager/salary-inventory'));
 assert(options.method==='POST' && options.cache==='no-store');
 assert(options.headers['X-EarnWage-Admin-Token']===elements.token.value);
 assert.deepStrictEqual(JSON.parse(options.body),{confirm:'export_read_only_salary_inventory'});
 if(scenario==='network')throw new TypeError('Failed to fetch');
 if(scenario==='timeout'){const e=new Error('aborted');e.name='AbortError';throw e;}
 return response;
 }};
vm.createContext(context);vm.runInContext(code,context);
const binding='$("salaryInventory").onclick='+html.split('$("salaryInventory").onclick=')[1].split('$("backup").onclick=')[0];
vm.runInContext(binding,context);
(async()=>{
 if(scenario==='cancel'){
  await elements.salaryInventory.onclick();assert(requests===0 && clicks===0);return;
 }
 let failure;try{await context.exportSalaryInventory()}catch(e){failure=e;}
 assert(requests===(scenario==='missing_token'?0:1));
 if(scenario==='success'){
  assert(!failure && clicks===1);assert(elements.salaryInventoryResult.textContent.includes('descarga iniciada'));
  assert(logs.every(l=>!l.includes(elements.token.value)));
 }else{
  assert(failure && clicks===0);const text=elements.salaryInventoryResult.textContent;
  assert(text.startsWith('Inventário NÃO exportado:'));
  const expected={unauthorized:'chave de administração',storage:'Sem espaço',invalid:'ZIP de inventário válido',
    partial:'incompleta',network:'Não foi possível contactar',timeout:'demorou demasiado',missing_token:'chave de administração',not_installed:'ainda não suporta'};
  assert(text.includes(expected[scenario]),text);
  if(elements.token.value)assert(!text.includes(elements.token.value));
 }
})().catch(e=>{console.error(e.message);process.exitCode=1});
'''
    result=subprocess.run(['node','-e',script,str(PAGE),scenario],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
