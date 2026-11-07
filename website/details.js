"use strict";
const API=window.EarnWageConfig.apiBase;
const $=id=>document.getElementById(id);
const page=document.body.dataset.page;
const langs=["en","pt","es","de","fr","it","nl"];
const tags={en:"en-GB",pt:"pt-PT",es:"es-ES",de:"de-DE",fr:"fr-FR",it:"it-IT",nl:"nl-NL"};
const fallback={PT:["Portugal","EUR"],ES:["Spain","EUR"],DE:["Germany","EUR"],FR:["France","EUR"],GB:["United Kingdom","GBP"],IN:["India","INR"],BR:["Brazil","BRL"],PK:["Pakistan","PKR"],NL:["Netherlands","EUR"],CH:["Switzerland","CHF"],IT:["Italy","EUR"],IE:["Ireland","EUR"],US:["United States","USD"],CA:["Canada","CAD"]};
let saved;try{saved=localStorage.getItem("earnwage_lang")}catch(_){}
let lang=langs.includes(saved)?saved:langs.includes((navigator.language||"").slice(0,2).toLowerCase())?navigator.language.slice(0,2).toLowerCase():"en";
let countries=Object.entries(fallback).map(([code,[name,currency]])=>({code,name,currency}));
let occupations=[{id:"accountant",label:"Accountant"}],revision=0,loadId=0;
const T=k=>window.EarnWageDetailsI18n?.[lang]?.[k]||window.EarnWageDetailsI18n?.en?.[k]||k;
const N=k=>window.EarnWageExploreI18n?.[lang]?.[k]||window.EarnWageExploreI18n?.en?.[k]||k;
function elt(tag,txt,cls){const n=document.createElement(tag);if(txt!==undefined)n.textContent=String(txt);if(cls)n.className=cls;return n}
function opts(v,txt){const n=document.createElement("option");n.value=v;n.textContent=txt;return n}
function countryName(code){try{return new Intl.DisplayNames([tags[lang]],{type:"region"}).of(code)||code}catch(_){return countries.find(c=>c.code===code)?.name||code}}
function number(v){return new Intl.NumberFormat(tags[lang],{maximumFractionDigits:3}).format(v)}
function money(v,code){try{return new Intl.NumberFormat(tags[lang],{style:"currency",currency:code,maximumFractionDigits:2}).format(v)}catch(_){return number(v)+" "+code}}
function urlSource(val){if(typeof val!=="string")return null;try{const u=new URL(val);return u.protocol==="https:"?u.href:null}catch(_){return null}}
async function api(path){const r=await fetch(API+path,{headers:{Accept:"application/json"}});if(!r.ok)throw Error("HTTP "+r.status);return r.json()}
function link(text,href){const a=elt("a",text);a.href=href;return a}
function namedSection(title,value,note){const c=elt("div",undefined,"card");c.append(elt("h3",title));c.append(elt("div",value,"metric"));if(note)c.append(elt("p",note));return c}
function tip(container,message){container.replaceChildren(elt("div",message,"notice"))}
function renderCountryOptions(){const e=$("country");if(!e)return;const selected=e.value||"PT";e.replaceChildren(...countries.map(x=>opts(x.code,window.EarnWageFlags.label(x.code,countryName(x.code)))));if(countries.some(x=>x.code===selected))e.value=selected}
function renderOccupations(){const e=$("occupation");if(!e)return;const selected=e.value||"accountant";e.replaceChildren(...occupations.map(x=>opts(x.id,x.label)));if(occupations.some(x=>x.id===selected))e.value=selected}
function applyLanguage(){
 document.querySelectorAll('[data-library="wages"]').forEach(x=>x.textContent=({en:"Wage groups",pt:"Grupos profissionais",es:"Grupos profesionales",de:"Berufsgruppen",fr:"Groupes professionnels",it:"Gruppi professionali",nl:"Beroepsgroepen"})[lang]);
 document.querySelectorAll('[data-library="directory"]').forEach(x=>x.textContent=({en:"Source directory",pt:"Diretório de fontes",es:"Directorio de fuentes",de:"Quellenverzeichnis",fr:"Répertoire des sources",it:"Elenco delle fonti",nl:"Bronnenoverzicht"})[lang]);
 document.querySelectorAll('[data-more="history"]').forEach(x=>x.textContent=({en:"History",pt:"Histórico",es:"Histórico",de:"Verlauf",fr:"Historique",it:"Storico",nl:"Historie"})[lang]);
 document.querySelectorAll('[data-more="coverage"]').forEach(x=>x.textContent=({en:"Coverage",pt:"Cobertura",es:"Cobertura",de:"Datenstand",fr:"Couverture",it:"Copertura",nl:"Dekking"})[lang]);document.documentElement.lang=tags[lang];$("lang").value=lang;document.querySelectorAll("[data-d]").forEach(x=>x.textContent=T(x.dataset.d));document.querySelectorAll("[data-nav]").forEach(x=>x.textContent=N(x.dataset.nav)||T(x.dataset.nav));document.querySelectorAll('a[data-nav="methodology"]').forEach(x=>x.textContent=T("methodTitle"));document.querySelectorAll('a[data-nav="sources"]').forEach(x=>x.textContent=T("sourcesTitle"));document.querySelectorAll('a[data-nav="about"]').forEach(x=>x.textContent=({en:"About",pt:"Sobre",es:"Acerca de",de:"Über uns",fr:"À propos",it:"Informazioni",nl:"Over ons"})[lang]);renderCountryOptions();renderOccupations()}
