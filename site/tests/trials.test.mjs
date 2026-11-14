// Trial-reader contract: synthetic records, no network or browser cookies.
import assert from 'node:assert/strict';
import path from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {test} from 'node:test';
import {handle} from '../worker/index.mjs';
const root=fileURLToPath(new URL('../..', import.meta.url));
const {handleTrial}=await import(pathToFileURL(path.join(root,'site/worker/trials.mjs')));
const {trialDetailsPath,buildTrialIndex}=await import(pathToFileURL(path.join(root,'site/src/lib/trial-links.mjs')));
const id='NCT04605549';
const now=Date.parse('2026-11-14T12:00:00Z');
const key='trial-record:v1:'+id;
const original='https://clinicaltrials.gov/study/'+id;
const template='<!doctype html><html><head><title>__TRIAL_TITLE__ | What came of it?</title><link rel="canonical" href="https://whatcameofit.com/trials/__TRIAL_ID__"></head><body><main class="trial-reader">__TRIAL_CONTENT__</main><footer>This site gives no medical advice. A registered clinical trial is not a treatment option.</footer></body></html>';
const record={protocolSection:{identificationModule:{nctId:id,briefTitle:'A study of CIN-107',officialTitle:'CIN-107 & primary aldosteronism'},statusModule:{overallStatus:'COMPLETED',lastUpdatePostDateStruct:{date:'2026-03-03'},studyFirstPostDateStruct:{date:'2020-10-28'},startDateStruct:{date:'2021-03-08',type:'ACTUAL'},completionDateStruct:{date:'2027-04',type:'ESTIMATED'}},descriptionModule:{briefSummary:'Patients received CIN-107.\n\nBlood pressure was measured.'},conditionsModule:{conditions:['Primary aldosteronism']},armsInterventionsModule:{interventions:[{name:'CIN-107',type:'DRUG',description:'Once daily'}]},designModule:{phases:['PHASE2'],studyType:'INTERVENTIONAL',enrollmentInfo:{count:15,type:'ACTUAL'}},sponsorCollaboratorsModule:{leadSponsor:{name:'Example Sponsor'}}},hasResults:true};
const index={trials:{[id]:[{slug:'primary-aldosteronism-baxdrostat',headline:'Baxdrostat claim'}]}};
function setup({payload=record,status=200,fail=false,entry,deny=false,contact=true}={}){
 const calls=[];const cache=new Map(entry?[[key,entry]]:[]);const puts=[];
 const env={CONTACT_EMAIL:contact?'corrections@whatcameofit.com':undefined,ASSETS:{fetch:async r=>{const p=new URL(r.url||r).pathname;return p==='/trial-index.json'?Response.json(index):p==='/trial-reader'?new Response(template):new Response('missing',{status:404});}},LOOKUP_RESULTS:{get:async(k)=>cache.get(k)??null,put:async(k,v,o)=>{puts.push({k,v:JSON.parse(v),options:o});cache.set(k,JSON.parse(v));}},TRIAL_RECORD_READS:{limit:async()=>({success:!deny})}};
 const fetch=async(url,options)=>{calls.push({url:String(url),options});if(fail)throw new Error('PRIVATE_ERROR_SECRET');return status===200?Response.json(payload):new Response('upstream failure',{status});};
 const run=(url='/trials/'+id,opts={})=>handleTrial(new Request('http://localhost'+url,opts),env,{fetch,now:()=>now});
 return {calls,cache,puts,env,run};
}
await test('recognises only official trial URLs and preserves identity',()=>{
 assert.equal(trialDetailsPath(original),'/trials/'+id);
 assert.equal(trialDetailsPath('https://clinicaltrials.gov/study/'+id+'?tab=results'),'/trials/'+id);
 for(const url of ['https://clinicaltrials.gov.evil.test/study/'+id,'https://evil.test/study/'+id,'javascript:alert(1)',null,'https://clinicaltrials.gov/study/NCT1'])assert.equal(trialDetailsPath(url),null);
 const d=buildTrialIndex({claims:[{slug:'claim',headline:'Claim',events:[{source_url:original}],matches:[{url:original},{url:'https://evil.test/study/NCT07007793'}]}]});
 assert.deepEqual(Object.keys(d.trials),[id]);assert.equal(d.trials[id].length,1);assert.equal(d.trials[id][0].slug,'claim');
});
await test('serves real readable HTML with source and independent dates',async()=>{
 const s=setup();const r=await s.run();const h=await r.text();assert.equal(r.status,200);assert.match(r.headers.get('content-type'),/text\/html/);
 for(const word of ['A study of CIN-107','Primary aldosteronism','CIN-107','Example Sponsor','15','ClinicalTrials.gov',original,'/primary-aldosteronism-baxdrostat'])assert.ok(h.includes(word),word);
 assert.match(h,/2026-03-03|3\s+Mar(?:ch)?\s+2026/);assert.match(h,/2026-11-14|14\s+Nov(?:ember)?\s+2026/);assert.match(h,/estimated/i);
 assert.ok(!h.includes('__TRIAL_'));assert.equal(s.calls.length,1);assert.equal(s.calls[0].url,'https://clinicaltrials.gov/api/v2/studies/'+id);
 assert.equal(s.puts.length,1);assert.equal(s.puts[0].k,key);assert.equal(s.puts[0].v.at,now);assert.equal(s.puts[0].v.record.protocolSection.identificationModule.nctId,id);
});
await test('does not forward reader cookies or authorisation and has a timeout',async()=>{
 const s=setup();const r=await s.run(undefined,{headers:{Cookie:'ncbi_sid=private',Authorization:'Bearer private'}});assert.equal(r.status,200);
 const headers=new Headers(s.calls[0].options.headers);assert.equal(headers.get('cookie'),null);assert.equal(headers.get('authorization'),null);assert.match(headers.get('user-agent'),/corrections@whatcameofit\.com/);assert.ok(s.calls[0].options.signal instanceof AbortSignal);
});
await test('reuses a fresh copy without upstream reads',async()=>{
 const s=setup({entry:{version:1,at:now-3600000,record}});const r=await s.run();assert.equal(r.status,200);assert.equal(s.calls.length,0);assert.equal(s.puts.length,0);
});
await test('a copy older than a day is never shown, even when the registry is down',async()=>{
 const s=setup({fail:true,entry:{version:1,at:now-2*86400000,record}});const r=await s.run();const h=await r.text();assert.equal(r.status,503);assert.equal(s.calls.length,1);assert.ok(!h.includes('A study of CIN-107'));assert.doesNotMatch(h,/older copy/i);assert.ok(h.includes(original));assert.ok(!h.includes('PRIVATE_ERROR_SECRET'));
});
await test('a copy older than a day is read again from the registry',async()=>{
 const s=setup({entry:{version:1,at:now-2*86400000,record}});const r=await s.run();assert.equal(r.status,200);assert.equal(s.calls.length,1);assert.equal(s.puts.length,1);assert.equal(s.puts[0].v.at,now);assert.equal(s.puts[0].options.expirationTtl,86400);
});
await test('outage without a usable copy is a recoverable 503',async()=>{
 for(const entry of [undefined,{version:1,at:now-2*86400000,record},{version:1,at:now-8*86400000,record},{version:1,at:now+60000,record}]){const s=setup({fail:true,entry});const r=await s.run();const h=await r.text();assert.equal(r.status,503);assert.ok(h.includes(original));assert.match(h,/try again|retry/i);assert.match(r.headers.get('cache-control'),/no-store/);assert.ok(!h.includes('PRIVATE_ERROR_SECRET'));}
});
await test('invalid or uncited IDs never query registry',async()=>{
 for(const suffix of ['NCT1','NCT00000000','NCT04605549/extra','%3Cscript%3E']){const s=setup();const r=await s.run('/trials/'+suffix);assert.equal(r.status,404);assert.equal(s.calls.length,0);}
});
await test('upstream missing record is 404 and not cached',async()=>{
 const s=setup({status:404});const r=await s.run();assert.equal(r.status,404);assert.equal(s.puts.length,0);
});
await test('wrong record identity is rejected',async()=>{
 const wrong=structuredClone(record);wrong.protocolSection.identificationModule.nctId='NCT07007793';const s=setup({payload:wrong});const r=await s.run();assert.equal(r.status,503);assert.equal(s.puts.length,0);
 const cached=setup({payload:record,entry:{version:1,at:now,record:wrong}});assert.equal((await cached.run()).status,200);assert.equal(cached.calls.length,1);
});
await test('external text cannot execute HTML or break replacement markers',async()=>{
 const evil=structuredClone(record);evil.protocolSection.identificationModule.briefTitle='<script>alert(1)</script> $&';evil.protocolSection.descriptionModule.briefSummary='<img src=x onerror=alert(1)> $&';const s=setup({payload:evil});const h=await(await s.run()).text();assert.ok(!h.includes('<script>alert(1)</script>'));assert.ok(!h.includes('<img src=x'));assert.ok(h.includes('&lt;script&gt;'));assert.ok(h.includes('$&amp;')||h.includes('$&'));assert.ok(!h.includes('__TRIAL_'));
});
await test('rate limit and missing contact do not send an upstream request',async()=>{
 for(const opts of [{deny:true},{contact:false}]){const s=setup(opts);const r=await s.run();assert.equal(r.status,503);assert.equal(s.calls.length,0);assert.equal(r.headers.get('retry-after'),'60');}
});
await test('HEAD returns no body; unsupported method is rejected',async()=>{
 const s=setup();assert.equal(await(await s.run(undefined,{method:'HEAD'})).text(),'');const p=setup();assert.equal((await p.run(undefined,{method:'POST'})).status,405);assert.equal(p.calls.length,0);
});
await test('KV failure does not break a successful response',async()=>{
 const s=setup();s.env.LOOKUP_RESULTS={get:async()=>{throw Error('kv')},put:async()=>{throw Error('kv')}};assert.equal((await s.run()).status,200);
});

