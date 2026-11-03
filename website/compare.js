"use strict";
const API=window.EarnWageConfig.apiBase;
const LANGS=["en","pt","es","de","fr","it","nl"];
const TAGS={en:"en-GB",pt:"pt-PT",es:"es-ES",de:"de-DE",fr:"fr-FR",it:"it-IT",nl:"nl-NL"};
const FALLBACK=[["PT","Portugal","EUR"],["ES","Spain","EUR"],["DE","Germany","EUR"],["FR","France","EUR"],["GB","United Kingdom","GBP"],["IN","India","INR"],["BR","Brazil","BRL"],["PK","Pakistan","PKR"],["NL","Netherlands","EUR"],["CH","Switzerland","CHF"],["IT","Italy","EUR"],["IE","Ireland","EUR"],["US","United States","USD"],["CA","Canada","CAD"]];
const $=id=>document.getElementById(id);
const stored=(()=>{try{return localStorage.getItem("earnwage_lang")}catch(_){return null}})();
let lang=LANGS.includes(stored)?stored:LANGS.includes((navigator.language||"").slice(0,2).toLowerCase())?navigator.language.slice(0,2).toLowerCase():"en";
let countries=FALLBACK.map(([code,name,currency])=>({code,name,currency}));
let jobs=[{id:"accountant",label:"Accountant"}],last=null,serial=0;
const meta={A:null,B:null},options={A:[],B:[]};
const T=key=>window.EarnWageCompareI18n?.[lang]?.[key]||window.EarnWageCompareI18n?.en?.[key]||key;
const navT=key=>window.EarnWageExploreI18n?.[lang]?.[key]||window.EarnWageExploreI18n?.en?.[key]||key;
function node(tag,text,cls){const x=document.createElement(tag);if(text!==undefined)x.textContent=String(text);if(cls)x.className=cls;return x}
function option(code,label){const o=document.createElement("option");o.value=code;o.textContent=label;return o}
function clearThen(target,...els){target.replaceChildren(...els)}
function countryName(code){try{return new Intl.DisplayNames([TAGS[lang]],{type:"region"}).of(code)||code}catch(_){return countries.find(c=>c.code===code)?.name||code}}
function currency(code){return countries.find(c=>c.code===code)?.currency||""}
function money(value,code){if(typeof value!=="number"||!Number.isFinite(value))return "—";try{return new Intl.NumberFormat(TAGS[lang],{style:"currency",currency:code,maximumFractionDigits:2}).format(value)}catch(_){return value.toLocaleString(TAGS[lang])+" "+code}}
function percent(value){return typeof value==="number"&&Number.isFinite(value)?new Intl.NumberFormat(TAGS[lang],{maximumFractionDigits:1,signDisplay:"always"}).format(value)+"%":"—"}
async function request(path){const resp=await fetch(API+path,{headers:{Accept:"application/json"}});if(!resp.ok)throw Error("HTTP "+resp.status);return resp.json()}
function setCountries(){for(const side of ["A","B"]){const sel=$("country"+side),v=sel.value|| (side==="A"?"PT":"CH");sel.replaceChildren(...countries.map(c=>option(c.code,countryName(c.code))));if(countries.some(c=>c.code===v))sel.value=v;$("currency"+side).textContent=currency(sel.value)}}
function setOccupations(){const select=$("occupation"),current=select.value;select.replaceChildren(...jobs.map(o=>option(o.id,o.label)));if(jobs.some(o=>o.id===current))select.value=current}
function applyLang(){
 document.querySelectorAll('[data-more="history"]').forEach(x=>x.textContent=({en:"History",pt:"Histórico",es:"Histórico",de:"Verlauf",fr:"Historique",it:"Storico",nl:"Historie"})[lang]);
 document.querySelectorAll('[data-more="coverage"]').forEach(x=>x.textContent=({en:"Coverage",pt:"Cobertura",es:"Cobertura",de:"Datenstand",fr:"Couverture",it:"Copertura",nl:"Dekking"})[lang]);
 document.querySelectorAll("[data-method-link]").forEach(el=>el.textContent=({en:"Methodology",pt:"Metodologia",es:"Metodología",de:"Methodik",fr:"Méthodologie",it:"Metodologia",nl:"Methodologie"})[lang]);
 document.querySelectorAll("[data-sources-link]").forEach(el=>el.textContent=({en:"Data sources",pt:"Fontes de dados",es:"Fuentes de datos",de:"Datenquellen",fr:"Sources de données",it:"Fonti dei dati",nl:"Gegevensbronnen"})[lang]);
 document.querySelectorAll("[data-about-link]").forEach(el=>el.textContent=({en:"About",pt:"Sobre",es:"Acerca de",de:"Über uns",fr:"À propos",it:"Informazioni",nl:"Over ons"})[lang]);document.documentElement.lang=TAGS[lang];$("lang").value=lang;$("lang").setAttribute("aria-label",navT("language"));document.querySelectorAll("[data-c]").forEach(e=>e.textContent=T(e.dataset.c));document.querySelectorAll("[data-t]").forEach(e=>e.textContent=navT(e.dataset.t));setCountries();setOccupations();if(last)renderResults(last)}
