"use strict";
const $=id=>document.getElementById(id),page=document.body.dataset.page;
const API="https://earnwage-api.policlinicosdesantoandre.com";
const tags={en:"en-GB",pt:"pt-PT",es:"es-ES",de:"de-DE",fr:"fr-FR",it:"it-IT",nl:"nl-NL"};
const saved=(()=>{try{return localStorage.getItem("earnwage_lang")}catch(_){return null}})();
let lang=Object.hasOwn(tags,saved)?saved:Object.hasOwn(tags,(navigator.language||"").slice(0,2).toLowerCase())?navigator.language.slice(0,2).toLowerCase():"en";
let catalogue=null,shown=null,sequence=0;
const T=k=>window.EarnWageLibraryI18n?.[lang]?.[k]||window.EarnWageLibraryI18n?.en?.[k]||k;
const N=k=>window.EarnWageExploreI18n?.[lang]?.[k]||window.EarnWageExploreI18n?.en?.[k]||k;
function el(tag,text,cls){const x=document.createElement(tag);if(text!==undefined)x.textContent=String(text);if(cls)x.className=cls;return x}
function opt(value,label){const x=el("option",label);x.value=value;return x}
function number(v){return new Intl.NumberFormat(tags[lang],{maximumFractionDigits:2}).format(v)}
function href(raw){if(typeof raw!=="string")return null;try{const x=new URL(raw);return x.protocol==="https:"?x.href:null}catch(_){return null}}
async function api(path){const r=await fetch(API+path,{headers:{Accept:"application/json"}});if(!r.ok)throw Error("HTTP "+r.status);return r.json()}
function notice(text){$("results").replaceChildren(el("div",text,"notice"))}
function safeLink(url){const link=href(url);if(!link)return null;const a=el("a",T("externalSource"));a.href=link;a.target="_blank";a.rel="noopener noreferrer";return a}
function setLanguage(){
 document.documentElement.lang=tags[lang];$("lang").value=lang;$("lang").setAttribute("aria-label",T("country"));
 document.querySelectorAll("[data-w]").forEach(n=>n.textContent=T(n.dataset.w));
 document.querySelectorAll("[data-nav]").forEach(n=>n.textContent=N(n.dataset.nav));
 document.querySelectorAll('[data-nav="about"]').forEach(n=>n.textContent=({en:"About",pt:"Sobre",es:"Acerca de",de:"Über uns",fr:"À propos",it:"Informazioni",nl:"Over ons"})[lang]);
 document.querySelectorAll('[data-new="history"]').forEach(n=>n.textContent=T("history"));
 document.querySelectorAll('[data-new="coverage"]').forEach(n=>n.textContent=({en:"Coverage",pt:"Cobertura",es:"Cobertura",de:"Datenstand",fr:"Couverture",it:"Copertura",nl:"Dekking"})[lang]);
 document.querySelectorAll('[data-new="wages"]').forEach(n=>n.textContent=T("wagesTitle"));
 document.querySelectorAll('[data-new="directory"]').forEach(n=>n.textContent=T("directoryTitle"));
 if(shown)render(shown);
}
function groupEntries(){
 if(!catalogue)return[];
 const entries=catalogue.groups||{};
 if(Array.isArray(entries))return entries.filter(x=>x.code).map(x=>[x.code,x.label||x.code]);
 return Object.entries(entries);
}
async function loadCatalogue(){
 const current=$("country").value,group=$("group");group.replaceChildren();catalogue=null;
 try{const endpoint=current==="ES"?"/v1/es/earnings/groups":"/v1/"+current.toLowerCase()+"/earnings/groups";
 const d=await api(endpoint);if(current!==$("country").value)return;catalogue=d;
 const rows=groupEntries();group.replaceChildren(...rows.map(([id,label])=>opt(id,label)));if(rows.some(([id])=>id==="TOTAL"))group.value="TOTAL";
 const sex=$("sex");for(const option of sex.options)option.disabled=current==="PT"&&option.value!=="both";if(current==="PT")sex.value="both";
 if(!rows.length)notice(T("unavailable"));else await load();
 }catch(_){notice(T("failure"))}
}
function makeTable(headings,rows){
 const wrap=el("div",undefined,"records"),table=el("table"),head=el("thead"),tr=el("tr");for(const text of headings)tr.append(el("th",text));head.append(tr);table.append(head);
 const body=el("tbody");for(const values of rows){const row=el("tr");for(const value of values)row.append(el("td",String(value)));body.append(row)}table.append(body);wrap.append(table);return wrap;
}
function pointsChart(rows){
 const valid=rows.filter(x=>Number.isInteger(x.year)&&Number.isFinite(x.value)).sort((a,b)=>a.year-b.year);
 if(valid.length<2)return el("p",T("noTrend"),"muted");
 const xmin=valid[0].year,xmax=valid[valid.length-1].year;
 if(xmin===xmax)return el("p",T("noTrend"),"muted");
 const ymin=Math.min(...valid.map(x=>x.value)),ymax=Math.max(...valid.map(x=>x.value)),pad=Math.max((ymax-ymin)*0.13,1),bottom=ymin-pad,top=ymax+pad;
 const x=year=>65+(year-xmin)*720/(xmax-xmin),y=value=>250-(value-bottom)*205/(top-bottom);
 const wrap=el("div",undefined,"library-chart"),svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.setAttribute("viewBox","0 0 840 295");svg.setAttribute("role","img");svg.setAttribute("aria-label",T("wagesTitle"));wrap.append(svg);
 function shape(tag,attrs){const e=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,String(v));svg.append(e);return e}
 for(let j=0;j<4;j++){const v=bottom+(top-bottom)*j/3;shape("line",{x1:65,x2:789,y1:y(v),y2:y(v),stroke:"#dce8e4"});shape("text",{x:8,y:y(v)+4,fill:"#526a71","font-size":12}).textContent=number(v)}
 for(let i=0;i<valid.length;i++){const p=valid[i];if(i>0&&p.year===valid[i-1].year+1)shape("line",{x1:x(valid[i-1].year),y1:y(valid[i-1].value),x2:x(p.year),y2:y(p.value),stroke:"#087f73","stroke-width":3});const dot=shape("circle",{cx:x(p.year),cy:y(p.value),r:5,fill:"#087f73"});dot.append(document.createElementNS("http://www.w3.org/2000/svg","title")).textContent=p.year+": "+number(p.value)}
 for(const year of [xmin,xmax])shape("text",{x:x(year),y:278,"text-anchor":"middle","font-size":12,fill:"#526a71"}).textContent=String(year);
 return wrap;
}
function renderWages(data){
 const out=$("results");out.replaceChildren();const source=el("p",undefined,"muted");
 source.textContent=[data.source,data.unit,data.precision,data.measure,data.salary_concept].filter(Boolean).join(" · ");out.append(source);
 const link=safeLink(data.source_url);if(link)out.append(link);
 out.append(el("div",T("groupNotice"),"notice"));
 const rows=Array.isArray(data.observations)?data.observations:[];
 if(!rows.length){out.append(el("p",T("unavailable"),"muted"));return}
 const entries=rows.map(r=>({period:String(r.period??r.year??""),year:typeof r.year==="number"?r.year:(/^\d{4}$/.test(String(r.period))?Number(r.period):null),value:r.status==="available"&&typeof r.value==="number"&&Number.isFinite(r.value)?r.value:null,status:r.status||T("missing"),quality:r.sample_quality||""}));
 const published=entries.filter(x=>x.value!==null);
 if(entries.some(x=>x.year!==null)&&published.filter(x=>x.year!==null).length>=2)out.append(pointsChart(published.filter(x=>x.year!==null)));
 else out.append(el("p",T("noTrend"),"muted"));
 out.append(makeTable([T("period"),T("amount"),T("unit"),T("dataQuality")],entries.map(x=>[x.period,x.value===null?T("missing"):number(x.value),data.unit||"",[x.status,x.quality].filter(Boolean).join(" · ")])));
 out.append(el("p",T("notHistory"),"muted"));
}
function renderDirectory(data){
 const out=$("results");out.replaceChildren();const entries=Object.entries(data||{}).filter(([,x])=>x&&typeof x==="object"&&!Array.isArray(x));
 if(!entries.length){notice(T("unavailable"));return}const grid=el("div",undefined,"library-list");
 for(const [id,source] of entries){const item=el("article",undefined,"source-item");item.append(el("h3",id.replaceAll("_"," ")));item.append(el("p",T("sourceRole")+": "+(source.role||"—")));item.append(el("p",T("sourceStatus")+": "+(source.status||"—")));const link=safeLink(source.url);if(link)item.append(link);grid.append(item)}out.append(grid);
}
function render(data){if(page==="wage-groups")renderWages(data);else renderDirectory(data)}
async function load(){
 const id=++sequence;notice(T("loading"));
 try{
  let path="/v1/sources";
  if(page==="wage-groups"){const c=$("country").value,group=$("group").value,sex=$("sex").value;if(!group){notice(T("unavailable"));return}
   path="/v1/"+c.toLowerCase()+"/earnings/groups/"+encodeURIComponent(group)+"?"+new URLSearchParams({sex}).toString();
  }
  const result=await api(path);if(id!==sequence)return;shown=result;render(result);
 }catch(_){if(id===sequence)notice(T("failure"))}
}
function init(){
 $("lang").addEventListener("change",event=>{lang=event.target.value;try{localStorage.setItem("earnwage_lang",lang)}catch(_){}setLanguage()});
 $("queryForm").addEventListener("submit",event=>{event.preventDefault();load()});
 setLanguage();
 if(page==="wage-groups"){$("country").addEventListener("change",loadCatalogue);$("sex").addEventListener("change",load);loadCatalogue()}else load();
}
init();
