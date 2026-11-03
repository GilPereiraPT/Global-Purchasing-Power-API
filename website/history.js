"use strict";
const API="https://earnwage-api.policlinicosdesantoandre.com";
const $=id=>document.getElementById(id),page=document.body.dataset.page;
const tags={en:"en-GB",pt:"pt-PT",es:"es-ES",de:"de-DE",fr:"fr-FR",it:"it-IT",nl:"nl-NL"};
const flags={PT:"Portugal",ES:"Spain",DE:"Germany",FR:"France",GB:"United Kingdom",IN:"India",BR:"Brazil",PK:"Pakistan",NL:"Netherlands",CH:"Switzerland",IT:"Italy",IE:"Ireland",US:"United States",CA:"Canada"};
const saved=(()=>{try{return localStorage.getItem("earnwage_lang")}catch(_){return null}})();
let lang=Object.hasOwn(tags,saved)?saved:Object.hasOwn(tags,(navigator.language||"").slice(0,2).toLowerCase())?navigator.language.slice(0,2).toLowerCase():"en";
let catalog=Object.keys(flags),loaded=null,requestId=0;
const T=k=>window.EarnWageHistoryI18n?.[lang]?.[k]||window.EarnWageHistoryI18n?.en?.[k]||k;
const N=k=>window.EarnWageExploreI18n?.[lang]?.[k]||window.EarnWageExploreI18n?.en?.[k]||k;
function elem(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(cls)e.className=cls;return e}
function option(value,label){const e=elem("option",label);e.value=value;return e}
function countryName(code){try{return new Intl.DisplayNames([tags[lang]],{type:"region"}).of(code)||code}catch(_){return flags[code]||code}}
function num(value){return new Intl.NumberFormat(tags[lang],{maximumFractionDigits:3}).format(value)}
async function fetchApi(path){const r=await fetch(API+path,{headers:{Accept:"application/json"}});if(!r.ok)throw Error("HTTP "+r.status);return r.json()}
function url(value){if(typeof value!=="string")return null;try{const u=new URL(value);return u.protocol==="https:"?u.href:null}catch(_){return null}}
function status(message){$("results").replaceChildren(elem("div",message,"notice"))}
function renderOptions(){const sel=$("country");if(!sel)return;const selected=sel.value||"PT";sel.replaceChildren(...catalog.map(code=>option(code,countryName(code))));if(catalog.includes(selected))sel.value=selected}
function translate(){
 document.querySelectorAll('[data-library="wages"]').forEach(x=>x.textContent=({en:"Wage groups",pt:"Grupos profissionais",es:"Grupos profesionales",de:"Berufsgruppen",fr:"Groupes professionnels",it:"Gruppi professionali",nl:"Beroepsgroepen"})[lang]);
 document.querySelectorAll('[data-library="directory"]').forEach(x=>x.textContent=({en:"Source directory",pt:"Diretório de fontes",es:"Directorio de fuentes",de:"Quellenverzeichnis",fr:"Répertoire des sources",it:"Elenco delle fonti",nl:"Bronnenoverzicht"})[lang]);
 document.documentElement.lang=tags[lang];$("lang").value=lang;$("lang").setAttribute("aria-label",T("indicator"));
 document.querySelectorAll("[data-h]").forEach(n=>n.textContent=T(n.dataset.h));
 document.querySelectorAll("[data-nav]").forEach(n=>n.textContent=N(n.dataset.nav));
 const named={about:{en:"About",pt:"Sobre",es:"Acerca de",de:"Über uns",fr:"À propos",it:"Informazioni",nl:"Over ons"}};
 document.querySelectorAll('[data-nav="about"]').forEach(n=>n.textContent=named.about[lang]);
 renderOptions();
 if(loaded)render(loaded);
}
function sourceLink(raw){const s=url(raw?.source_url);if(!s)return null;const a=elem("a",T("sourceLink"));a.href=s;a.target="_blank";a.rel="noopener noreferrer";return a}
function summary(raw,metric){const d=elem("div",undefined,"card");d.append(elem("h3",metric));const has=raw?.status==="available"&&Number.isFinite(raw.value);d.append(elem("div",has?num(raw.value):T("missing"),"metric"));const summaryText=[raw?.unit,raw?.year,raw?.source].filter(v=>v!==null&&v!==undefined&&v!=="").join(" · ");d.append(elem("p",summaryText));const a=sourceLink(raw);if(a)d.append(a);return d}
function table(headers,rows){const wrap=elem("div",undefined,"table-scroll"),tbl=elem("table",undefined,"data-table"),thead=elem("thead"),tr=elem("tr");for(const h of headers)tr.append(elem("th",h));thead.append(tr);tbl.append(thead);const body=elem("tbody");for(const cells of rows){const row=elem("tr");for(const cell of cells)row.append(elem("td",cell));body.append(row)}tbl.append(body);wrap.append(tbl);return wrap}
/* Real dated gaps break the polyline; no interpolation and no synthetic points. */
function plot(points){
 const root=elem("div",undefined,"history-plot");
 const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.setAttribute("viewBox","0 0 850 310");svg.setAttribute("role","img");svg.setAttribute("aria-label",T("historyDesc"));root.append(svg);
 const valid=points.filter(p=>Number.isInteger(p.year)&&Number.isFinite(p.value)).sort((a,b)=>a.year-b.year);if(!valid.length)return root;
 const years=valid.map(p=>p.year),values=valid.map(p=>p.value);const xmin=Math.min(...years),xmax=Math.max(...years),ymin=Math.min(...values),ymax=Math.max(...values);
 const ypad=Math.max((ymax-ymin)*0.12,Math.abs(ymax)*0.03,0.1),bottom=ymin-ypad,top=ymax+ypad;
 const x=y=>60+(y-xmin)*735/Math.max(xmax-xmin,1),y=v=>256-(v-bottom)*213/(top-bottom);
 function svgEl(tag,attrs){const z=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const [k,v]of Object.entries(attrs))z.setAttribute(k,String(v));svg.append(z);return z}
 for(let i=0;i<=4;i++){const value=bottom+(top-bottom)*i/4,sy=y(value);svgEl("line",{x1:60,y1:sy,x2:798,y2:sy,stroke:"#d9e7e5","stroke-width":1});const label=svgEl("text",{x:8,y:sy+4});label.textContent=num(value)}
 const distinctYears=[xmin,Math.round((xmin+xmax)/2),xmax].filter((v,i,a)=>a.indexOf(v)===i);
 for(const year of distinctYears){const text=svgEl("text",{x:x(year),y:286,"text-anchor":"middle"});text.textContent=String(year)}
 for(let i=0;i<valid.length-1;i++){const a=valid[i],b=valid[i+1];if(b.year!==a.year+1)continue;svgEl("line",{x1:x(a.year),y1:y(a.value),x2:x(b.year),y2:y(b.value),stroke:"#087f73","stroke-width":3,"stroke-linecap":"round"})}
 for(const p of valid){const circle=svgEl("circle",{cx:x(p.year),cy:y(p.value),r:4,fill:"#087f73"});circle.append(document.createElementNS("http://www.w3.org/2000/svg","title")).textContent=String(p.year)+": "+num(p.value)}
 return root;
}
function renderHistory(raw){
 const out=$("results");out.replaceChildren();const valid=(raw?.history||[]).filter(p=>Number.isInteger(p.year)&&typeof p.value==="number"&&Number.isFinite(p.value));
 if(!valid.length){status(T("noData"));return}
 valid.sort((a,b)=>a.year-b.year);
 const flex=elem("div",undefined,"cards");flex.append(summary(raw,T(raw.name==="ppp_private_consumption"?"ppp":"inflation")));out.append(flex,plot(valid));
 out.append(table([T("year"),T("value"),T("unit")],valid.slice().reverse().map(p=>[String(p.year),num(p.value),raw.unit||"—"])));
 out.append(elem("p",T("historyDisclaimer"),"muted"));
 if(raw.last_successful_refresh)out.append(elem("p",T("lastRefresh")+": "+raw.last_successful_refresh,"muted"));
}
function renderCoverage(raw){
 const out=$("results");out.replaceChildren();const list=elem("div",undefined,"coverage-list");
 const records=Array.isArray(raw?.countries)?raw.countries:[];if(!records.length){status(T("noData"));return}
 for(const record of records){const item=elem("article",undefined,"coverage-item");item.append(elem("h3",countryName(record.country)));
 for(const [key,label] of [["inflation_annual",T("inflation")],["ppp_private_consumption",T("ppp")]]){
  const indicator=record.indicators?.[key],available=indicator?.status==="available"&&Number.isFinite(indicator.value);
  const p=elem("p");const strong=elem("strong",label+": ");p.append(strong,elem("span",available?T("available")+(indicator.year?" · "+indicator.year:""):T("missing"),available?"status-good":"status-missing"));item.append(p);
 }
 const links=elem("div",undefined,"actions");
 const a=elem("a",T("countryDetails"),"secondary");a.href="./country.html?country="+encodeURIComponent(record.country);links.append(a);
 const b=elem("a",T("viewHistory"),"secondary");b.href="./history.html?country="+encodeURIComponent(record.country);links.append(b);
 item.append(links);list.append(item);
 }
 out.append(list,elem("p",T("coverageDisclaimer"),"muted"));
}
function render(raw){if(page==="history")renderHistory(raw);else renderCoverage(raw)}
async function load(){
 const id=++requestId;status(T("loading"));
 try{
  const path=page==="history"?"/v1/economy/history/"+encodeURIComponent($("country").value)+"?indicator="+encodeURIComponent($("indicator").value):"/v1/economy/coverage";
  const r=await fetchApi(path);if(id!==requestId)return;loaded=r;render(r);
 }catch(_){if(id!==requestId)return;loaded=null;status(T("error"))}
}
async function init(){
 $("lang").addEventListener("change",event=>{lang=event.target.value;try{localStorage.setItem("earnwage_lang",lang)}catch(_){}translate()});
 $("load").addEventListener("click",load);
 $("country")?.addEventListener("change",load);
 $("indicator")?.addEventListener("change",load);
 translate();
 if(page==="history"){
  try{const d=await fetchApi("/v1/countries");if(Array.isArray(d.countries)&&d.countries.length)catalog=d.countries.filter(c=>c.code&&c.currency).map(c=>c.code)}catch(_){}
  renderOptions();const params=new URLSearchParams(location.search),code=params.get("country");
  if(code&&catalog.includes(code))$("country").value=code;
  const ind=params.get("indicator");if(ind==="ppp_private_consumption"||ind==="inflation_annual")$("indicator").value=ind;
 }
 await load();
}
init();
