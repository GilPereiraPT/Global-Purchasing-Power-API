"use strict";
/* Data-specific country guides: no invented salary values or client-side conversions. */
(() => {
const LABELS={"en":{"section":"Salary evidence in this country","intro":"Choose a profession to see only the observations returned by EarnWage. Unavailable values are not estimated.","choose":"Profession","exact":"Occupation-specific gross wage","entry":"Public-sector entry salary","group":"Occupational-group context (not this profession's salary)","unavailable":"No validated value available","loading":"Checking published data…","failed":"The API did not return data. No value is inferred.","year":"Reference period","source":"Source","groups":"Explore official wage groups","compare":"Compare with another country","method":"Methodology","links":"Country guides with additional wage context","help":"The measure, currency and period are preserved from the original source.","hour":"per hour","yearUnit":"per year","month":"per month"},"pt":{"section":"Dados salariais deste país","intro":"Selecione uma profissão para consultar apenas os valores devolvidos pelo EarnWage. Os valores indisponíveis não são estimados.","choose":"Profissão","exact":"Salário bruto específico da profissão","entry":"Remuneração de entrada na função pública","group":"Contexto do grupo profissional (não é o salário da profissão)","unavailable":"Sem valor validado disponível","loading":"A consultar os dados publicados…","failed":"A API não devolveu dados. Não é apresentado qualquer valor estimado.","year":"Período de referência","source":"Fonte","groups":"Explorar salários oficiais por grupo","compare":"Comparar com outro país","method":"Metodologia","links":"Guias por país com informação salarial adicional","help":"Mantêm-se a medida, a moeda e o período publicados pela fonte original.","hour":"por hora","yearUnit":"por ano","month":"por mês"},"es":{"section":"Datos salariales de este país","intro":"Selecciona una profesión para consultar únicamente los datos de EarnWage. No estimamos valores ausentes.","choose":"Profesión","exact":"Salario bruto específico de la profesión","entry":"Salario de entrada al sector público","group":"Contexto del grupo profesional (no es el salario de la profesión)","unavailable":"Sin datos validados disponibles","loading":"Consultando los datos publicados…","failed":"La API no devolvió datos. No se infiere ningún valor.","year":"Periodo de referencia","source":"Fuente","groups":"Explorar salarios oficiales por grupos","compare":"Comparar con otro país","method":"Metodología","links":"Guías de países con contexto salarial adicional","help":"Se conservan la medida, la moneda y el periodo originales.","hour":"por hora","yearUnit":"por año","month":"por mes"},"de":{"section":"Gehaltsdaten in diesem Land","intro":"Wählen Sie einen Beruf. Fehlende Werte werden nicht geschätzt.","choose":"Beruf","exact":"Bruttoverdienst für den Beruf","entry":"Einstiegsgehalt im öffentlichen Dienst","group":"Berufsgruppenkontext (kein Gehalt dieses Berufs)","unavailable":"Keine validierten Daten verfügbar","loading":"Veröffentlichte Daten werden geprüft…","failed":"Keine API-Daten verfügbar. Es werden keine Werte geschätzt.","year":"Bezugszeitraum","source":"Quelle","groups":"Amtliche Berufsgruppen erkunden","compare":"Mit anderem Land vergleichen","method":"Methodik","links":"Länderleitfäden mit zusätzlichen Gehaltsdaten","help":"Maß, Währung und Zeitraum der Quelle bleiben erhalten.","hour":"pro Stunde","yearUnit":"pro Jahr","month":"pro Monat"},"fr":{"section":"Données salariales de ce pays","intro":"Choisissez un métier. Aucune valeur manquante n'est estimée.","choose":"Métier","exact":"Salaire brut du métier","entry":"Salaire d'entrée dans le secteur public","group":"Groupe professionnel (pas le salaire de ce métier)","unavailable":"Aucune donnée validée","loading":"Consultation des données publiées…","failed":"Données API indisponibles. Aucune valeur estimée.","year":"Période de référence","source":"Source","groups":"Explorer les salaires par groupe","compare":"Comparer avec un autre pays","method":"Méthodologie","links":"Guides pays et contexte salarial","help":"Mesure, devise et période d'origine conservées.","hour":"par heure","yearUnit":"par an","month":"par mois"},"it":{"section":"Dati retributivi del paese","intro":"Seleziona una professione. Nessuna stima dei valori mancanti.","choose":"Professione","exact":"Retribuzione lorda per professione","entry":"Retribuzione iniziale nel settore pubblico","group":"Contesto del gruppo (non è lo stipendio della professione)","unavailable":"Nessun dato verificato disponibile","loading":"Verifica dei dati pubblicati…","failed":"API non disponibile. Nessun valore stimato.","year":"Periodo di riferimento","source":"Fonte","groups":"Esplora i gruppi professionali","compare":"Confronta con un altro paese","method":"Metodologia","links":"Guide paese con dati retributivi aggiuntivi","help":"Misura, valuta e periodo originali conservati.","hour":"all'ora","yearUnit":"all'anno","month":"al mese"},"nl":{"section":"Loongegevens voor dit land","intro":"Kies een beroep. Ontbrekende waarden worden niet geschat.","choose":"Beroep","exact":"Brutoloon voor dit beroep","entry":"Startsalaris publieke sector","group":"Beroepsgroep (niet het loon van dit beroep)","unavailable":"Geen gevalideerde gegevens","loading":"Gepubliceerde gegevens worden opgehaald…","failed":"API-gegevens ontbreken. Geen schatting gemaakt.","year":"Referentieperiode","source":"Bron","groups":"Officiële beroepsgroepen bekijken","compare":"Vergelijk met een ander land","method":"Methodologie","links":"Landengidsen met extra looninformatie","help":"Maatstaf, valuta en periode van de bron blijven behouden.","hour":"per uur","yearUnit":"per jaar","month":"per maand"}};
const GUIDES={"ES":{"name":"España","code":"ES","flag":"🇪🇸","defaultJob":"accountant","source":"Instituto Nacional de Estadística (INE), Encuesta Anual de Estructura Salarial","url":"https://www.ine.es/jaxiT3/Tabla.htm?t=28186","period":"2008–2024","currency":"EUR","note":{"en":"Spain's INE EAES table 28186 reports national gross annual means for broad CNO-11 occupational groups, not salaries for individual professions. Data are published through 2024; suppressed figures are not filled in.","pt":"A tabela 28186 da EAES do INE espanhol apresenta médias salariais brutas anuais nacionais por grandes grupos CNO-11, e não salários de profissões individuais. Os dados vão até 2024; os valores suprimidos não são preenchidos.","es":"La tabla 28186 de la EAES del INE publica salarios medios brutos anuales nacionales por grandes grupos CNO-11, no salarios de profesiones individuales. Los datos llegan a 2024 y no se sustituyen cifras suprimidas.","de":"Die INE-EAES-Tabelle 28186 enthält nationale Bruttojahresmittelwerte breiter CNO-11-Berufsgruppen, keine Gehälter einzelner Berufe. Verfügbare Jahre reichen bis 2024.","fr":"Le tableau 28186 de l'INE EAES présente les moyennes annuelles brutes nationales de grands groupes CNO-11, et non des salaires par métier. La série va jusqu'en 2024.","it":"La tabella INE EAES 28186 riporta medie nazionali lorde annue di grandi gruppi CNO-11, non stipendi di singole professioni. La serie arriva al 2024.","nl":"INE EAES-tabel 28186 geeft nationale gemiddelde bruto jaarlonen voor brede CNO-11-beroepsgroepen, niet voor afzonderlijke beroepen. De reeks loopt tot 2024."}},"IE":{"name":"Ireland","code":"IE","flag":"🇮🇪","defaultJob":"nurse","source":"Health Service Executive (HSE), Consolidated Salary Scales","url":"https://healthservice.hse.ie/documents/10686/1_June_2026_pay_scales.pdf","period":"2026","currency":"EUR","note":{"en":"Ireland has official entry-grade salary references for selected public-sector careers (HSE and other public employers). These are not private-market averages. CSO SES 2022 hourly figures provide separate, broader occupational-group context.","pt":"A Irlanda dispõe de referências oficiais de remuneração de entrada para determinadas carreiras públicas (HSE e outros empregadores públicos). Não são médias do mercado privado. Os valores horários da CSO SES 2022 constituem contexto separado de grupos profissionais.","es":"Irlanda dispone de escalas oficiales de entrada para determinadas carreras del sector público (HSE y otras entidades). No son medias del mercado privado. Las cifras horarias CSO SES 2022 son contexto de grupos amplios.","de":"Irland hat amtliche Einstiegsgehälter für ausgewählte öffentliche Laufbahnen (HSE und weitere Behörden). Es sind keine privaten Marktmittelwerte. CSO SES 2022 liefert gesonderten Kontext breiter Berufsgruppen.","fr":"L'Irlande publie des salaires d'entrée officiels pour certaines carrières publiques (HSE et autres employeurs). Ce ne sont pas des moyennes privées. L'enquête CSO SES 2022 présente séparément des groupes plus larges.","it":"L'Irlanda pubblica retribuzioni iniziali ufficiali per alcune carriere pubbliche (HSE e altri enti). Non sono medie del mercato privato. CSO SES 2022 offre il contesto di gruppi professionali più ampi.","nl":"Ierland publiceert officiële startsalarissen voor geselecteerde functies in de publieke sector (HSE en andere werkgevers), geen gemiddelde private lonen. CSO SES 2022 biedt afzonderlijke context voor brede beroepsgroepen."}},"GB":{"name":"United Kingdom","code":"GB","flag":"🇬🇧","defaultJob":"software_developer","source":"Office for National Statistics (ONS), Annual Survey of Hours and Earnings, Table 14","url":"https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/occupation4digitsoc2010ashetable14/2025provisional","period":"2025 (provisional)","currency":"GBP","note":{"en":"ONS ASHE Table 14 provides 2025 provisional annual gross wages for selected occupations with validated one-to-one SOC 2020 mappings. Suppressed estimates and excessively imprecise measures remain unavailable. These are not 2026 pay offers.","pt":"A tabela 14 do ONS ASHE disponibiliza remunerações brutas anuais provisórias de 2025 para profissões com correspondência direta validada ao SOC 2020. Estimativas suprimidas ou demasiado imprecisas permanecem indisponíveis. Não são ofertas salariais de 2026.","es":"La tabla 14 del ONS ASHE publica salarios brutos anuales provisionales de 2025 para profesiones con equivalencia SOC 2020 validada. Los datos suprimidos o imprecisos no se muestran. No son ofertas de 2026.","de":"ONS ASHE Tabelle 14 enthält vorläufige Bruttojahresverdienste 2025 für validierte direkte SOC-2020-Berufscodes. Unterdrückte oder zu ungenaue Werte bleiben nicht verfügbar. Keine Stellenangebote für 2026.","fr":"Le tableau 14 de l'ONS ASHE fournit des salaires annuels bruts provisoires de 2025 pour des métiers associés directement au SOC 2020. Les données supprimées ou trop imprécises restent absentes. Il ne s'agit pas d'offres 2026.","it":"La tabella 14 di ONS ASHE pubblica retribuzioni lorde annue provvisorie 2025 per professioni con codici SOC 2020 validati. I dati soppressi o imprecisi restano indisponibili. Non sono offerte 2026.","nl":"ONS ASHE tabel 14 bevat voorlopige bruto jaarlonen 2025 voor beroepen met gevalideerde directe SOC 2020-koppeling. Onderdrukte of onnauwkeurige waarden blijven ontbreken. Dit zijn geen vacaturesalarissen voor 2026."}}};
const LOCALES={en:"en-GB",pt:"pt-PT",es:"es-ES",de:"de-DE",fr:"fr-FR",it:"it-IT",nl:"nl-NL"};
let generation=0;
const text=(tag,value,cls)=>{const e=document.createElement(tag);if(value!==undefined)e.textContent=String(value);if(cls)e.className=cls;return e;};
function safeUrl(url){try{const u=new URL(url);return u.protocol==="https:"?u.href:null}catch(_){return null}}
function action(label,url){const e=text("a",label,"secondary");e.href=url;return e}
function external(label,url){const href=safeUrl(url);if(!href)return null;const a=text("a",label);a.href=href;a.target="_blank";a.rel="noopener noreferrer";return a}
function take(record){
 if(record?.status!=="available")return null;
 const list=Array.isArray(record.observations)?record.observations.filter(o=>o&&Number.isFinite(o.value)&&o.value>0):[];
 const preferred=list.find(o=>o.measure==="median")||list.find(o=>o.measure==="mean")||list[0];
 if(preferred)return {...preferred,source_url:preferred.source_url||record.source_url,source:preferred.source||record.source,source_label:preferred.source_label||record.source_label};
 return Number.isFinite(record.value)&&record.value>0?record:null;
}
function amount(record,lang,copy){
 const code=record.currency;
 let value;
 try{value=new Intl.NumberFormat(LOCALES[lang]||"en-GB",{style:"currency",currency:code,maximumFractionDigits:2}).format(record.value)}
 catch(_){value=record.value+" "+(code||"")}
 const unit=String(record.unit||"");
 return value+(unit.includes("hour")?" / "+copy.hour:unit.includes("year")?" / "+copy.yearUnit:unit.includes("month")?" / "+copy.month:"");
}
function card(label,record,lang,copy,extra){
 const c=text("article",undefined,"card");
 c.append(text("h3",label));
 const chosen=take(record);
 c.append(text("div",chosen?amount(chosen,lang,copy):copy.unavailable,"metric"));
 if(chosen){
  const note=[extra||chosen.source_label||"",chosen.reference_period||chosen.period||record.period||"",chosen.measure||record.measure||""].filter(Boolean).join(" · ");
  if(note)c.append(text("p",note,"muted"));
  const source=external(copy.source,chosen.source_url||record.source_url);
  if(source)c.append(source);
 }
 return c;
}
function selectOccupation(occupations,defaultJob){
 const s=document.createElement("select");s.id="guideOccupation";s.setAttribute("aria-label","Profession");
 const items=Array.isArray(occupations)&&occupations.length?occupations:[{id:defaultJob,label:defaultJob}];
 s.replaceChildren(...items.filter(o=>o&&o.id).map(o=>{const op=document.createElement("option");op.value=o.id;op.textContent=o.label||o.id;return op}));
 s.value=items.some(o=>o.id===defaultJob)?defaultJob:items[0].id;
 return s;
}
function render({code,language,occupations,api,container}){
 if(!container)return;
 const config=GUIDES[code];const token=++generation;
 container.replaceChildren();
 if(!config){container.hidden=true;return}
 container.hidden=false;
 const lang=LABELS[language]?language:"en",copy=LABELS[lang],note=config.note[lang]||config.note.en;
 container.append(text("h2",config.flag+" "+copy.section));
 container.append(text("p",note,"muted"));
 const meta=text("p",config.source+" · "+config.period,"muted");container.append(meta);
 const source=external(copy.source,config.url);if(source)container.append(source);
 const description=text("p",copy.intro,"muted");container.append(description);
 const field=text("div",undefined,"field"),label=text("label",copy.choose);label.htmlFor="guideOccupation";
 const chooser=selectOccupation(occupations,config.defaultJob);field.append(label,chooser);container.append(field);
 const result=text("div",undefined,"cards");result.setAttribute("aria-live","polite");container.append(result);
 const actions=text("div",undefined,"actions"),compare=action(copy.compare,"./compare.html?country_a="+code);
 actions.append(compare,action(copy.method,"./methodology.html"));
 if(code==="ES")actions.append(action(copy.groups,"./wage-groups.html?country=ES"));
 container.append(actions,text("p",copy.help,"muted"));
 async function refresh(){
  const id=++generation,occupation=chooser.value;
  compare.href="./compare.html?country_a="+encodeURIComponent(code)+"&occupation="+encodeURIComponent(occupation);
  result.replaceChildren(text("div",copy.loading,"notice"));
  try{
   const data=await api("/v1/earnwage/overview?"+new URLSearchParams({country:code,occupation}));
   if(token>id||id!==generation||container.hidden)return;
   result.replaceChildren();
   result.append(card(copy.exact,data.national_occupation_wage,lang,copy));
   if(code==="IE"){
    result.append(card(copy.entry,data.ireland_public_sector_entry,lang,copy));
    const group=data.ireland_cso_occupational_group_context;
    const median=group?.values?.median;
    result.append(card(copy.group,median?.value!=null?{...median,status:group.status,source:group.source,source_url:group.source_url,period:group.period,source_label:group.source_label}:null,lang,copy,group?.source_label||""));
   }
  }catch(_){if(token<=id&&id===generation&&!container.hidden)result.replaceChildren(text("div",copy.failed,"notice"))}
 }
 chooser.addEventListener("change",refresh);
 refresh();
}
function renderLinks(language,container){
 if(!container)return;
 const lang=LABELS[language]?language:"en",copy=LABELS[lang];
 container.replaceChildren(text("h2",copy.links));
 const grid=text("div",undefined,"cards");
 for(const c of Object.values(GUIDES)){
  const box=text("article",undefined,"card");
  const link=external(c.flag+" "+c.name,null)||action(c.flag+" "+c.name,"./country.html?country="+encodeURIComponent(c.code));
  box.append(text("h3",undefined));
  box.lastElementChild.append(link);
  box.append(text("p",c.note[lang]||c.note.en,"muted"));
  grid.append(box);
 }
 container.append(grid);
}
window.EarnWageCountryGuides=Object.freeze({render,renderLinks});
const links=document.getElementById("countryGuidesLinks");
if(links){
 const select=document.getElementById("lang");
 function currentLang(){
  let stored=null;try{stored=localStorage.getItem("earnwage_lang")}catch(_){}
  const user=stored||(navigator.language||"en").slice(0,2).toLowerCase();
  return LABELS[select?.value]&&select.value!=="en"?select.value:(LABELS[user]?user:"en");
 }
 renderLinks(currentLang(),links);
 select?.addEventListener("change",()=>renderLinks(select.value,links));
}
})();