async function loadCountries(){try{const d=await api("/v1/countries");if(Array.isArray(d.countries)&&d.countries.length)countries=d.countries.filter(c=>c.code&&c.currency&&c.name)}catch(_){}renderCountryOptions()}
async function loadOccupations(){const id=++revision;try{const d=await api("/v1/occupations?lang="+lang);if(id!==revision)return;if(Array.isArray(d.occupations)&&d.occupations.length)occupations=d.occupations}catch(_){}renderOccupations()}
function indicatorCard(indicator,label){const available=indicator?.status==="available"&&typeof indicator.value==="number"&&Number.isFinite(indicator.value);const note=[indicator?.year,indicator?.unit,indicator?.source,indicator?.status].filter(x=>x!==null&&x!==undefined&&x!=="").join(" · ");const c=namedSection(label,available?number(indicator.value):T("unavailable"),note);const u=urlSource(indicator?.source_url);if(u){const a=link(T("viewSource"),u);a.target="_blank";a.rel="noopener noreferrer";c.append(a)}return c}
function linkToProfiles(code,occupation){if($("compareLink"))$("compareLink").href="./compare.html?country_a="+encodeURIComponent(code)+(occupation?"&occupation="+encodeURIComponent(occupation):"");if($("salaryLink"))$("salaryLink").href="./occupation.html?country="+encodeURIComponent(code)}
async function showCountryOrSources(){const id=++loadId,code=$("country").value,target=$("detailsResults");tip(target,T("refresh"));linkToProfiles(code);if(page==="country")window.EarnWageCountryGuides?.render({code,language:lang,occupations,api,container:$("countryGuide")});
if(page==="country"&&window.EarnWageCountryData){
 const country=countries.find(c=>c.code===code);
 await window.EarnWageCountryData.showCountry({code,language:lang,container:target,request:api,country});
 return;
}
try{
 const [country,economy]=await Promise.all([api("/v1/countries/"+code),api("/v1/economy/compare?country_a="+code+"&country_b="+code)]);if(id!==loadId)return;
 target.replaceChildren();const cards=elt("div",undefined,"cards");
 if(page==="country"){cards.append(namedSection(T("countryTitle"),countryName(code),code));cards.append(namedSection(N("currency"),country.currency||"—"));cards.append(namedSection(N("capital"),country.capital||"—"))}
 const row=economy?.countries?.[0];for(const [key,label] of [["inflation_annual",N("inflation")],["ppp_private_consumption",N("ppp")]])cards.append(indicatorCard(row?.indicators?.[key],label));
 target.append(cards);const related=elt("div",undefined,"actions");const history=link(({en:"History",pt:"Histórico",es:"Histórico",de:"Verlauf",fr:"Historique",it:"Storico",nl:"Historie"})[lang],"./history.html?country="+encodeURIComponent(code));history.className="secondary";related.append(history);target.append(related);target.append(elt("p",T("disclaimer"),"muted"));
 }catch(_){if(id===loadId)tip(target,T("unavailable"))}}