async function loadJobs(){const id=++serial;try{const d=await request("/v1/occupations?lang="+lang);if(id!==serial)return;if(Array.isArray(d.occupations)&&d.occupations.length)jobs=d.occupations}catch(_){/* Keep last language or default occupation. */}setOccupations()}
function regionOptions(side,rows){const select=$("region"+side),was=select.value;select.replaceChildren(option("","—"),...rows.map(x=>option(x.code,x.name)));if(rows.some(x=>x.code===was))select.value=was}
async function loadRegions(side){const country=$("country"+side).value,sel=$("region"+side),box=$("region"+side+"Box");box.hidden=true;sel.replaceChildren(option("","—"));
 try{const d=await request("/v1/regions/"+country);if(country!==$("country"+side).value)return;if(d.visible&&Array.isArray(d.options)&&d.options.length){regionOptions(side,d.options);box.hidden=false}}catch(_){}}
function taxAvailability(metadata){return Array.isArray(metadata?.scenarios)?metadata.scenarios.filter(x=>x&&x.id&&["verified","benchmark_estimate","partial"].includes(x.status)):[]}
async function loadTax(side){
 const country=$("country"+side).value,sel=$("taxScenario"+side),old=sel.value,fields=$("tax"+side+"Fields");
 meta[side]=null;sel.replaceChildren(option("",T("selectScenario")));fields.hidden=true;
 try{const data=await request("/v1/tax/assumptions/"+country);if(country!==$("country"+side).value)return;meta[side]=data;const list=taxAvailability(data);
 sel.replaceChildren(option("",list.length?T("selectScenario"):T("noScenario")),...list.map(x=>option(x.id,x.id+" · "+x.status)));
 if(list.some(x=>x.id===old))sel.value=old;renderTaxFields(side);
 }catch(_){sel.replaceChildren(option("",T("noScenario")))}
}
function taxOptions(side){return taxAvailability(meta[side]).find(x=>x.id===$("taxScenario"+side).value)}
function renderTaxFields(side){
 const scenario=taxOptions(side),box=$("tax"+side+"Fields"),yearSel=$("taxYear"+side),regionSel=$("taxRegion"+side),expenseBox=$("expenses"+side+"Box");
 box.hidden=!scenario;if(!scenario)return;
 const country=$("country"+side).value,years=[...new Set([...(scenario.supported_tax_years||[]),...(scenario.benchmark_tax_years||[]),...(meta[side]?.candidate_tax_years||[])].filter(x=>Number.isInteger(x)))].sort((a,b)=>b-a);
 const formerYear=yearSel.value;yearSel.replaceChildren(...years.map(y=>option(String(y),String(y))));if(years.includes(Number(formerYear)))yearSel.value=formerYear;
 const choices=Array.isArray(scenario.regions)?scenario.regions:[],old=regionSel.value;
 regionSel.replaceChildren(option("","—"),...choices.map(x=>option(x,x)));
 if(choices.includes(old))regionSel.value=old;
 regionSel.closest(".field").hidden=!choices.length;
 expenseBox.hidden=!Boolean(meta[side]?.inputs?.eligible_household_expenses&&country==="PT");
 if(!years.length){box.hidden=true;$("taxScenario"+side).value=""}
}
function emptyResult(){last=null;$("results").hidden=true;for(const id of ["paneGross","paneTax","paneSources"])$(id).replaceChildren()}
function switchTab(name){for(const item of ["Gross","Tax","Sources"]){const on=item===name;$("pane"+item).hidden=!on;$("tab"+item).setAttribute("aria-selected",String(on));$("tab"+item).tabIndex=on?0:-1}}
function present(container,heading,value,note){const c=node("div",undefined,"card");c.append(node("h3",heading),node("div",value,"num"));if(note)c.append(node("p",note,"muted"));container.append(c)}
function info(container,msg){container.append(node("div",msg,"notice"))}
function labelStatus(val){return val==="verified"?T("verified"):val==="benchmark_estimate"?T("benchmark"):val||T("unavailable")}
function renderGross(d){
 const pane=$("paneGross");pane.replaceChildren();const grid=node("div",undefined,"cards");const codeA=d.country_a?.country?.currency||currency($("countryA").value),codeB=d.country_b?.country?.currency||currency($("countryB").value);
 const grossA=Number(d.country_a?.tax_scenario?.annual_gross||$("grossA").value),grossB=d.country_b?.tax_scenario?.annual_gross??$("grossB").value;
 present(grid,T("grossAResult"),money(grossA,codeA),countryName(d.country_a?.country?.code||$("countryA").value));
 if(grossB!==""&&Number.isFinite(Number(grossB))&&Number(grossB)>0)present(grid,T("grossBResult"),money(Number(grossB),codeB),countryName(d.country_b?.country?.code||$("countryB").value));
 const p=d.gross_purchasing_power_equivalence;
 if(p?.status==="available"&&typeof p.value==="number"&&Number.isFinite(p.value)){
   present(grid,T("pppEquivalent"),money(p.value,p.currency||codeB),T("sourceYear")+": "+p.reference_year+" · World Bank");
   if(typeof p.destination_offer_difference_percent==="number")present(grid,T("offerDifference"),percent(p.destination_offer_difference_percent),T("grossCaution"));
 }else info(pane,T("missingPpp")+(p?.reason?" · "+p.reason:""));
 pane.append(grid);pane.append(node("p",T("grossCaution"),"muted"));
}
function renderTax(d){
 const pane=$("paneTax");pane.replaceChildren();
 const grid=node("div",undefined,"cards"),a=d.country_a?.tax_scenario||{},b=d.country_b?.tax_scenario||{};
 for(const [x,label,currencyCode] of [[a,T("netA"),d.country_a?.country?.currency],[b,T("netB"),d.country_b?.country?.currency]]){
  const supported=["verified","benchmark_estimate"].includes(x.status)&&x.net_income!==null&&Number.isFinite(Number(x.net_income));
  present(grid,label,supported?money(Number(x.net_income),currencyCode):T("unavailable"),labelStatus(x.status)+(x.tax_year?" · "+x.tax_year:""));
 }
 const p=d.net_purchasing_power;
 if(["verified_models","benchmark_estimate"].includes(p?.status)&&Number.isFinite(p?.origin_net_equivalent_in_destination_currency)){
   present(grid,T("netPPP"),money(p.origin_net_equivalent_in_destination_currency,p.currency),T("sourceYear")+": "+p.ppp_reference_year);
   if(Number.isFinite(p.destination_net_difference_percent))present(grid,T("netDifference"),percent(p.destination_net_difference_percent),T("taxNotice"));
 }else info(pane,T("missingNet")+(p?.reason?" · "+p.reason:""));
 pane.append(grid);pane.append(node("p",T("taxNotice"),"muted"));
}
function sourceCard(container,label,item){
 const card=node("article",undefined,"source-row");card.append(node("strong",label));
 const details=[item?.source||item?.underlying_source,item?.year||item?.published_year||item?.latest_period,item?.unit,item?.status].filter(x=>x!==undefined&&x!==null&&x!=="");card.append(node("p",details.length?details.join(" · "):T("notCalculated"),"muted"));
 const url=item?.source_url;if(typeof url==="string"){try{const u=new URL(url);if(u.protocol==="https:"){const link=node("a",navT("sourceLink"));link.href=u.href;link.target="_blank";link.rel="noopener noreferrer";card.append(link)}}catch(_){}}
 container.append(card);
}
function renderSources(d){
 const pane=$("paneSources");pane.replaceChildren();pane.append(node("p",T("sourcesHint"),"muted"));
 for(const [side,countryLabel] of [[d.country_a,T("from")],[d.country_b,T("to")]]){
  const c=side?.country?.code||"",heading=node("h3",countryLabel+" — "+countryName(c));pane.append(heading);
  sourceCard(pane,T("grossAResult"),side?.national_occupation_wage);
  sourceCard(pane,T("taxScenario"),side?.tax_scenario);
 }
 const p=d.gross_purchasing_power_equivalence;
 if(p){sourceCard(pane,T("pppEquivalent"),{source:p.source,year:p.reference_year,status:p.status,source_url:p.source_urls?.[0]});if(p.source_urls?.[1])sourceCard(pane,T("to"),{source:p.source,year:p.reference_year,status:p.status,source_url:p.source_urls[1]})}
 pane.append(node("p",T("grossDisclaimer"),"muted"));
}
function renderResults(data){$("results").hidden=false;renderGross(data);renderTax(data);renderSources(data);switchTab(document.querySelector('.tab[aria-selected="true"]')?.id.replace("tab","")||"Gross")}
function amount(id,optional=false){
 const raw=$(id).value.trim();if(!raw&&optional)return null;
 const num=Number(raw);return Number.isFinite(num)&&num>0&&num<=100000000?num:NaN
}
function taxParams(params,side,code){
 const scenario=$("taxScenario"+side).value;if(!scenario)return;
 const year=$("taxYear"+side).value, region=$("taxRegion"+side).value,expenses=$("expenses"+side).value.trim();
 if(!year)throw Error(T("taxNotice"));
 params.set("tax_scenario_"+side.toLowerCase(),scenario);
 params.set("net_tax_year_"+side.toLowerCase(),year);
 if(region)params.set("tax_region_"+side.toLowerCase(),region);
 if(code==="PT"&&expenses)params.set("eligible_household_expenses_"+side.toLowerCase(),expenses);
}
let pending=0;
async function compare(event){
 event?.preventDefault();const a=amount("grossA"),b=amount("grossB",true),output=$("results");
 if(Number.isNaN(a)||Number.isNaN(b)){output.hidden=false;info($("paneGross"),T("invalidGross"));switchTab("Gross");return}
 if(!Number.isFinite(a)){output.hidden=false;info($("paneGross"),T("missingGrossA"));switchTab("Gross");return}
 const button=$("submit"),req=++pending;button.disabled=true;button.textContent=T("loading");
 const codeA=$("countryA").value,codeB=$("countryB").value;
 try{
  const q=new URLSearchParams({country_a:codeA,country_b:codeB,occupation:$("occupation").value,annual_gross_a:String(a)});
  if(b!==null)q.set("annual_gross_b",String(b));
  for(const side of ["A","B"]){const region=$("region"+side).value;if(region)q.set("region_"+side.toLowerCase(),region)}
  taxParams(q,"A",codeA);if(b!==null)taxParams(q,"B",codeB);
  else if($("taxScenarioB").value)throw Error(T("grossB"));
  const d=await request("/v1/earnwage/compare?"+q.toString());if(req!==pending)return;
  d.gross_purchasing_power_equivalence=await window.EarnWagePPP.ensure(d.gross_purchasing_power_equivalence,codeA,codeB,a,b,request);
  if(req!==pending)return;
  last=d;renderResults(d);output.scrollIntoView({behavior:"smooth",block:"start"});
 }catch(e){if(req!==pending)return;output.hidden=false;$("paneGross").replaceChildren();info($("paneGross"),T("requestFailed")+" "+e.message);switchTab("Gross")}
 finally{if(req===pending){button.disabled=false;button.textContent=T("calculate")}}
}
async function onCountry(side){$("currency"+side).textContent=currency($("country"+side).value);await Promise.all([loadRegions(side),loadTax(side)])}
function swap(){for(const id of ["country","gross","region","taxScenario","taxRegion","taxYear","expenses"]){const left=$(id+"A"),right=$(id+"B");if(!left||!right)continue;const a=left.value;left.value=right.value;right.value=a}onCountry("A");onCountry("B");emptyResult()}
function bind(){
 $("compareForm").addEventListener("submit",compare);
 $("swap").addEventListener("click",swap);
 $("reset").addEventListener("click",emptyResult);
 $("countryA").addEventListener("change",()=>{onCountry("A");emptyResult()});
 $("countryB").addEventListener("change",()=>{onCountry("B");emptyResult()});
 for(const side of ["A","B"])$("taxScenario"+side).addEventListener("change",()=>renderTaxFields(side));
 for(const name of ["Gross","Tax","Sources"])$("tab"+name).addEventListener("click",()=>switchTab(name));
 $("lang").addEventListener("change",async e=>{lang=e.target.value;try{localStorage.setItem("earnwage_lang",lang)}catch(_){}applyLang();await loadJobs();for(const side of ["A","B"])renderTaxFields(side)});
}
async function init(){
 bind();applyLang();
 try{const rows=await request("/v1/countries");if(Array.isArray(rows.countries)&&rows.countries.length)countries=rows.countries.filter(x=>x.code&&x.name&&x.currency)}catch(_){}
 setCountries();await loadJobs();
 const params=new URLSearchParams(location.search);
 for(const [key,id] of [["country_a","countryA"],["country_b","countryB"]]){const c=params.get(key);if(c&&countries.some(x=>x.code===c))$(id).value=c}
 const occupation=params.get("occupation");if(occupation&&jobs.some(x=>x.id===occupation))$("occupation").value=occupation;
 const grossA=params.get("annual_gross_a"),grossB=params.get("annual_gross_b");
 if(grossA&&Number.isFinite(Number(grossA))&&Number(grossA)>0)$("grossA").value=grossA;
 if(grossB&&Number.isFinite(Number(grossB))&&Number(grossB)>0)$("grossB").value=grossB;
 await Promise.all([onCountry("A"),onCountry("B")]);
}
init();
