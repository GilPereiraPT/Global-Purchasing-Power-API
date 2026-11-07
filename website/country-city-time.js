/* Country profile: local clocks and representative cities. No network calls.
 * The clock uses the browser's Intl/IANA time-zone database and changes at DST.
 * It never claims to show live weather, national climate, or largest cities.
 */
(() => {
"use strict";
const languageLabels={
en:{title:"Cities and local time",city:"City",local:"Local time",zone:"Time zone",note:"Representative cities, not a population ranking. Time uses your device's time-zone database; update the device for recent legal changes.",weather:"Weather and monthly climate",pending:"Weather and climate data are not yet connected to a licensed source. No temperatures are estimated.",timeError:"Local time unavailable for this city."},
pt:{title:"Cidades e hora local",city:"Cidade",local:"Hora local",zone:"Fuso horário",note:"Cidades selecionadas, sem classificação por população. A hora utiliza a base de fusos horários do dispositivo; atualize-o para alterações legais recentes.",weather:"Meteorologia e clima mensal",pending:"Os dados meteorológicos e climáticos ainda não estão ligados a uma fonte com utilização autorizada. Não são estimadas temperaturas.",timeError:"Hora local indisponível para esta cidade."},
es:{title:"Ciudades y hora local",city:"Ciudad",local:"Hora local",zone:"Zona horaria",note:"Ciudades seleccionadas, sin clasificación por población. La hora utiliza la base de zonas horarias del dispositivo.",weather:"Meteorología y clima mensual",pending:"Los datos meteorológicos y climáticos aún no están conectados a una fuente autorizada. No se estiman temperaturas.",timeError:"Hora local no disponible."},
de:{title:"Städte und Ortszeit",city:"Stadt",local:"Ortszeit",zone:"Zeitzone",note:"Ausgewählte Städte, keine Bevölkerungsrangliste. Uhrzeit basiert auf der Zeitzonendatenbank des Geräts.",weather:"Wetter und Monatsklima",pending:"Wetter- und Klimadaten sind noch nicht an eine lizenzierte Quelle angebunden. Keine geschätzten Temperaturen.",timeError:"Ortszeit nicht verfügbar."},
fr:{title:"Villes et heure locale",city:"Ville",local:"Heure locale",zone:"Fuseau horaire",note:"Villes sélectionnées, sans classement par population. L'heure dépend de la base des fuseaux horaires de l'appareil.",weather:"Météo et climat mensuel",pending:"Les données météo et climat ne sont pas encore reliées à une source autorisée. Aucune température n'est estimée.",timeError:"Heure locale indisponible."},
it:{title:"Città e ora locale",city:"Città",local:"Ora locale",zone:"Fuso orario",note:"Città selezionate, non una classifica per popolazione. L'ora utilizza i fusi orari del dispositivo.",weather:"Meteo e clima mensile",pending:"Dati meteo e climatici non ancora collegati a una fonte autorizzata. Nessuna temperatura stimata.",timeError:"Ora locale non disponibile."},
nl:{title:"Steden en lokale tijd",city:"Stad",local:"Lokale tijd",zone:"Tijdzone",note:"Geselecteerde steden, geen bevolkingsranglijst. Tijd gebruikt de tijdzonedatabase van het apparaat.",weather:"Weer en maandklimaat",pending:"Weer- en klimaatgegevens zijn nog niet gekoppeld aan een toegestane bron. Geen geschatte temperaturen.",timeError:"Lokale tijd niet beschikbaar."}
};
const tags={en:"en-GB",pt:"pt-PT",es:"es-ES",de:"de-DE",fr:"fr-FR",it:"it-IT",nl:"nl-NL"};
const el=(tag,cls,txt)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=txt;return n};
let interval=null;
let active=null;
function locale(){const selected=document.getElementById("lang")?.value||"en";return languageLabels[selected]?selected:"en"}
function dispose(){if(interval!==null){clearInterval(interval);interval=null}}
function render(){
 const section=document.getElementById("countryCityTime");
 const code=document.getElementById("country")?.value;
 if(!section)return;
 dispose();
 const cities=window.EarnWageCityTimezones?.[code];
 if(!Array.isArray(cities)||!cities.length){section.hidden=true;section.replaceChildren();return}
 section.hidden=false;
 const lang=locale(),t=languageLabels[lang];
 const heading=el("h2","",t.title);
 const layout=el("div","ct-grid");
 const left=el("div","ct-left");
 const label=el("label","",t.city);label.htmlFor="ct-city";
 const select=el("select","");select.id="ct-city";
 for(const [index,city]of cities.entries()){
  const option=el("option","",city.name);option.value=String(index);select.append(option);
 }
 const clock=el("output","ct-clock");clock.setAttribute("aria-label",t.local);
 const zone=el("p","ct-zone");
 const tz=el("span","ct-zone-caption",t.zone+": ");
 zone.append(tz,el("span","ct-zone-value"));
 left.append(label,select,clock,zone);
 const right=el("div","ct-weather");
 right.append(el("h3","",t.weather),el("p","",t.pending));
 layout.append(left,right);
 section.replaceChildren(heading,layout,el("p","ct-note",t.note));
 function tick(){
   const index=Number(select.value),city=cities[index];
   if(!city)return;
   const zoneValue=zone.querySelector(".ct-zone-value");zoneValue.textContent=city.timeZone;
   try{
     clock.textContent=new Intl.DateTimeFormat(tags[lang],{
       timeZone:city.timeZone,weekday:"short",day:"2-digit",month:"short",
       hour:"2-digit",minute:"2-digit",second:"2-digit",hourCycle:"h23"
     }).format(new Date());
     clock.dateTime="";
   }catch(_){clock.textContent=t.timeError}
 }
 const updateWeather=()=>window.EarnWageWeather?.load(code,Number(select.value),right,lang);
 select.addEventListener("change",()=>{tick();updateWeather()});
 active=code;tick();updateWeather();
 interval=setInterval(tick,1000);
}
function init(){
 if(!document.getElementById("countryCityTime"))return;
 document.getElementById("country")?.addEventListener("change",render);
 document.getElementById("lang")?.addEventListener("change",render);
 document.getElementById("refresh")?.addEventListener("click",render);
 document.addEventListener("visibilitychange",()=>{if(!document.hidden)render()});
 window.addEventListener("pagehide",dispose);
 render();
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});else init();
})();