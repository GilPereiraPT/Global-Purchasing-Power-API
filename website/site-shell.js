/* Shared EarnWage navigation and footer. No account or API request required. */
(() => {
  "use strict";
  const languages=["en","pt","es","de","fr","it","nl"];
  const copy={
    en:{home:"Home",compare:"Compare",salaries:"Salaries",countries:"Countries",jobs:"Jobs",insights:"Insights",more:"More",history:"History",coverage:"Data coverage",groups:"Wage groups",sources:"Sources",methodology:"Methodology",about:"About",report:"Report an error",project:"Project & sources",tagline:"Your salary. Your world.",disclaimer:"Data coverage varies by country and year. Results are informational, not individual tax or financial advice.",menu:"More information"},
    pt:{home:"Início",compare:"Comparar",salaries:"Salários",countries:"Países",jobs:"Empregos",insights:"Análises",more:"Mais",history:"Histórico",coverage:"Cobertura de dados",groups:"Grupos profissionais",sources:"Fontes",methodology:"Metodologia",about:"Sobre",report:"Comunicar um erro",project:"Projeto e fontes",tagline:"O seu salário. O seu mundo.",disclaimer:"A cobertura varia conforme o país e o ano. Os resultados são informativos, não constituindo aconselhamento fiscal ou financeiro individual.",menu:"Mais informações"},
    es:{home:"Inicio",compare:"Comparar",salaries:"Salarios",countries:"Países",jobs:"Empleos",insights:"Análisis",more:"Más",history:"Histórico",coverage:"Cobertura de datos",groups:"Grupos profesionales",sources:"Fuentes",methodology:"Metodología",about:"Acerca de",report:"Informar de un error",project:"Proyecto y fuentes",tagline:"Tu salario. Tu mundo.",disclaimer:"La cobertura varía por país y año. Los resultados son informativos, no asesoramiento fiscal o financiero personal.",menu:"Más información"},
    de:{home:"Startseite",compare:"Vergleichen",salaries:"Gehälter",countries:"Länder",jobs:"Jobs",insights:"Analysen",more:"Mehr",history:"Verlauf",coverage:"Datenabdeckung",groups:"Berufsgruppen",sources:"Quellen",methodology:"Methodik",about:"Über uns",report:"Fehler melden",project:"Projekt und Quellen",tagline:"Ihr Gehalt. Ihre Welt.",disclaimer:"Die Datenabdeckung variiert nach Land und Jahr. Keine individuelle Steuer- oder Finanzberatung.",menu:"Weitere Informationen"},
    fr:{home:"Accueil",compare:"Comparer",salaries:"Salaires",countries:"Pays",jobs:"Emplois",insights:"Analyses",more:"Plus",history:"Historique",coverage:"Couverture des données",groups:"Groupes professionnels",sources:"Sources",methodology:"Méthodologie",about:"À propos",report:"Signaler une erreur",project:"Projet et sources",tagline:"Votre salaire. Votre monde.",disclaimer:"La couverture varie selon les pays et années. Résultats informatifs, sans conseil fiscal ou financier individuel.",menu:"Informations supplémentaires"},
    it:{home:"Home",compare:"Confronta",salaries:"Stipendi",countries:"Paesi",jobs:"Lavoro",insights:"Analisi",more:"Altro",history:"Storico",coverage:"Copertura dati",groups:"Gruppi professionali",sources:"Fonti",methodology:"Metodologia",about:"Informazioni",report:"Segnala un errore",project:"Progetto e fonti",tagline:"Il tuo stipendio. Il tuo mondo.",disclaimer:"La copertura varia per paese e anno. Risultati informativi, non consulenza fiscale o finanziaria personale.",menu:"Altre informazioni"},
    nl:{home:"Home",compare:"Vergelijken",salaries:"Salarissen",countries:"Landen",jobs:"Vacatures",insights:"Inzichten",more:"Meer",history:"Historie",coverage:"Gegevensdekking",groups:"Beroepsgroepen",sources:"Bronnen",methodology:"Methodologie",about:"Over ons",report:"Fout melden",project:"Project en bronnen",tagline:"Jouw salaris. Jouw wereld.",disclaimer:"Gegevensdekking verschilt per land en jaar. Geen persoonlijk financieel of fiscaal advies.",menu:"Meer informatie"}
  };
  const top=[["home","index.html"],["compare","compare.html"],["salaries","salaries.html"],["countries","countries.html"],["jobs","jobs.html"],["insights","insights.html"]];
  const secondary=[["history","history.html"],["coverage","coverage.html"],["groups","wage-groups.html"],["sources","source-directory.html"],["methodology","methodology.html"],["about","about.html"]];
  const filename=(location.pathname.split("/").pop()||"index.html").toLowerCase();
  const active={ "country.html":"countries","occupation.html":"salaries","wage-groups.html":"groups","coverage.html":"coverage","history.html":"history","source-directory.html":"sources","sources.html":"sources","methodology.html":"methodology","about.html":"about" }[filename]||top.concat(secondary).find(([,f])=>f===filename)?.[0]||"";
  const activeExtra=filename==="sources.html"?"sources.html":null;
  function locale(requested){
    if(languages.includes(requested))return requested;
    let saved=null;try{saved=localStorage.getItem("earnwage_lang")}catch(_){}
    if(languages.includes(saved))return saved;
    const browser=(navigator.language||"en").slice(0,2).toLowerCase();
    if(languages.includes(browser))return browser;
    return languages.includes(document.querySelector("#languageSelector, #lang")?.value)
      ?document.querySelector("#languageSelector, #lang").value:"en";
  }
  const make=(tag,css,text)=>{const n=document.createElement(tag);if(css)n.className=css;if(text!==undefined)n.textContent=text;return n;};
  function anchor(key,file,txt){
    const a=make("a","ew-link",txt);
    a.href="./"+file;
    if(filename===file||(filename==="country.html"&&key==="countries")||(filename==="occupation.html"&&key==="salaries"))a.setAttribute("aria-current","page");
    return a;
  }
  function update(requested){
    const l=copy[locale(requested)]||copy.en;
    const nav=document.querySelector("header nav");
    if(nav){
      nav.classList.add("ew-nav");
      const list=nav.querySelector(".navlinks, .links");
      if(list)list.replaceChildren(...top.map(([key,file])=>anchor(key,file,l[key])));
      let more=nav.querySelector("#ewMore");
      if(!more){
        more=make("details","ew-more");more.id="ewMore";
        const summary=make("summary","ew-more-trigger");
        summary.id="ewMoreSummary";more.append(summary);
        const menu=make("div","ew-more-menu");
        menu.id="ewMoreMenu";more.append(menu);
        const sel=nav.querySelector(".nav-actions, .lang");
        if(sel)nav.insertBefore(more,sel);else nav.append(more);
        document.addEventListener("click",event=>{
          if(!more.contains(event.target))more.open=false;
        });
        document.addEventListener("keydown",event=>{if(event.key==="Escape"&&more.open){more.open=false;more.querySelector("summary")?.focus()}});
      }
      more.querySelector("summary").textContent=l.more;
      more.querySelector("summary").setAttribute("aria-label",l.menu);
      const menu=more.querySelector(".ew-more-menu");
      menu.replaceChildren(...secondary.map(([key,file])=>anchor(key,file,l[key])));
      if(activeExtra)menu.append(anchor("sources",activeExtra,l.sources));
      more.querySelector("summary").classList.toggle("ew-selected",secondary.some(([key])=>active===key));
      nav.querySelector(".brand")?.setAttribute("aria-label","EarnWage — "+l.home);
    }
    const footer=document.querySelector("footer");
    if(footer){
      footer.classList.add("ew-site-footer");
      const wrap=make("div","ew-footer-layout");
      const identity=make("div","ew-footer-identity");
      const brand=anchor("home","index.html","EarnWage");
      brand.className="ew-footer-brand";
      identity.append(brand,make("p","",l.tagline),make("p","ew-footer-note",l.disclaimer));
      const navigation=make("div","ew-footer-column");
      navigation.append(make("h2","ew-footer-heading",l.more));
      for(const [key,file] of [["compare","compare.html"],["salaries","salaries.html"],["countries","countries.html"],["jobs","jobs.html"],["insights","insights.html"],["history","history.html"],["coverage","coverage.html"]])navigation.append(anchor(key,file,l[key]));
      const information=make("div","ew-footer-column");
      information.append(make("h2","ew-footer-heading",l.sources));
      for(const [key,file] of [["sources","source-directory.html"],["methodology","methodology.html"],["about","about.html"]])information.append(anchor(key,file,l[key]));
      information.append(anchor("report","about.html#report",l.report));
      const git=make("a","ew-link",l.project);
      git.href="https://github.com/GilPereiraPT/Global-Purchasing-Power-API";
      git.target="_blank";git.rel="noopener noreferrer";
      information.append(git);
      wrap.append(identity,navigation,information);
      footer.replaceChildren(wrap);
    }
  }
  const controls=document.querySelectorAll("#languageSelector,#lang");
  for(const control of controls)control.addEventListener("change",()=>queueMicrotask(()=>update(control.value)));
  update();
  window.EarnWageShell={refresh:update};
})();
