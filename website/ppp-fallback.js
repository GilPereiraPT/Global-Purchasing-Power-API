/* Browser compatibility only: verified World Bank PPP, same reported year.
 * No exchange-rate conversion, speculative wage, net pay or city cost-of-living inference.
 */
(() => {
 "use strict";
 const KEY="ppp_private_consumption",UNIT="local_currency_units_per_international_dollar";
 function observed(row,country) {
  const v=row?.indicators?.[KEY];
  if(row?.country!==country||!/^[A-Z]{3}$/.test(row.currency||"")||
     v?.status!=="available"||v.unit!==UNIT||
     v.source!=="World Bank World Development Indicators"||
     !Number.isInteger(v.year)||v.year<1960||v.year>2100||
     !Number.isFinite(v.value)||v.value<=0||
     typeof v.source_url!=="string"||!v.source_url.startsWith("https://"))return null;
  return v;
 }
 async function ensure(original,countryA,countryB,grossA,grossB,request) {
  // A deployed API result is authoritative, including an explicit unavailable status.
  if(original&&typeof original.status==="string"&&original.status!=="not_implemented")return original;
  if(!/^[A-Z]{2}$/.test(countryA)||!/^[A-Z]{2}$/.test(countryB)||
     !Number.isFinite(grossA)||grossA<=0||grossA>100000000||
     typeof request!=="function")return original||{status:"unavailable"};
  try {
   const query=new URLSearchParams({country_a:countryA,country_b:countryB});
   const response=await request("/v1/economy/compare?"+query.toString());
   const rows=response?.countries;
   if(!Array.isArray(rows)||rows.length!==2||
      rows[0].country!==countryA||rows[1].country!==countryB)return original||{status:"unavailable"};
   const a=observed(rows[0],countryA),b=observed(rows[1],countryB);
   if(!a||!b||a.year!==b.year)return original||{status:"unavailable",reason:"No matched official PPP reference year"};
   const value=grossA*b.value/a.value;
   if(!Number.isFinite(value)||value<=0||value>1e15)return original||{status:"unavailable"};
   const result={status:"available",kind:"gross_annual_ppp_equivalence",
      value,currency:rows[1].currency,reference_year:a.year,
      origin_ppp:a.value,destination_ppp:b.value,
      source:"World Bank World Development Indicators",source_urls:[a.source_url,b.source_url],
      calculation_method:"client_fallback_same_year_official_api",
      note:"Gross annual PPP-equivalent from source-backed same-year national price levels; not a currency conversion, take-home pay or city living-cost basket."};
   if(Number.isFinite(grossB)&&grossB>0&&grossB<=100000000)
      result.destination_offer_difference_percent=(grossB/value-1)*100;
   return result;
  }catch(_) {return original||{status:"unavailable",reason:"PPP API observations not accessible"}}
 }
 window.EarnWagePPP=Object.freeze({ensure});
})();
