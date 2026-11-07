/* Curated geographic reference for country-page city/time-zone exploration.
 * Cities are examples, NOT a ranking of population or a complete country directory.
 * IANA time zones use the browser's bundled time-zone rules (including DST).
 * Static reference; review city coverage before extending to top-N populations.
 */
(() => {
  "use strict";
  const data={
    PT:[["Lisboa","Europe/Lisbon"],["Porto","Europe/Lisbon"],["Funchal","Atlantic/Madeira"],["Ponta Delgada","Atlantic/Azores"]],
    ES:[["Madrid","Europe/Madrid"],["Barcelona","Europe/Madrid"],["Sevilha","Europe/Madrid"],["Las Palmas de Gran Canaria","Atlantic/Canary"]],
    DE:[["Berlim","Europe/Berlin"],["Hamburgo","Europe/Berlin"],["Munique","Europe/Berlin"]],
    FR:[["Paris","Europe/Paris"],["Marselha","Europe/Paris"],["Lyon","Europe/Paris"]],
    GB:[["Londres","Europe/London"],["Manchester","Europe/London"],["Edimburgo","Europe/London"]],
    IE:[["Dublin","Europe/Dublin"],["Cork","Europe/Dublin"],["Galway","Europe/Dublin"]],
    NL:[["Amesterdão","Europe/Amsterdam"],["Roterdão","Europe/Amsterdam"],["Haia","Europe/Amsterdam"]],
    CH:[["Berna","Europe/Zurich"],["Zurique","Europe/Zurich"],["Genebra","Europe/Zurich"]],
    IT:[["Roma","Europe/Rome"],["Milão","Europe/Rome"],["Nápoles","Europe/Rome"]],
    US:[["Washington, D.C.","America/New_York"],["Nova Iorque","America/New_York"],["Chicago","America/Chicago"],["Los Angeles","America/Los_Angeles"],["Honolulu","Pacific/Honolulu"]],
    CA:[["Ottawa","America/Toronto"],["Toronto","America/Toronto"],["Vancouver","America/Vancouver"],["Calgary","America/Edmonton"],["Halifax","America/Halifax"]],
    BR:[["Brasília","America/Sao_Paulo"],["São Paulo","America/Sao_Paulo"],["Rio de Janeiro","America/Sao_Paulo"],["Manaus","America/Manaus"],["Rio Branco","America/Rio_Branco"]],
    IN:[["Nova Deli","Asia/Kolkata"],["Mumbai","Asia/Kolkata"],["Bengaluru","Asia/Kolkata"],["Calcutá","Asia/Kolkata"]],
    PK:[["Islamabad","Asia/Karachi"],["Karachi","Asia/Karachi"],["Lahore","Asia/Karachi"]]
  };
  window.EarnWageCityTimezones=Object.freeze(Object.fromEntries(
    Object.entries(data).map(([country,cities])=>[country,Object.freeze(cities.map(([name,timeZone])=>Object.freeze({name,timeZone})))])));
})();