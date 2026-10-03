"""Real manager browser controls never infer authorization from a backup list."""
from pathlib import Path
import subprocess
import pytest


@pytest.mark.parametrize('case',['disabled','missing_recovery','stale','changed_checksum','conflict','publish','cancel','rollback','rollback_cancel','edit'])
def test_operator_controls(case):
    page=Path(__file__).resolve().parents[1]/'docs/data-manager.html'
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[1],'utf8'),scenario=process.argv[2];
assert(html.includes('id="salaryPublish" disabled'));
const checksum='a'.repeat(64),elements={};
const get=id=>elements[id]||(elements[id]={value:'',textContent:'',disabled:false});
get('salaryChecksum').value=checksum;
let calls=[];
const context={working:false,Date,$:get,
 publicationState:{ready:true,publication_enabled:true},
 salaryReview:{checksum,newRows:1,duplicates:0,protected:0,at:Date.now()},
 salaryChecksum:()=>get('salaryChecksum').value,standalone:work=>work(),confirm:()=>true,
 prompt:()=>scenario==='cancel'||scenario==='rollback_cancel'?'wrong':scenario==='rollback'?'REVERTER '+checksum:checksum,
 admin:async(action,payload)=>{calls.push({action,payload});return {status:action==='bulk-publish'?'published':'rolled_back',inserted_rows:1,removed_rows:1,backup_id:'backup-isolated'}}};
vm.createContext(context);
const code='function updatePublicationButtons(){'+html.split('function updatePublicationButtons(){')[1].split('$("inventory").onclick=')[0];
vm.runInContext(code,context);
if(scenario==='disabled')context.publicationState.publication_enabled=false;
if(scenario==='missing_recovery')context.publicationState.ready=false;
if(scenario==='stale')context.salaryReview.at=0;
if(scenario==='changed_checksum')get('salaryChecksum').value='b'.repeat(64);
if(scenario==='conflict')context.salaryReview.protected=1;
context.updatePublicationButtons();
(async()=>{
 if(['disabled','missing_recovery','stale','changed_checksum','conflict'].includes(scenario)){
  assert(get('salaryPublish').disabled);try{await get('salaryPublish').onclick()}catch(e){};assert(calls.length===0);
 }else if(scenario==='edit'){
  get('salaryChecksum').oninput();assert(context.salaryReview===null && get('salaryPublish').disabled);
 }else{
  assert(!get('salaryPublish').disabled);
  if(scenario.startsWith('rollback'))await get('salaryRollback').onclick();else await get('salaryPublish').onclick();
  if(scenario==='cancel'||scenario==='rollback_cancel')assert(calls.length===0);
  else{
   assert(calls.length===1 && calls[0].payload.checksum===checksum);
   assert(calls[0].payload.confirm===(scenario==='rollback'?'rollback_reviewed_salary_package':'publish_reviewed_salary_package'));
  }
 }
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result=subprocess.run(['node','-e',script,str(page),case],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
