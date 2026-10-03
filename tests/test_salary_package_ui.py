"""Browser package upload hashes original bytes and never requests publication."""
from pathlib import Path
import subprocess
import pytest


@pytest.mark.parametrize('scenario',['success','hash','extension','size','token','server','preview'])
def test_browser_salary_intake(scenario):
    page=Path(__file__).resolve().parents[1]/'docs/data-manager.html'
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert'),crypto=require('crypto').webcrypto;
const html=fs.readFileSync(process.argv[1],'utf8'),scenario=process.argv[2];
const raw=new TextEncoder().encode('{"schema":"test"}\n');
(async()=>{
const sha=Buffer.from(await crypto.subtle.digest('SHA-256',raw)).toString('hex');
const elements={token:{value:'x'.repeat(40)},salaryChecksum:{value:scenario==='hash'?'a'.repeat(64):sha},
 salaryFile:{files:[{name:scenario==='extension'?'file.zip':'file.json',size:scenario==='size'?3*1024*1024:raw.length,arrayBuffer:async()=>raw.buffer}]},
 salaryResult:{textContent:''},salarySafety:{textContent:''}};
if(scenario==='token')elements.token.value='';
let requests=0;
const context={crypto,Uint8Array,API:'https://isolated.test',$:id=>elements[id],
 fetch:async(url,options)=>{requests++;assert(url.endsWith('/salary-upload'));assert(options.body===raw.buffer);
 assert(options.headers['X-EarnWage-Package-SHA256']===sha);
 return {ok:scenario!=='server',status:422,json:async()=>scenario==='server'?{message:'Pacote recusado'}:
 {checksum:sha,observations:12,target_rows:1}};},
 admin:async(action,payload)=>{assert(action==='bulk-preview' && payload.checksum===sha);return {
 status:'review_required',checksum:sha,inserted_rows:1,duplicate_rows:0,protected_existing_rows:0,
 publication_enabled:false,backups:['backup-one'],backup_readiness:{ready:true}};}};
vm.createContext(context);
const code='function salaryChecksum(){'+html.split('function salaryChecksum(){')[1].split('$("salaryUpload").onclick=')[0];
vm.runInContext(code,context);
let error;
try{if(scenario==='preview')await context.previewSalaryPackage();else await context.uploadSalaryPackage()}catch(e){error=e}
if(scenario==='success')assert(!error && requests===1 && elements.salaryResult.textContent.includes('12 medidas'));
else if(scenario==='preview'){
 assert(!error && requests===0 && elements.salaryResult.textContent.includes('Registos novos: 1'));
 assert(elements.salarySafety.textContent.includes('não comprova recuperação'));
}else{assert(error);assert(requests===(scenario==='server'?1:0));}
assert(!code.includes('bulk-publish'));
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result=subprocess.run(['node','-e',script,str(page),scenario],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
