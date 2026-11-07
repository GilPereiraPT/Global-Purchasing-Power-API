"use strict";
const EW_API=window.EarnWageConfig.apiBase;
const EW_LANGS=["en","pt","es","de","fr","it","nl"];
const EW_TAGS={en:"en-GB",pt:"pt-PT",es:"es-ES",de:"de-DE",fr:"fr-FR",it:"it-IT",nl:"nl-NL"};
const EW_FLAGS={en:"🇬🇧",pt:"🇵🇹",es:"🇪🇸",de:"🇩🇪",fr:"🇫🇷",it:"🇮🇹",nl:"🇳🇱"};
const EW_COUNTRIES={PT:["Portugal","EUR"],ES:["Spain","EUR"],DE:["Germany","EUR"],FR:["France","EUR"],GB:["United Kingdom","GBP"],IN:["India","INR"],BR:["Brazil","BRL"],PK:["Pakistan","PKR"],NL:["Netherlands","EUR"],CH:["Switzerland","CHF"],IT:["Italy","EUR"],IE:["Ireland","EUR"],US:["United States","USD"],CA:["Canada","CAD"]};
const $=id=>document.getElementById(id);
const page=document.body.dataset.page;
const stored=(()=>{try{return localStorage.getItem("earnwage_lang")}catch(_){return null}})();
let language=EW_LANGS.includes(stored)?stored:EW_LANGS.includes((navigator.language||"").slice(0,2).toLowerCase())?navigator.language.slice(0,2).toLowerCase():"en";
let countryCatalogue=Object.entries(EW_COUNTRIES).map(([code,[name,currency]])=>({code,name,currency}));
let occupations=[];
let currentOverview=null;
const T=k=>window.EarnWageExploreI18n?.[language]?.[k]||window.EarnWageExploreI18n?.en?.[k]||k;
const format=(x)=>new Intl.NumberFormat(EW_TAGS[language],{maximumFractionDigits:2}).format(x);
function make(tag,txt,cls){const n=document.createElement(tag);if(txt!==undefined)n.textContent=String(txt);if(cls)n.className=cls;return n}
function appendText(parent,tag,txt,cls){const e=make(tag,txt,cls);parent.append(e);return e}
function option(v,label){const e=document.createElement("option");e.value=v;e.textContent=label;return e}
function safeExternal(url){try{const p=new URL(url);return p.protocol==="https:"?p.href:null}catch(_){return null}}
function countryLabel(code){try{return new Intl.DisplayNames([EW_TAGS[language]],{type:"region"}).of(code)||EW_COUNTRIES[code]?.[0]||code}catch(_){return EW_COUNTRIES[code]?.[0]||code}}
function renderCountries(){
 document.querySelectorAll("select[data-country]").forEach(node=>{
   const value=node.value||node.dataset.default||"PT";
   node.replaceChildren(...countryCatalogue.map(x=>option(x.code,window.EarnWageFlags.label(x.code,countryLabel(x.code)))));
   if(countryCatalogue.some(x=>x.code===value))node.value=value;
 });
 const grid=$("countryTiles");
 if(grid&&window.EarnWageCountryData)
   window.EarnWageCountryData.flagsGrid({container:grid,countries:countryCatalogue,language,selected:$("country")?.value||"PT"});
}
function renderOccupations(){
  document.querySelectorAll("select[data-occupation]").forEach(node=>{const value=node.value||node.dataset.default||"accountant";node.replaceChildren(...occupations.map(x=>option(x.id,x.label||x.id)));if(occupations.some(x=>x.id===value))node.value=value})
}
function applyLanguage(){
 document.querySelectorAll('[data-library="wages"]').forEach(x=>x.textContent=({en:"Wage groups",pt:"Grupos profissionais",es:"Grupos profesionales",de:"Berufsgruppen",fr:"Groupes professionnels",it:"Gruppi professionali",nl:"Beroepsgroepen"})[language]);
 document.querySelectorAll('[data-library="directory"]').forEach(x=>x.textContent=({en:"Source directory",pt:"Diretório de fontes",es:"Directorio de fuentes",de:"Quellenverzeichnis",fr:"Répertoire des sources",it:"Elenco delle fonti",nl:"Bronnenoverzicht"})[language]);
 document.querySelectorAll('[data-more="history"]').forEach(x=>x.textContent=({en:"History",pt:"Histórico",es:"Histórico",de:"Verlauf",fr:"Historique",it:"Storico",nl:"Historie"})[language]);
 document.querySelectorAll('[data-more="coverage"]').forEach(x=>x.textContent=({en:"Coverage",pt:"Cobertura",es:"Cobertura",de:"Datenstand",fr:"Couverture",it:"Copertura",nl:"Dekking"})[language]);
 document.querySelectorAll("[data-method-link]").forEach(el=>el.textContent=({en:"Methodology",pt:"Metodologia",es:"Metodología",de:"Methodik",fr:"Méthodologie",it:"Metodologia",nl:"Methodologie"})[language]);
 document.querySelectorAll("[data-sources-link]").forEach(el=>el.textContent=({en:"Data sources",pt:"Fontes de dados",es:"Fuentes de datos",de:"Datenquellen",fr:"Sources de données",it:"Fonti dei dati",nl:"Gegevensbronnen"})[language]);
 document.querySelectorAll("[data-about-link]").forEach(el=>el.textContent=({en:"About",pt:"Sobre",es:"Acerca de",de:"Über uns",fr:"À propos",it:"Informazioni",nl:"Over ons"})[language]);
  document.documentElement.lang=EW_TAGS[language];$("lang").value=language;$("lang").setAttribute("aria-label",T("language"));
  document.querySelectorAll("[data-t]").forEach(node=>node.textContent=T(node.dataset.t));
  renderCountries();renderOccupations();
}
async function api(path){const r=await fetch(EW_API+path,{headers:{Accept:"application/json"}});if(!r.ok)throw Error("HTTP "+r.status);return r.json()}
function warning(target,message){target.replaceChildren(make("div",message,"notice"))}
function card(title,value,note){const n=make("div",undefined,"card");appendText(n,"h3",title);appendText(n,"div",value,"metric");if(note)appendText(n,"p",note);return n}
async function loadCountries(){try{const r=await api("/v1/countries");if(Array.isArray(r.countries)&&r.countries.length){countryCatalogue=r.countries.filter(x=>x?.code&&x?.currency&&x?.name)}}catch(_){}renderCountries()}
let occupationRevision=0;
async function loadOccupations(){const revision=++occupationRevision;try{const data=await api("/v1/occupations?lang="+encodeURIComponent(language));if(revision!==occupationRevision)return;if(Array.isArray(data.occupations))occupations=data.occupations}catch(_){if(!occupations.length)occupations=[{id:"accountant",label:language==="pt"?"Contabilista":"Accountant"}]}renderOccupations()}
function currentCountry(code){return countryCatalogue.find(c=>c.code===code)}
function money(value,currency){if(typeof value!=="number"||!Number.isFinite(value)||!currency)return "—";try{return new Intl.NumberFormat(EW_TAGS[language],{style:"currency",currency,maximumFractionDigits:2}).format(value)}catch(_){return format(value)+" "+currency}}
function statusNote(row){const s=row?.source||row?.source_name||"";const y=row?.year||row?.period||row?.latest_period||"";return [s,y].filter(Boolean).join(" · ")||T("dataNote")}
function preferredOccupationWage(record){
 if(record?.status!=="available")return null;
 if(Number.isFinite(record.value)&&record.value>0)return record;
 const rows=Array.isArray(record.observations)?record.observations.filter(x=>x&&Number.isFinite(x.value)&&x.value>0):[];
 return rows.find(x=>x.measure==="median")||rows.find(x=>x.measure==="mean")||rows[0]||null;
}
function renderSalaryOverview(data){
 const out=$("results");out.replaceChildren();
 const wage=data.national_occupation_wage||{},annual=data.annual_presentation||{},group=data.national_major_group_context||{};
 const wrapper=make("div",undefined,"cards");
 const label=data.occupation?.translations?.[language]||occupations.find(o=>o.id===data.occupation?.id)?.label||data.occupation?.label||"";
 const selected=preferredOccupationWage(wage);
 if(wage.status==="available"){
  const amountValue=selected?format(selected.value)+" "+(selected.unit?.includes("/")?selected.unit:(selected.currency||wage.currency||data.country?.currency||"")):T("official");
  wrapper.append(card(label,amountValue,statusNote(selected||wage)+" · "+[selected?.measure||wage.measure,selected?.unit||wage.unit].filter(Boolean).join(" · ")));
 }else wrapper.append(card(label,T("unavailable"),wage.reason||T("missing")));
 if(annual.status==="available"){wrapper.append(card(T("annual"),money(Number(annual.value),annual.currency||data.country?.currency),statusNote(annual)))}else{wrapper.append(card(T("annual"),T("unavailable"),annual.reason||T("missing")))}
 const groupLocal=group?.values?.local_currency;
 const groupHasValue=group?.status==="available"&&groupLocal?.status==="available"&&Number.isFinite(groupLocal.value)&&groupLocal.value>0;
 const contextValue=groupHasValue?format(groupLocal.value)+" "+groupLocal.currency:group.status==="available"?T("official"):T("unavailable");
 wrapper.append(card(T("context"),contextValue,[T("context"),group?.precision,group?.period,groupHasValue?group.unit:""].filter(Boolean).join(" · ")));
 out.append(wrapper);
 const detailLink=make("a",T("details"),"secondary");detailLink.href="./occupation.html?country="+encodeURIComponent(data.country?.code||$("country").value)+"&occupation="+encodeURIComponent(data.occupation?.id||$("occupation").value);const links=make("div",undefined,"actions");links.append(detailLink);const a=make("a",T("compareAction"),"secondary");a.href="./compare.html?country_a="+encodeURIComponent(data.country?.code||$("country").value)+"&occupation="+encodeURIComponent(data.occupation?.id||$("occupation").value);links.append(a);out.append(links);
 const note=make("p",T("dataNote"),"muted");out.append(note);
}
async function searchSalary(){const out=$("results"),code=$("country").value,occupation=$("occupation").value;if(!occupation){warning(out,T("choose"));return}warning(out,T("reload"));try{const p=new URLSearchParams({country:code,occupation});currentOverview=await api("/v1/earnwage/overview?"+p);renderSalaryOverview(currentOverview)}catch(e){warning(out,T("unavailable")+" ("+e.message+")")}}
function renderCountryDetail(row){
 const out=$("results");out.replaceChildren();
 const c=currentCountry(row.code);const grid=make("div",undefined,"cards");
 grid.append(card(T("countryProfile"),window.EarnWageFlags.label(row.code,countryLabel(row.code)),row.code));
 grid.append(card(T("currency"),row.currency||c?.currency||"—",""));
 grid.append(card(T("capital"),row.capital||"—",""));
 out.append(grid);
 const link=make("a",T("compareAction"),"secondary");link.href="./compare.html?country_a="+encodeURIComponent(row.code);
 const actions=make("div",undefined,"actions");actions.append(link);const profile=make("a",T("details"),"secondary");profile.href="./country.html?country="+encodeURIComponent(row.code);actions.append(profile);const history=make("a",({en:"History",pt:"Histórico",es:"Histórico",de:"Verlauf",fr:"Historique",it:"Storico",nl:"Historie"})[language],"secondary");history.href="./history.html?country="+encodeURIComponent(row.code);actions.append(history);out.append(actions);
}
async function showCountry(){const code=$("country").value,out=$("results");warning(out,T("reload"));try{const [country,econ]=await Promise.all([api("/v1/countries/"+encodeURIComponent(code)),api("/v1/economy/compare?country_a="+encodeURIComponent(code)+"&country_b="+encodeURIComponent(code))]);renderCountryDetail(country);const row=(econ.countries||[])[0];if(row){const cards=make("div",undefined,"cards");for(const [key,label] of [["inflation_annual",T("inflation")],["ppp_private_consumption",T("ppp")]]){const v=row.indicators?.[key];cards.append(card(label,v?.status==="available"&&v?.value!=null?format(v.value)+(v.unit?" "+v.unit:""):T("missing"),statusNote(v)))}out.append(make("h2",T("insights")));out.append(cards)}}catch(e){warning(out,T("unavailable")+" ("+e.message+")")}}
async function showInsights(){const out=$("results"),country=$("country").value;warning(out,T("reload"));try{const data=await api("/v1/economy/compare?country_a="+country+"&country_b="+country);const row=data.countries?.[0];if(!row)throw Error("No data");out.replaceChildren();const cards=make("div",undefined,"cards");for(const [key,title] of [["inflation_annual",T("inflation")],["ppp_private_consumption",T("ppp")]]){const metric=row.indicators?.[key];const val=metric?.status==="available"&&Number.isFinite(metric.value)?format(metric.value)+(metric.unit?" "+metric.unit:""):T("missing");cards.append(card(title,val,statusNote(metric)));if(metric?.source_url){const link=make("a",T("sourceLink"));link.href=metric.source_url;link.target="_blank";link.rel="noopener noreferrer";const child=cards.lastElementChild;child.append(make("p")).append(link)}}out.append(cards);const history=make("a",({en:"History",pt:"Histórico",es:"Histórico",de:"Verlauf",fr:"Historique",it:"Storico",nl:"Historie"})[language],"secondary");history.href="./history.html?country="+encodeURIComponent(country);out.append(make("div",undefined,"actions")).append(history);out.append(make("p",T("dataNote"),"muted"))}catch(e){warning(out,T("unavailable")+" ("+e.message+")")}}
async function searchJobs(){
 const out=$("results"),country=$("country").value,occupation=$("occupation").value;if(!occupation){warning(out,T("choose"));return}warning(out,T("reload"));
 try{const params=new URLSearchParams({country,occupation,limit:"30",salary_published:$("salaryOnly").checked?"true":"false"});const d=await api("/v1/jobs?"+params);out.replaceChildren();const rows=Array.isArray(d.jobs)?d.jobs:[];if(!rows.length){warning(out,T("noJobs"));return}
 const stack=make("div",undefined,"stack");for(const j of rows){const rec=make("article",undefined,"record"),left=make("div");appendText(left,"div",j.title||"—","name");appendText(left,"p",[j.company,j.candidate_required_location,j.salary_text||j.salary_structured&&[j.salary_structured.min,j.salary_structured.max,j.salary_structured.currency,j.salary_structured.period].filter(x=>x!==null&&x!==undefined).join(" ")].filter(Boolean).join(" · "));appendText(left,"p",[j.source,j.published_at?.slice(0,10)].filter(Boolean).join(" · "));rec.append(left);const url=safeExternal(j.apply_url||j.source_url);if(url){const a=make("a",T("apply"));a.href=url;a.target="_blank";a.rel="noopener noreferrer";rec.append(a)}stack.append(rec)}out.append(stack);out.append(make("p",T("remoteDisclaimer"),"muted"))}catch(e){warning(out,T("unavailable")+" ("+e.message+")")}
}
const routes={salaries:searchSalary,countries:showCountry,jobs:searchJobs,insights:showInsights};
function bind(){const form=$("exploreForm");form?.addEventListener("submit",e=>{e.preventDefault();routes[page]?.()});$("lang")?.addEventListener("change",async e=>{language=e.target.value;try{localStorage.setItem("earnwage_lang",language)}catch(_){}applyLanguage();await loadOccupations();if($("results")?.children.length)routes[page]?.()})}
async function init(){bind();applyLanguage();await Promise.all([loadCountries(),loadOccupations()]);const params=new URLSearchParams(location.search);const code=params.get("country");if(code&&countryCatalogue.some(x=>x.code===code))$("country").value=code;const occupation=params.get("occupation");if(occupation&&occupations.some(x=>x.id===occupation)&&$("occupation"))$("occupation").value=occupation;}
init();
