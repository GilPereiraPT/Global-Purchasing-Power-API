/* Official EarnWage country dashboard. Reads existing public API only.
 * Each indicator is independent, with its original year, unit and source.
 * Histories load on demand; no interpolated periods or composite rankings.
 */
(() => {
 "use strict";
 const GROUPS=[
  {key:"demography",symbol:"👥",items:["population_total","population_growth","urban_population","population_ages_0_14","population_ages_65_plus","fertility_rate","birth_rate","death_rate"]},
  {key:"geography",symbol:"🌍",items:["surface_area","land_area","population_density"]},
  {key:"economy",symbol:"📈",items:["gdp_per_capita","inflation_annual","ppp_private_consumption","gini"]},
  {key:"employment",symbol:"💼",items:["unemployment","youth_unemployment","employment_population_ratio","advanced_education_unemployment"]},
  {key:"health",symbol:"🩺",items:["life_expectancy","health_coverage","physicians","hospital_beds","out_of_pocket_health_expenditure"]},
  {key:"living",symbol:"🏡",items:["electricity_access","safe_drinking_water","safe_sanitation","internet_use","pm25_air_pollution"]},
  {key:"education",symbol:"🎓",items:["primary_completion","adult_literacy"]},
  {key:"safety",symbol:"🛡️",items:["intentional_homicides","intentional_homicides_female","intentional_homicides_male","political_stability","battle_related_deaths"]},
  {key:"governance",symbol:"⚖️",items:["rule_of_law","control_of_corruption","bribery_incidence_firms","tax_official_gifts_firms"]},
 ];
 const CODES=["PT","ES","DE","FR","GB","IE","NL","CH","IT","US","CA","BR","IN","PK"];
 const KNOWN=new Set(CODES);
 const ALL=GROUPS.flatMap(g=>g.items);
 const LABELS=window.EarnWageCountryDataLocale||{};
 const localeTags={en:"en-GB",pt:"pt-PT",es:"es-ES",de:"de-DE",fr:"fr-FR",it:"it-IT",nl:"nl-NL"};
 const sourceLink=v=>{try{const u=new URL(v);return u.protocol==="https:"?u.href:null}catch(_){return null}};
 const make=(tag,cls,content)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(content!==undefined)e.textContent=String(content);return e};
 const msg=(lang,key)=>LABELS[lang]?.[key]||LABELS.en?.[key]||key;
 const metricName=(key,lang)=>LABELS[lang]?.metric?.[key]||LABELS.en?.metric?.[key]||key;
 function flag(code) {
   if(!KNOWN.has(code))return "🏳️";
   return String.fromCodePoint(...[...code].map(char=>127397+char.charCodeAt(0)));
 }
 function display(code,lang="en") {
   if(!KNOWN.has(code))return code;
   let name=code;
   try{name=new Intl.DisplayNames([localeTags[lang]||"en-GB"],{type:"region"}).of(code)||code}catch(_){}
   return flag(code)+" "+name;
 }
 function validRecord(r) {
   return !!(r&&r.status==="available"&&typeof r.value==="number"&&Number.isFinite(r.value)&&
     Number.isInteger(r.year)&&r.year>=1960&&r.year<=2100);
 }
 function formatValue(r,lang) {
   if(!validRecord(r))return msg(lang,"missing");
   const value=new Intl.NumberFormat(localeTags[lang]||"en-GB",{maximumFractionDigits:2}).format(r.value);
   if(r.unit==="persons")return value;
   if(r.unit==="square_km")return value+" km²";
   if(r.unit==="people_per_square_km_land")return value+" / km²";
   if(r.unit==="births_per_woman")return value+" "+(lang==="pt"?"nascimentos/mulher":"births/woman");
   if(r.unit==="births_per_1000_people"||r.unit==="deaths_per_1000_people")return value+" / 1 000";
   if(r.unit==="USD_current_per_person")return value+" USD";
   if(r.unit==="years")return value+" "+(lang==="pt"?"anos":"years");
   if(r.unit==="micrograms_per_cubic_meter")return value+" µg/m³";
   if(r.unit==="per_1000_people")return value+" / 1 000";
   if(r.unit==="per_100000_people"||r.unit==="per_100000_female"||r.unit==="per_100000_male")return value+" / 100 000";
   if(r.unit==="index_0_100"||r.unit==="governance_score_0_100")return value+" / 100";
   if(r.unit==="index_0_100")return value+" / 100";
   if(r.unit==="annual_percent"||r.unit?.startsWith("percent_"))return value+"%";
   if(r.unit==="local_currency_units_per_international_dollar")return value+" "+(lang==="pt"?"unid. locais/Int$":"local units/Int$");
   return value+(r.unit==="persons"?"":"");
 }
 function metaText(r,lang){
   const result=[];
   if(Number.isInteger(r?.year))result.push(msg(lang,"year")+": "+r.year);
   if(r?.unit)result.push(r.unit);
   if(r?.underlying_source)result.push(r.underlying_source);
   else if(r?.source)result.push(r.source);
   return result.join(" · ");
 }
 function metricTile(key,record,context){
   const {language:lang,code,onHistory}=context;
   const card=make("article","ci-metric"+(validRecord(record)?"":" ci-unavailable"));
   const header=make("div","ci-card-head");
   header.append(make("h3","",metricName(key,lang)));
   if(validRecord(record))header.append(make("span","ci-year",String(record.year)));
   card.append(header,make("div","ci-value",formatValue(record,lang)));
   const m=make("p","ci-meta",metaText(record,lang));
   if(m.textContent)card.append(m);
   const actions=make("div","ci-card-actions");
   if(validRecord(record)){
     const button=make("button","ci-action",msg(lang,"history"));button.type="button";
     button.addEventListener("click",()=>onHistory(key,button));actions.append(button);
   }
   const url=sourceLink(record?.source_url);
   if(url){const a=make("a","ci-source",msg(lang,"directSource"));a.href=url;a.target="_blank";a.rel="noopener noreferrer";actions.append(a)}
   if(actions.childElementCount)card.append(actions);
   return card;
 }
 function chart(raw,key,lang) {
   const data=(Array.isArray(raw.history)?raw.history:[]).filter(r=>r&&
     Number.isInteger(r.year)&&r.year>=1960&&r.year<=2100&&typeof r.value==="number"&&Number.isFinite(r.value))
     .sort((a,b)=>a.year-b.year);
   const panel=make("div","ci-chart-zone");
   if(!data.length){panel.append(make("p","ci-missing",msg(lang,"historyMissing")));return panel}
   const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
   svg.setAttribute("viewBox","0 0 820 300");svg.setAttribute("role","img");
   svg.setAttribute("aria-label",metricName(key,lang));
   const line=(tag,attrs,text)=>{
     const node=document.createElementNS("http://www.w3.org/2000/svg",tag);
     for(const [k,v]of Object.entries(attrs))node.setAttribute(k,String(v));
     if(text!==undefined)node.textContent=String(text);
     svg.append(node);
     return node;
   };
   const ys=data.map(r=>r.value),xs=data.map(r=>r.year),min=Math.min(...ys),max=Math.max(...ys);
   const pad=Math.max((max-min)*.12,Math.abs(max)*.025,.05),floor=min-pad,ceil=max+pad;
   const minYear=Math.min(...xs),maxYear=Math.max(...xs);
   const x=year=>70+(year-minYear)/Math.max(1,maxYear-minYear)*695;
   const y=value=>249-(value-floor)/(ceil-floor)*207;
   for(let i=0;i<=4;i++){
     const value=floor+(ceil-floor)*i/4,pos=y(value);
     line("line",{x1:70,x2:770,y1:pos,y2:pos,stroke:"#d9e8e7","stroke-width":1});
     line("text",{x:6,y:pos+4,fill:"#57747a","font-size":12},new Intl.NumberFormat(localeTags[lang],{maximumFractionDigits:1}).format(value));
   }
   for(const year of [...new Set([minYear,Math.round((minYear+maxYear)/2),maxYear])])
     line("text",{x:x(year),y:281,"text-anchor":"middle",fill:"#57747a","font-size":12},year);
   for(let i=0;i<data.length-1;i++){
     if(data[i+1].year!==data[i].year+1)continue; // break every real missing year
     line("line",{x1:x(data[i].year),y1:y(data[i].value),x2:x(data[i+1].year),y2:y(data[i+1].value),stroke:"#168a79","stroke-width":2.8});
   }
   for(const r of data){
     const point=line("circle",{cx:x(r.year),cy:y(r.value),r:3.6,fill:"#0d8171"});
     const tooltip=document.createElementNS("http://www.w3.org/2000/svg","title");
     tooltip.textContent=r.year+": "+new Intl.NumberFormat(localeTags[lang],{maximumFractionDigits:3}).format(r.value);
     point.append(tooltip);
   }
   panel.append(svg);
   const note=make("p","ci-note",msg(lang,"historicalNote")+" · "+data.length+" "+msg(lang,"observationCount"));
   panel.append(note);
   if(raw.source_url){
     const url=sourceLink(raw.source_url);
     if(url){const a=make("a","ci-source",msg(lang,"directSource"));a.href=url;a.rel="noopener noreferrer";a.target="_blank";panel.append(a)}
   }
   const table=make("details","ci-history-table");
   table.append(make("summary","",msg(lang,"expand")+" · "+msg(lang,"yearLabel")));
   const wrapper=make("div","ci-table-scroll");
   const t=make("table","ci-table"),head=make("thead"),header=make("tr");
   header.append(make("th","",msg(lang,"yearLabel")),make("th","",msg(lang,"valueLabel")));
   head.append(header);t.append(head);const body=make("tbody");
   for(const r of data.slice().reverse()){const row=make("tr");row.append(make("td","",r.year),make("td","",new Intl.NumberFormat(localeTags[lang],{maximumFractionDigits:4}).format(r.value)));body.append(row)}
   t.append(body);wrapper.append(t);table.append(wrapper);panel.append(table);
   return panel;
 }
 async function showCountry({code,language="en",container,request,country}){
   if(!container||!KNOWN.has(code)||typeof request!=="function")return;
   const lang=LABELS[language]?language:"en",generation=(container._ciGeneration||0)+1;
   container._ciGeneration=generation;
   container.replaceChildren(make("p","ci-loading",msg(lang,"loading")));
   try {
     const payload=await request("/v1/countries/"+encodeURIComponent(code)+"/indicators");
     if(container._ciGeneration!==generation)return;
     if(payload?.country!==code||!payload.indicators||typeof payload.indicators!=="object")throw Error("Invalid indicator response");
     const records=payload.indicators,available=ALL.filter(key=>validRecord(records[key])).length;
     container.replaceChildren();
     const hero=make("div","ci-country-hero");
     const brand=make("div","ci-flag",""+flag(code));brand.setAttribute("aria-hidden","true");
     const title=make("div","ci-hero-main");
     const name=make("h2","",display(code,lang).replace(flag(code)+" ",""));
     title.append(name,make("p","",[
       country?.capital?msg(lang,"capital")+": "+country.capital:"",
       country?.currency?msg(lang,"currency")+": "+country.currency:""
     ].filter(Boolean).join(" · ")));
     const coverage=make("div","ci-counter",String(available)+" / "+ALL.length);
     coverage.append(make("span","",msg(lang,"available")));
     hero.append(brand,title,coverage);
     container.append(hero,make("p","ci-note",msg(lang,"countryNote")));
     const historyArea=make("section","ci-history-panel");historyArea.hidden=true;
     historyArea.id="ciHistoryPanel";
     historyArea.setAttribute("aria-live","polite");
     let historyIndex=0;
     async function onHistory(key,button){
       const requestId=++historyIndex;
       historyArea.hidden=false;historyArea.replaceChildren();
       const head=make("div","ci-history-head");
       head.append(make("h3","",metricName(key,lang)));
       const close=make("button","ci-action",msg(lang,"close"));close.type="button";close.addEventListener("click",()=>{historyIndex++;historyArea.hidden=true;historyArea.replaceChildren()});
       head.append(close);historyArea.append(head,make("p","ci-loading",msg(lang,"historyLoading")));
       historyArea.scrollIntoView({behavior:"smooth",block:"nearest"});
       try {
         const data=await request("/v1/countries/"+encodeURIComponent(code)+"/indicators/"+encodeURIComponent(key)+"?history=true");
         if(container._ciGeneration!==generation||requestId!==historyIndex)return;
         if(data?.country!==code||data?.name!==key)throw Error("Unexpected history response");
         historyArea.replaceChildren(head,chart(data,key,lang));
       }catch(_){
         if(container._ciGeneration===generation&&requestId===historyIndex)
           historyArea.replaceChildren(head,make("p","ci-missing",msg(lang,"historyError")));
       }
     }
     container.append(historyArea);
     const grid=make("div","ci-groups");
     for(const [position,group] of GROUPS.entries()){
       const section=make("details","ci-group ci-group-"+group.key);
       section.open=position<2;
       const availableInGroup=group.items.filter(k=>validRecord(records[k])).length;
       const summary=make("summary","ci-group-label");
       summary.append(make("span","ci-group-icon",group.symbol),
         make("strong","",msg(lang,group.key)),
         make("span","ci-group-count",availableInGroup+" / "+group.items.length));
       section.append(summary);
       const cards=make("div","ci-metric-grid");
       group.items.forEach(key=>cards.append(metricTile(key,records[key],{code,language:lang,onHistory})));
       section.append(cards);
       if(group.key==="governance"||group.key==="health"||group.key==="safety")
         section.append(make("p","ci-note",msg(lang,group.key+"Note")));
       grid.append(section);
     }
     container.append(grid);
   } catch(_) {
     if(container._ciGeneration===generation)container.replaceChildren(make("div","notice",msg(lang,"error")));
   }
 }
 function flagsGrid({container,countries,language="en",selected="PT"}){
   if(!container)return;
   const lang=LABELS[language]?language:"en";container.replaceChildren();
   const list=make("div","ci-country-grid");
   const rows=(Array.isArray(countries)?countries:[]).filter(c=>KNOWN.has(c.code));
   for(const row of rows){
     const a=make("a","ci-country-choice"+(row.code===selected?" ci-chosen":""));
     a.href="./country.html?country="+encodeURIComponent(row.code);
     const f=make("span","ci-choice-flag",flag(row.code));f.setAttribute("aria-hidden","true");
     a.append(f,make("span","ci-choice-name",display(row.code,lang).replace(flag(row.code)+" ","")),make("small","",row.code));
     list.append(a);
   }
   container.append(list);
 }
 window.EarnWageCountryData=Object.freeze({
   flag,display,metricName,msg,GROUPS,ALL,showCountry,flagsGrid
 });
})();
