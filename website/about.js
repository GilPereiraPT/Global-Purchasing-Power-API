"use strict";
const $=id=>document.getElementById(id);
const LANGS=["en","pt","es","de","fr","it","nl"];
const loc={en:"en-GB",pt:"pt-PT",es:"es-ES",de:"de-DE",fr:"fr-FR",it:"it-IT",nl:"nl-NL"};
const saved=(()=>{try{return localStorage.getItem("earnwage_lang")}catch(_){return null}})();
let lang=LANGS.includes(saved)?saved:LANGS.includes((navigator.language||"").slice(0,2).toLowerCase())?navigator.language.slice(0,2).toLowerCase():"en";
const T=k=>window.EarnWageAboutI18n?.[lang]?.[k]||window.EarnWageAboutI18n?.en?.[k]||k;
const N=k=>window.EarnWageExploreI18n?.[lang]?.[k]||window.EarnWageExploreI18n?.en?.[k]||k;
let captchaId=null;let submitting=false;
function applyLanguage(){
 document.querySelectorAll("[data-method-link]").forEach(el=>el.textContent=({en:"Methodology",pt:"Metodologia",es:"Metodología",de:"Methodik",fr:"Méthodologie",it:"Metodologia",nl:"Methodologie"})[lang]);
 document.querySelectorAll("[data-sources-link]").forEach(el=>el.textContent=({en:"Data sources",pt:"Fontes de dados",es:"Fuentes de datos",de:"Datenquellen",fr:"Sources de données",it:"Fonti dei dati",nl:"Gegevensbronnen"})[lang]);
 document.documentElement.lang=loc[lang];$("lang").value=lang;$("lang").setAttribute("aria-label",T("language"));
 document.querySelectorAll("[data-a]").forEach(el=>el.textContent=T(el.dataset.a));
 document.querySelectorAll("[data-t]").forEach(el=>el.textContent=N(el.dataset.t));
 document.title=T("eyebrow")+" — EarnWage";
}
function status(key){$("reportStatus").textContent=T(key)}
async function setupCaptcha(){
 const siteKey=window.EarnWageReportConfig?.turnstileSiteKey||"";
 if(!/^[A-Za-z0-9_-]{12,128}$/.test(siteKey)){status("configured");return}
 $("captchaContainer").hidden=false;
 try{
  await new Promise((resolve,reject)=>{
   const script=document.createElement("script");script.src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";script.async=true;script.defer=true;
   script.onload=resolve;script.onerror=()=>reject(new Error("captcha unavailable"));document.head.append(script);
  });
  if(!window.turnstile)throw Error("captcha unavailable");
  captchaId=window.turnstile.render("#captchaContainer",{sitekey:siteKey,callback:()=>{$("sendReport").disabled=false}, "expired-callback":()=>{$("sendReport").disabled=true}});
 }catch(_){status("failure")}
}
async function submit(event){
 event.preventDefault();
 if(submitting||captchaId===null||!window.turnstile)return;
 const token=window.turnstile.getResponse(captchaId);
 if(!token||!$("consent").checked)return;
 const form=$("reportForm");if(!form.reportValidity())return;
 submitting=true;$("sendReport").disabled=true;status("sending");
 const payload={name:$("reportName").value.trim(),email:$("reportEmail").value.trim(),type:$("reportType").value,page:$("reportPage").value.trim(),message:$("reportMessage").value.trim(),source_url:$("reportSource").value.trim(),consent:true,website:$("reportWebsite").value,turnstile_token:token};
 try{
  const response=await fetch("./api/report",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  const result=await response.json().catch(()=>({}));
  if(!response.ok||result.status!=="sent")throw Error("send failed");
  form.reset();status("success");
 }catch(_){status("failure")}
 finally{submitting=false;window.turnstile.reset(captchaId);$("sendReport").disabled=true}
}
$("lang").addEventListener("change",event=>{lang=event.target.value;try{localStorage.setItem("earnwage_lang",lang)}catch(_){}applyLanguage()});
$("reportForm").addEventListener("submit",submit);
const params=new URLSearchParams(location.search);
if(params.get("page")?.startsWith("https://"))$("reportPage").value=params.get("page").slice(0,500);
applyLanguage();setupCaptcha();