function preferredOccupationWage(record){
 if(record?.status!=="available")return null;
 if(Number.isFinite(record.value)&&record.value>0)return record;
 const rows=Array.isArray(record.observations)?record.observations.filter(x=>x&&Number.isFinite(x.value)&&x.value>0):[];
 return rows.find(x=>x.measure==="median")||rows.find(x=>x.measure==="mean")||rows[0]||null;
}
function wageCard(label,record,unit){
 const chosen=preferredOccupationWage(record),available=chosen&&Number.isFinite(chosen.value);
 const displayed=available?number(chosen.value)+" "+(chosen.unit?.includes("/")?chosen.unit:(chosen.currency||unit||"")):T("unavailable");
 return namedSection(label,displayed,[chosen?.reference_period||record?.reference_period||record?.period,chosen?.measure||record?.measure,chosen?.unit||record?.unit,chosen?.source||record?.source,record?.status].filter(Boolean).join(" · "));
}
async function showOccupation(){const id=++loadId,code=$("country").value,occupation=$("occupation").value,target=$("detailsResults");tip(target,T("refresh"));linkToProfiles(code,occupation);try{
 const q=new URLSearchParams({country:code,occupation});const d=await api("/v1/earnwage/overview?"+q);if(id!==loadId)return;target.replaceChildren();
 const cards=elt("div",undefined,"cards");cards.append(wageCard(T("occupationWage"),d.national_occupation_wage,d.country?.currency));const a=d.annual_presentation||{};cards.append(namedSection(T("annual"),a.status==="available"&&typeof a.value==="number"?money(a.value,a.currency||d.country?.currency):T("unavailable"),[a.note,a.year,a.unit].filter(Boolean).join(" · ")));const group=d.national_major_group_context||{},local=group.values?.local_currency;
 const contextAmount=group.status==="available"&&local?.status==="available"&&Number.isFinite(local.value)&&local.value>0?
   number(local.value)+" "+(local.currency||""):group.status==="available"?T("coverage"):T("unavailable");
 cards.append(namedSection(T("groupContext"),contextAmount,[T("groupWarning"),group.precision,group.period,local?.unit||group.unit].filter(Boolean).join(" · ")));target.append(cards);
 const primary=preferredOccupationWage(d.national_occupation_wage)||d.national_occupation_wage;if(urlSource(primary?.source_url)){const l=link(T("viewSource"),primary.source_url);l.target="_blank";l.rel="noopener noreferrer";target.append(elt("div",undefined,"actions")).append(l)}
 target.append(elt("p",T("disclaimer"),"muted"));if(Array.isArray(d.warnings)){for(const warning of d.warnings.slice(0,5))target.append(elt("p",warning,"muted"))}
 }catch(_){if(id===loadId)tip(target,T("unavailable"))}}
function pick(){if(page==="occupation")showOccupation();else if(page==="country"||page==="sources")showCountryOrSources()}
async function init(){
 applyLanguage();const params=new URLSearchParams(location.search);
 const code=params.get("country");const occupation=params.get("occupation");
 await Promise.all([loadCountries(),loadOccupations()]);
 if(code&&countries.some(x=>x.code===code)&&$("country"))$("country").value=code;
 if(occupation&&occupations.some(x=>x.id===occupation)&&$("occupation"))$("occupation").value=occupation;
 $("refresh")?.addEventListener("click",pick);$("country")?.addEventListener("change",pick);$("occupation")?.addEventListener("change",pick);
 $("lang").addEventListener("change",async e=>{lang=e.target.value;try{localStorage.setItem("earnwage_lang",lang)}catch(_){}applyLanguage();await loadOccupations();pick()});
 if(page!=="methodology")pick();
}
init();
