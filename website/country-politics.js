/* Editorial country government classifications, reviewed 2026-11-07.
 * These are categorical descriptors, not numerical political stability indices.
 * Reference 2025 denotes the archived CIA Factbook edition, not a live 2026 verification.
 * Explicitly separate form of state, government system, and territorial organisation.
 */
(() => {
 "use strict";
 const PROFILES=Object.freeze({
    PT: {form:"republic",system:"semi_presidential",territory:"unitary",source:"https://european-union.europa.eu/principles-countries-history/eu-countries/portugal_en",reference:"2026"}},
    ES: {form:"monarchy",system:"parliamentary",territory:"autonomous_unitary",source:"https://european-union.europa.eu/principles-countries-history/eu-countries/spain_en",reference:"2026"}},
    DE: {form:"republic",system:"parliamentary",territory:"federal",source:"https://european-union.europa.eu/principles-countries-history/eu-countries/germany_en",reference:"2026"}},
    FR: {form:"republic",system:"semi_presidential",territory:"unitary",source:"https://european-union.europa.eu/principles-countries-history/eu-countries/france_en",reference:"2026"}},
    GB: {form:"monarchy",system:"parliamentary",territory:"devolved_unitary",source:"https://www.thefactbook.org/fields/government-type",reference:"2025"}},
    IE: {form:"republic",system:"parliamentary",territory:"unitary",source:"https://european-union.europa.eu/principles-countries-history/eu-countries/ireland_en",reference:"2026"}},
    NL: {form:"monarchy",system:"parliamentary",territory:"unitary",source:"https://european-union.europa.eu/principles-countries-history/eu-countries/netherlands_en",reference:"2026"}},
    CH: {form:"republic",system:"collegial",territory:"federal",source:"https://www.thefactbook.org/fields/government-type",reference:"2025"}},
    IT: {form:"republic",system:"parliamentary",territory:"regionalised_unitary",source:"https://european-union.europa.eu/principles-countries-history/eu-countries/italy_en",reference:"2026"}},
    US: {form:"republic",system:"presidential",territory:"federal",source:"https://www.thefactbook.org/fields/government-type",reference:"2025"}},
    CA: {form:"monarchy",system:"parliamentary",territory:"federal",source:"https://www.thefactbook.org/fields/government-type",reference:"2025"}},
    BR: {form:"republic",system:"presidential",territory:"federal",source:"https://www.thefactbook.org/fields/government-type",reference:"2025"}},
    IN: {form:"republic",system:"parliamentary",territory:"federal",source:"https://www.thefactbook.org/fields/government-type",reference:"2025"}},
    PK: {form:"republic",system:"parliamentary",territory:"federal",source:"https://www.thefactbook.org/fields/government-type",reference:"2025"}}
 });
 const labels={
 en:{title:"Government and territorial organisation",form:"Form of state",system:"Government system",territory:"Territorial organisation",source:"Reference",asof:"Reference edition/year",notice:"Categorical country descriptions, not scores of democracy, safety or political stability. Archived 2025 references may require review for recent legal changes.",republic:"Republic",monarchy:"Constitutional monarchy",semi_presidential:"Semi-presidential",parliamentary:"Parliamentary",presidential:"Presidential",collegial:"Collegial executive / directorial",unitary:"Unitary",federal:"Federal",autonomous_unitary:"Unitary with autonomous communities",devolved_unitary:"Unitary with devolved administrations",regionalised_unitary:"Unitary with autonomous regions"},
 pt:{title:"Sistema político e organização territorial",form:"Forma de Estado",system:"Sistema de governo",territory:"Organização territorial",source:"Fonte",asof:"Edição/ano de referência",notice:"Classificações descritivas, não índices de democracia, segurança ou estabilidade política. As fontes arquivadas de 2025 exigem revisão perante alterações legais recentes.",republic:"República",monarchy:"Monarquia constitucional",semi_presidential:"Semipresidencialista",parliamentary:"Parlamentar",presidential:"Presidencialista",collegial:"Executivo colegial / diretorial",unitary:"Estado unitário",federal:"Estado federal",autonomous_unitary:"Estado unitário com comunidades autónomas",devolved_unitary:"Estado unitário com administrações descentralizadas",regionalised_unitary:"Estado unitário com regiões autónomas"},
 es:{title:"Sistema político y organización territorial",form:"Forma de Estado",system:"Sistema de gobierno",territory:"Organización territorial",source:"Fuente",asof:"Edición/año de referencia",notice:"Categorías descriptivas, no índices democráticos. Las fuentes archivadas de 2025 requieren revisión ante cambios recientes.",republic:"República",monarchy:"Monarquía constitucional",semi_presidential:"Semipresidencial",parliamentary:"Parlamentario",presidential:"Presidencial",collegial:"Ejecutivo colegiado / directoral",unitary:"Unitario",federal:"Federal",autonomous_unitary:"Unitario con comunidades autónomas",devolved_unitary:"Unitario con administraciones descentralizadas",regionalised_unitary:"Unitario con regiones autónomas"},
 de:{title:"Regierungssystem und Staatsaufbau",form:"Staatsform",system:"Regierungssystem",territory:"Staatsaufbau",source:"Quelle",asof:"Referenzausgabe/-jahr",notice:"Beschreibende Kategorien, keine Demokratie- oder Sicherheitsbewertungen. Archivquellen von 2025 benötigen Überprüfung.",republic:"Republik",monarchy:"Konstitutionelle Monarchie",semi_presidential:"Semipräsidentiell",parliamentary:"Parlamentarisch",presidential:"Präsidentiell",collegial:"Kollegialexekutive / Direktorialsystem",unitary:"Einheitsstaat",federal:"Bundesstaat",autonomous_unitary:"Einheitsstaat mit autonomen Gemeinschaften",devolved_unitary:"Einheitsstaat mit dezentralisierten Verwaltungen",regionalised_unitary:"Einheitsstaat mit autonomen Regionen"},
 fr:{title:"Régime politique et organisation territoriale",form:"Forme de l'État",system:"Régime politique",territory:"Organisation territoriale",source:"Source",asof:"Édition/année de référence",notice:"Catégories descriptives, non des indices démocratiques. Les références archivées de 2025 doivent être vérifiées après toute évolution juridique.",republic:"République",monarchy:"Monarchie constitutionnelle",semi_presidential:"Semi-présidentiel",parliamentary:"Parlementaire",presidential:"Présidentiel",collegial:"Exécutif collégial / directorial",unitary:"État unitaire",federal:"État fédéral",autonomous_unitary:"État unitaire avec communautés autonomes",devolved_unitary:"État unitaire avec administrations dévolues",regionalised_unitary:"État unitaire avec régions autonomes"},
 it:{title:"Sistema politico e organizzazione territoriale",form:"Forma di Stato",system:"Sistema di governo",territory:"Organizzazione territoriale",source:"Fonte",asof:"Edizione/anno di riferimento",notice:"Categorie descrittive, non indici di democrazia. Le fonti archiviate del 2025 richiedono una revisione in caso di modifiche giuridiche.",republic:"Repubblica",monarchy:"Monarchia costituzionale",semi_presidential:"Semipresidenziale",parliamentary:"Parlamentare",presidential:"Presidenziale",collegial:"Esecutivo collegiale / direttoriale",unitary:"Stato unitario",federal:"Stato federale",autonomous_unitary:"Stato unitario con comunità autonome",devolved_unitary:"Stato unitario con amministrazioni decentrate",regionalised_unitary:"Stato unitario con regioni autonome"},
 nl:{title:"Staatsvorm en territoriale organisatie",form:"Staatsvorm",system:"Regeringssysteem",territory:"Territoriale organisatie",source:"Bron",asof:"Referentie-editie/jaar",notice:"Beschrijvende categorieën, geen democratie- of veiligheidsscores. Gearchiveerde bronnen uit 2025 moeten opnieuw worden gecontroleerd bij wetswijzigingen.",republic:"Republiek",monarchy:"Constitutionele monarchie",semi_presidential:"Semipresidentieel",parliamentary:"Parlementair",presidential:"Presidentieel",collegial:"Collegiaal bestuur / directoriaal",unitary:"Eenheidsstaat",federal:"Federale staat",autonomous_unitary:"Eenheidsstaat met autonome gemeenschappen",devolved_unitary:"Eenheidsstaat met gedecentraliseerde besturen",regionalised_unitary:"Eenheidsstaat met autonome regio's"}
 };
 const node=(tag,cls,value)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(value!==undefined)e.textContent=value;return e};
 function show(){
  const host=document.getElementById("countryPolitics");
  if(!host)return;
  const code=document.getElementById("country")?.value;
  const selected=document.getElementById("lang")?.value||"en";
  const t=labels[selected]||labels.en,p=PROFILES[code];
  if(!p){host.hidden=true;host.replaceChildren();return}
  host.hidden=false;
  const title=node("h2","",t.title);
  const grid=node("div","cp-grid");
  for(const key of ["form","system","territory"]){
   const item=node("div","cp-field");
   item.append(node("h3","",t[key]),node("p","",t[p[key]]));
   grid.append(item);
  }
  const ref=node("p","cp-source",t.asof+": "+p.reference+" · ");
  const a=node("a","",t.source);a.href=p.source;a.target="_blank";a.rel="noopener noreferrer";ref.append(a);
  host.replaceChildren(title,grid,ref,node("p","cp-note",t.notice));
 }
 function init(){
   if(!document.getElementById("countryPolitics"))return;
   document.getElementById("country")?.addEventListener("change",show);
   document.getElementById("lang")?.addEventListener("change",show);
   document.getElementById("refresh")?.addEventListener("click",show);
   show();
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});else init();
 window.EarnWagePoliticalProfiles=Object.freeze({PROFILES,labels});
})();