await test('the public Worker serves trial HTML without lookup credentials',async()=>{
 const s=setup();
 const response=await handle(new Request('http://localhost/trials/'+id),s.env,{trial:{fetch:async()=>Response.json(record),now:()=>now}});
 assert.equal(response.status,200);
 assert.equal(response.headers.get('x-robots-tag'),'noindex, follow');
 const html=await response.text();
 assert.ok(html.includes('href="https://whatcameofit.com/trials/'+id+'"'));
 assert.ok(html.includes('A study of CIN-107'));
 assert.ok(!html.includes('__TRIAL_'));
});

await test('the private template cannot be opened through the public Worker',async()=>{
 const s=setup();
 for(const suffix of ['', '/', '.html', '/index', '/index.html']) {
  const response=await handle(new Request('http://localhost/trial-reader'+suffix),s.env);
  assert.equal(response.status,404,suffix);
  assert.ok(!(await response.text()).includes('__TRIAL_'));
 }
});

await test('marker-like registry text cannot consume the reader template',async()=>{
 const unusual=structuredClone(record);
 unusual.protocolSection.identificationModule.briefTitle='A __TRIAL_CONTENT__ & __TRIAL_ID__ Study';
 const s=setup({payload:unusual});
 const html=await(await s.run()).text();
 assert.ok(html.includes('<title>A __TRIAL_CONTENT__ &amp; __TRIAL_ID__ Study | What came of it?</title>'));
 assert.ok(html.includes('<h1>A __TRIAL_CONTENT__ &amp; __TRIAL_ID__ Study</h1>'));
 assert.ok(html.includes('Study overview'));
 assert.ok(!html.includes('<main class="trial-reader">__TRIAL_CONTENT__'));
 assert.ok(html.includes('href="https://whatcameofit.com/trials/'+id+'"'));
});
