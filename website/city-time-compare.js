/* EarnWage: compare time in two cities, using existing IANA reference catalogue.
 * No geographic coordinate claims, geocoding, live weather, or remote API calls.
 */
(() => {
"use strict";
const codes=["PT","ES","DE","FR","GB","IE","NL","CH","IT","US","CA","BR","IN","PK"];
const tags={en:"en-GB",pt:"pt-PT",es:"es-ES",de:"de-DE",fr:"fr-FR",it:"it-IT",nl:"nl-NL"};
const words={
 en:{title:"Compare local time",first:"First city",second:"Second city",difference:"Time difference",same:"Both cities have the same local time",ahead:"is ahead of",behind:"is behind",hour:"hour",hours:"hours",minute:"minute",minutes:"minutes",map:"Find on OpenStreetMap",info:"Time difference is calculated for the current instant, including applicable daylight saving time. Map links open a search, not a verified point on a map.",invalid:"Time zone unavailable"},
 pt:{title:"Comparar horas locais",first:"Primeira cidade",second:"Segunda cidade",difference:"Diferença horária",same:"As duas cidades têm a mesma hora local",ahead:"está adiantada em relação a",behind:"está atrasada em relação a",hour:"hora",hours:"horas",minute:"minuto",minutes:"minutos",map:"Localizar no OpenStreetMap",info:"A diferença horária corresponde ao instante atual e considera o horário de verão aplicável. As ligações abrem uma pesquisa no mapa, não um ponto geográfico validado.",invalid:"Fuso horário indisponível"},
 es:{title:"Comparar horas locales",first:"Primera ciudad",second:"Segunda ciudad",difference:"Diferencia horaria",same:"Ambas ciudades tienen la misma hora local",ahead:"está adelantada respecto a",behind:"está atrasada respecto a",hour:"hora",hours:"horas",minute:"minuto",minutes:"minutos",map:"Buscar en OpenStreetMap",info:"Diferencia calculada para el momento actual, incluido el horario de verano. Los enlaces abren una búsqueda, no coordenadas verificadas.",invalid:"Zona horaria no disponible"},
 de:{title:"Ortszeiten vergleichen",first:"Erste Stadt",second:"Zweite Stadt",difference:"Zeitunterschied",same:"Beide Städte haben dieselbe Ortszeit",ahead:"liegt zeitlich vor",behind:"liegt zeitlich hinter",hour:"Stunde",hours:"Stunden",minute:"Minute",minutes:"Minuten",map:"Auf OpenStreetMap suchen",info:"Zeitunterschied zum aktuellen Zeitpunkt einschließlich Sommerzeit. Kartenlinks sind Suchanfragen, keine verifizierten Koordinaten.",invalid:"Zeitzone nicht verfügbar"},
 fr:{title:"Comparer les heures locales",first:"Première ville",second:"Deuxième ville",difference:"Décalage horaire",same:"Les deux villes ont la même heure locale",ahead:"est en avance sur",behind:"est en retard sur",hour:"heure",hours:"heures",minute:"minute",minutes:"minutes",map:"Rechercher sur OpenStreetMap",info:"Décalage calculé à l'instant présent, heure d'été comprise. Les liens cartographiques lancent une recherche, sans coordonnées validées.",invalid:"Fuseau horaire indisponible"},
 it:{title:"Confrontare le ore locali",first:"Prima città",second:"Seconda città",difference:"Differenza di orario",same:"Le due città hanno la stessa ora locale",ahead:"è avanti rispetto a",behind:"è indietro rispetto a",hour:"ora",hours:"ore",minute:"minuto",minutes:"minuti",map:"Cerca su OpenStreetMap",info:"Differenza calcolata per l'istante attuale, compresa l'ora legale. I collegamenti aprono una ricerca, non coordinate verificate.",invalid:"Fuso orario non disponibile"},
 nl:{title:"Lokale tijden vergelijken",first:"Eerste stad",second:"Tweede stad",difference:"Tijdsverschil",same:"Beide steden hebben dezelfde lokale tijd",ahead:"loopt voor op",behind:"loopt achter op",hour:"uur",hours:"uur",minute:"minuut",minutes:"minuten",map:"Zoeken op OpenStreetMap",info:"Huidig tijdsverschil, inclusief zomertijd. Kaartlinks openen een zoekopdracht, geen geverifieerde coördinaten.",invalid:"Tijdzone niet beschikbaar"}
};
const make=(name,text,cls)=>{const e=document.createElement(name);if(text!==undefined)e.textContent=String(text);if(cls)e.className=cls;return e};
const catalogue=()=>window.EarnWageCityTimezones||{};
function entries(){return codes.flatMap(code=>(catalogue()[code]||[]).map(city=>({...city,code})))}
function offsetMinutes(zone,instant){
 const fields=new Intl.DateTimeFormat("en-GB",{
  timeZone:zone,year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",
  minute:"2-digit",second:"2-digit",hourCycle:"h23"
 }).formatToParts(instant);
 const dict=Object.fromEntries(fields.filter(x=>x.type!=="literal").map(x=>[x.type,Number(x.value)]));
 return Math.round((Date.UTC(dict.year,dict.month-1,dict.day,dict.hour,dict.minute,dict.second)-
   Math.floor(instant.getTime()/1000)*1000)/60000);
}
function formatClock(zone,lang,instant){
 return new Intl.DateTimeFormat(tags[lang]||tags.en,{
  timeZone:zone,weekday:"short",day:"numeric",month:"short",
  hour:"2-digit",minute:"2-digit",second:"2-digit",hourCycle:"h23"
 }).format(instant);
}
function cityLink(city,lang){
 const name=(()=>{try{return new Intl.DisplayNames([tags[lang]||"en-GB"],{type:"region"}).of(city.code)||city.code}catch(_){return city.code}})();
 return "https://www.openstreetmap.org/search?query="+encodeURIComponent(city.name+", "+name);
}
let timer=null;
function init(){
 const host=document.getElementById("countryCityCompare");
 if(!host)return;
 const cities=entries();if(!cities.length){host.hidden=true;return}
 host.hidden=false;
 const heading=make("h2");
 const grid=make("div",undefined,"ct-compare-grid");
 const selectors=[],clocks=[],maps=[];
 for(let i=0;i<2;i++){
  const card=make("div",undefined,"ct-compare-city");
  const label=make("label");label.htmlFor="ct-compare-"+i;
  const selector=make("select");selector.id=label.htmlFor;
  const clock=make("output",undefined,"ct-compare-clock");
  const map=make("a");map.target="_blank";map.rel="noopener noreferrer";
  for(let j=0;j<cities.length;j++){
   const city=cities[j],option=make("option",city.name+" ("+city.code+")");
   option.value=String(j);selector.append(option);
  }
  card.append(label,selector,clock,map);grid.append(card);
  selectors.push({selector,label});clocks.push(clock);maps.push(map);
 }
 const result=make("p",undefined,"ct-time-difference");
 result.setAttribute("aria-live","off"); // avoid screen-reader announcements every second
 const note=make("p",undefined,"ct-note");
 host.replaceChildren(heading,grid,result,note);
 function refresh(){
  const lang=document.getElementById("lang")?.value||"en",t=words[lang]||words.en;
  heading.textContent=t.title;selectors[0].label.textContent=t.first;selectors[1].label.textContent=t.second;
  note.textContent=t.info;
  const a=cities[Number(selectors[0].selector.value)],b=cities[Number(selectors[1].selector.value)];
  if(!a||!b)return;
  const now=new Date();
  try{
   const delta=offsetMinutes(b.timeZone,now)-offsetMinutes(a.timeZone,now);
   clocks[0].textContent=formatClock(a.timeZone,lang,now);
   clocks[1].textContent=formatClock(b.timeZone,lang,now);
   const abs=Math.abs(delta),h=Math.floor(abs/60),m=abs%60;
   const parts=[];
   if(h)parts.push(h+" "+(h===1?t.hour:t.hours));
   if(m)parts.push(m+" "+(m===1?t.minute:t.minutes));
   result.textContent=delta===0?t.same:(b.name+" "+(delta>0?t.ahead:t.behind)+" "+a.name+": "+parts.join(" "));
  }catch(_){result.textContent=t.invalid;clocks.forEach(x=>x.textContent=t.invalid)}
  [a,b].forEach((city,i)=>{maps[i].href=cityLink(city,lang);maps[i].textContent=t.map});
 }
 function selectDefaults(){
  const country=document.getElementById("country")?.value||"PT";
  const first=Math.max(0,cities.findIndex(city=>city.code===country));
  let second=cities.findIndex(city=>city.code!==country);
  if(second<0)second=first;
  selectors[0].selector.value=String(first);selectors[1].selector.value=String(second);
  refresh();
 }
 selectors.forEach(x=>x.selector.addEventListener("change",refresh));
 document.getElementById("country")?.addEventListener("change",selectDefaults);
 document.getElementById("lang")?.addEventListener("change",refresh);
 document.getElementById("refresh")?.addEventListener("click",refresh);
 document.addEventListener("visibilitychange",()=>{if(!document.hidden)refresh()});
 selectDefaults();timer=window.setInterval(refresh,1000);
 window.addEventListener("pagehide",()=>{if(timer!==null)window.clearInterval(timer)},{once:true});
}
window.EarnWageCityCompare=Object.freeze({offsetMinutes,formatClock,cityLink});
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});else init();
})();