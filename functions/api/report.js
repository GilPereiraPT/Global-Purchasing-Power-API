/* Cloudflare Pages Function: authenticated by Turnstile, delivers feedback through Resend.
 * Configure REPORT_TO_EMAIL, REPORT_FROM_EMAIL, RESEND_API_KEY, TURNSTILE_SECRET_KEY,
 * REPORT_ALLOWED_ORIGIN as environment variables/secrets on Cloudflare Pages.
 */
const json=(status,body)=>new Response(JSON.stringify(body),{status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
const MAX_BODY=12000;
function validUrl(value){if(!value)return true;try{const u=new URL(value);return u.protocol==="https:"&&u.href.length<=500}catch(_){return false}}
function validEmail(value){return typeof value==="string"&&value.length<=254&&/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)}
export async function onRequestPost({request,env}){
 if(!env.RESEND_API_KEY||!env.REPORT_TO_EMAIL||!env.REPORT_FROM_EMAIL||!env.TURNSTILE_SECRET_KEY||!env.REPORT_ALLOWED_ORIGIN)return json(503,{error:"not_configured"});
 const origin=request.headers.get("Origin");
 if(!origin||origin!==env.REPORT_ALLOWED_ORIGIN)return json(403,{error:"origin_rejected"});
 if(!(request.headers.get("Content-Type")||"").toLowerCase().startsWith("application/json"))return json(415,{error:"unsupported_media_type"});
 const size=Number(request.headers.get("Content-Length")||0);if(size>MAX_BODY)return json(413,{error:"too_large"});
 let raw;try{raw=await request.text()}catch(_){return json(400,{error:"invalid_body"})}
 if(raw.length>MAX_BODY)return json(413,{error:"too_large"});
 let v;try{v=JSON.parse(raw)}catch(_){return json(400,{error:"invalid_json"})}
 if(!v||typeof v!=="object"||Array.isArray(v))return json(400,{error:"invalid_payload"});
 const name=typeof v.name==="string"?v.name.trim():"";
 const email=typeof v.email==="string"?v.email.trim():"";
 const message=typeof v.message==="string"?v.message.trim():"";
 const type=typeof v.type==="string"?v.type:"";
 const page=typeof v.page==="string"?v.page.trim():"";
 const source=typeof v.source_url==="string"?v.source_url.trim():"";
 if(v.website)return json(400,{error:"invalid_payload"});
 if(!name||name.length>100||!validEmail(email)||message.length<15||message.length>4000||
    !["value","translation","source","other"].includes(type)||!validUrl(page)||!validUrl(source)||v.consent!==true||
    typeof v.turnstile_token!=="string"||v.turnstile_token.length<1||v.turnstile_token.length>2048)return json(422,{error:"invalid_fields"});
 const challenge=new URLSearchParams({secret:env.TURNSTILE_SECRET_KEY,response:v.turnstile_token});
 const ip=request.headers.get("CF-Connecting-IP");if(ip)challenge.set("remoteip",ip);
 let verified=false;
 try{const r=await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:challenge});const result=await r.json();verified=r.ok&&result.success===true}catch(_){}
 if(!verified)return json(403,{error:"challenge_failed"});
 const body=["EarnWage feedback", "Type: "+type,"Name: "+name,"Email: "+email,"Page: "+(page||"Not provided"),"Source: "+(source||"Not provided"),"","Message:",message].join("\n");
 const subjectKinds={value:"Incorrect value",translation:"Translation issue",source:"Source or broken link",other:"Suggestion"};
 const payload={from:env.REPORT_FROM_EMAIL,to:[env.REPORT_TO_EMAIL],reply_to:email,subject:"EarnWage: "+subjectKinds[type],text:body};
 try{
  const r=await fetch("https://api.resend.com/emails",{method:"POST",headers:{"Authorization":"Bearer "+env.RESEND_API_KEY,"Content-Type":"application/json"},body:JSON.stringify(payload)});
  if(!r.ok)return json(502,{error:"delivery_failed"});
  return json(200,{status:"sent"});
 }catch(_){return json(502,{error:"delivery_failed"})}
}
export function onRequestGet(){return json(405,{error:"method_not_allowed"})}
