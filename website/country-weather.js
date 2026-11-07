/* EarnWage city weather: city-index zero capital forecasts via own API.
 * Never uses MET Norway from the browser. No "live observed" claim.
 */
(() => {
"use strict";
const locale={
en:{pending:"Forecast not available",loading:"Loading weather forecast…",current:"Next forecast",humidity:"Humidity",wind:"Wind",days:"Next 7 local dates",source:"Weather data: MET Norway · CC BY 4.0",note:"These are model forecasts, not on-site observations. Daily extremes are calculated from available forecast samples; the first day may be incomplete.",stale:"Last cached forecast; source refresh failed.",config:"Weather service not configured on the server.",other:"Forecasts currently cover the capital only. Other cities will follow.",failed:"Forecast temporarily unavailable.",climate:"Monthly climate normals: not yet connected"},
pt:{pending:"Previsão indisponível",loading:"A carregar previsão meteorológica…",current:"Próxima previsão",humidity:"Humidade",wind:"Vento",days:"Próximas 7 datas locais",source:"Dados meteorológicos: MET Norway · CC BY 4.0",note:"São previsões de modelos, não medições locais. Os extremos diários resultam das amostras disponíveis; o primeiro dia pode estar incompleto.",stale:"Última previsão em cache; falhou a atualização da fonte.",config:"Serviço meteorológico ainda não configurado no servidor.",other:"As previsões abrangem, por enquanto, apenas a capital. As restantes cidades serão acrescentadas.",failed:"Previsão temporariamente indisponível.",climate:"Médias climáticas mensais: ainda não disponíveis"},
es:{pending:"Pronóstico no disponible",loading:"Cargando pronóstico…",current:"Próximo pronóstico",humidity:"Humedad",wind:"Viento",days:"Próximas 7 fechas locales",source:"Datos meteorológicos: MET Norway · CC BY 4.0",note:"Predicciones de modelos, no observaciones locales. Los extremos diarios usan las muestras disponibles; el primer día puede ser parcial.",stale:"Pronóstico en caché; falló la actualización.",config:"Servicio meteorológico no configurado.",other:"Por ahora solo hay pronósticos para la capital.",failed:"Pronóstico temporalmente no disponible.",climate:"Medias climáticas mensuales: aún no disponibles"},
de:{pending:"Vorhersage nicht verfügbar",loading:"Wettervorhersage wird geladen…",current:"Nächste Vorhersage",humidity:"Luftfeuchte",wind:"Wind",days:"Nächste 7 lokale Tage",source:"Wetterdaten: MET Norway · CC BY 4.0",note:"Modellvorhersagen, keine Messungen vor Ort. Tagesextreme aus verfügbaren Vorhersagewerten; der erste Tag kann unvollständig sein.",stale:"Letzte zwischengespeicherte Vorhersage; Aktualisierung fehlgeschlagen.",config:"Wetterdienst auf dem Server noch nicht konfiguriert.",other:"Aktuell nur Vorhersage für die Hauptstadt.",failed:"Vorhersage vorübergehend nicht verfügbar.",climate:"Monatliche Klimamittel: noch nicht verfügbar"},
fr:{pending:"Prévisions indisponibles",loading:"Chargement des prévisions…",current:"Prochaine prévision",humidity:"Humidité",wind:"Vent",days:"7 prochaines dates locales",source:"Données météo : MET Norway · CC BY 4.0",note:"Prévisions de modèles, pas des observations sur place. Extrêmes tirés des échantillons disponibles ; la première journée peut être partielle.",stale:"Dernière prévision en cache ; échec de mise à jour.",config:"Service météo non configuré sur le serveur.",other:"Prévisions limitées actuellement à la capitale.",failed:"Prévisions temporairement indisponibles.",climate:"Normales climatiques mensuelles : indisponibles"},
it:{pending:"Previsione non disponibile",loading:"Caricamento previsioni…",current:"Prossima previsione",humidity:"Umidità",wind:"Vento",days:"Prossime 7 date locali",source:"Dati meteo: MET Norway · CC BY 4.0",note:"Previsioni modellistiche, non osservazioni locali. Estremi da campioni disponibili; il primo giorno può essere parziale.",stale:"Ultima previsione in cache; aggiornamento non riuscito.",config:"Servizio meteo non configurato sul server.",other:"Previsioni attualmente solo per la capitale.",failed:"Previsioni temporaneamente non disponibili.",climate:"Medie climatiche mensili: non ancora disponibili"},
nl:{pending:"Voorspelling niet beschikbaar",loading:"Weersverwachting laden…",current:"Eerstvolgende voorspelling",humidity:"Luchtvochtigheid",wind:"Wind",days:"Volgende 7 lokale datums",source:"Weergegevens: MET Norway · CC BY 4.0",note:"Modelvoorspellingen, geen lokale metingen. Daggrenzen uit beschikbare voorspelde waarden; de eerste dag kan onvolledig zijn.",stale:"Laatste opgeslagen voorspelling; verversen mislukt.",config:"Weerdienst nog niet geconfigureerd.",other:"Momenteel alleen voorspellingen voor de hoofdstad.",failed:"Voorspelling tijdelijk niet beschikbaar.",climate:"Maandelijkse klimaatgemiddelden: nog niet beschikbaar"}
};
const tags={en:"en-GB",pt:"pt-PT",es:"es-ES",de:"de-DE",fr:"fr-FR",it:"it-IT",nl:"nl-NL"};
const el=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=String(text);return node};
let requestCounter=0;
function load(code, cityIndex, container, lang){
 if(!container)return;
 const current=++requestCounter,t=locale[lang]||locale.en;
 container.replaceChildren(el("h3","",lang==="pt"?"Meteorologia e previsão de 7 dias":t.current));
 if(cityIndex!==0){container.append(el("p","",t.other),el("p","ct-weather-meta",t.climate));return}
 const status=el("p","",t.loading);container.append(status);
 const source=el("a","ct-weather-source",t.source);source.href="https://api.met.no/";source.rel="noopener noreferrer";source.target="_blank";
 const path="/v1/weather/"+encodeURIComponent(code)+"/0";
 fetch(window.EarnWageConfig.apiBase+path,{headers:{Accept:"application/json"}})
 .then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json()})
 .then(d=>{
   if(current!==requestCounter||!container.isConnected)return;
   if(d?.country!==code||d?.city_id!==0)throw Error("Unexpected response");
   if(d.status!=="available"){
     status.textContent=d.status==="not_configured"?t.config:t.failed;
     container.append(el("p","ct-weather-meta",t.climate));return;
   }
   const currentForecast=d.current_forecast||{};
   const temp=Number.isFinite(currentForecast.temperature_c)?currentForecast.temperature_c.toFixed(1)+" °C":t.pending;
   status.className="ct-weather-temp";status.textContent=temp;
   const row=el("p","ct-weather-meta",t.current+": "+(currentForecast.time||""));
   container.append(row);
   const details=[];
   if(Number.isFinite(currentForecast.humidity_percent))details.push(t.humidity+": "+Math.round(currentForecast.humidity_percent)+"%");
   if(Number.isFinite(currentForecast.wind_m_s))details.push(t.wind+": "+currentForecast.wind_m_s+" m/s");
   if(details.length)container.append(el("p","ct-weather-meta",details.join(" · ")));
   if(Array.isArray(d.daily_forecast)&&d.daily_forecast.length){
     container.append(el("h4","ct-weather-heading",t.days));
     const list=el("ul","ct-weather-days");
     for(const day of d.daily_forecast.slice(0,7)){
       if(!Number.isFinite(day.min_temp_c)||!Number.isFinite(day.max_temp_c))continue;
       const line=el("li");
       line.append(el("span","",day.date),el("strong","",day.min_temp_c.toFixed(1)+" / "+day.max_temp_c.toFixed(1)+" °C"));
       list.append(line);
     }
     container.append(list);
   }
   if(d.stale)container.append(el("p","ct-weather-meta",t.stale));
   container.append(el("p","ct-weather-meta",t.note),el("p","ct-weather-meta",t.climate),source);
 })
 .catch(()=>{if(current===requestCounter&&container.isConnected){status.textContent=t.failed;container.append(el("p","ct-weather-meta",t.climate))}});
}
window.EarnWageWeather=Object.freeze({load});
})();