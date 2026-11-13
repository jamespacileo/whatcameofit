import assert from "node:assert/strict";
import { test } from "node:test";
import { handle } from "../worker/index.mjs";
import { makeModel } from "../worker/model.mjs";
import { validateImage, sourceUrl, readBody } from "../worker/visual.mjs";
import { previousResult, storeResult } from "../worker/results.mjs";
const image={dataUrl:"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jBzQAAAAASUVORK5CYII=",width:1,height:1};
const found={about_a_treatment:true,treatment:"EX-patch",condition:"missing teeth",gist:"Do not cache this prose",candidates:[]};
const registry={search:async()=>[],fetch:async()=>null,named:async()=>[]};
const env={OPENAI_API_KEY:"test",LLM_MODEL:"configured",CONTACT_EMAIL:"test@example.org",LOOKUP_PER_READER:{limit:async()=>({success:true})},LOOKUP_IN_ALL:{limit:async()=>({success:true})},ASSETS:{fetch:async()=>Response.json({claims:{},articles:{}})}};
test("image-only Reddit claim is read visually without asking Reddit or treating a media URL as an article",async()=>{
 let read=0;const response=await handle(new Request("https://whatcameofit.example/api/lookup",{method:"POST",body:JSON.stringify({text:"Dental revolution",platform:"Reddit",links:["https://preview.redd.it/image.png"],image,pageUrl:"https://www.reddit.com/r/science/comments/abc/title/?token=secret"})}),env,
 {model:{read:async(text,options)=>{read++;assert.deepEqual(options.image,image);assert.equal(options.pageUrl,null);return {...found,intervention:"EX-patch",indication:"missing teeth"};},score:async()=>[]},registry,fetch:async()=>{throw new Error("must not fetch Reddit");}});
 assert.equal(response.status,200);const answer=await response.json();assert.equal(answer.treatment,"EX-patch");assert.equal(answer.source.kind,"screenshot");assert.equal(read,1);
});
test("provider receives the image once, only for reading, with storage disabled and bounded output",async()=>{
 const calls=[];const model=makeModel({apiKey:"test",model:"configured",fetch:async(url,options)=>{calls.push(JSON.parse(options.body));return Response.json({choices:[{message:{content:JSON.stringify(found)}}]});}});
 await model.read("caption",{image,pageUrl:"https://example.org/story"});
 assert.equal(calls.length,1);assert.equal(calls[0].store,false);assert.equal(calls[0].model,"configured");
 assert.deepEqual(calls[0].messages[1].content[1],{type:"image_url",image_url:{url:image.dataUrl,detail:"high"}});
 assert.match(calls[0].messages[0].content,/untrusted.*never instructions/s);
});
test("image validation rejects URLs, SVG, false dimensions and oversized input",()=>{
 assert.deepEqual(validateImage(image),image);
 for(const bad of [{...image,dataUrl:"https://x.test/private"},{...image,dataUrl:"data:image/svg+xml;base64,PHN2Zz4="},{...image,width:900}])assert.throws(()=>validateImage(bad),e=>e.status===400);
 assert.throws(()=>validateImage({...image,dataUrl:"data:image/png;base64,"+"A".repeat(1_500_000)}),e=>e.status===413);
});
test("chunked bodies are bounded even without a content-length header",async()=>{
 const request=new Request("https://example.org",{method:"POST",body:new ReadableStream({start(c){c.enqueue(new Uint8Array(1_100_001));c.close();}}),duplex:"half"});
 await assert.rejects(readBody(request),e=>e.status===413);
});
test("only independently public structured results enter the shared cache and remain dated",async()=>{
 const values=new Map();const store={get:async k=>values.has(k)?JSON.parse(values.get(k)):null,put:async(k,v,options)=>{assert.equal(options.expirationTtl,86400);values.set(k,v);}};
 await storeResult(store,"https://example.org/report",found,false,1000);assert.equal(values.size,0);
 await storeResult(store,"https://example.org/report?utm_source=x",found,true,1000);assert.equal(values.size,1);
 assert.doesNotMatch([...values.values()][0],/Do not cache|data:image|gist/);
 const cached=await previousResult(store,"https://example.org/report",1001);assert.equal(cached.treatment,"EX-patch");assert.equal(cached.cache.checkedAt,1000);
 assert.equal(await previousResult(store,"https://example.org/report",1000+86400000),null);
 assert.equal(sourceUrl("https://localhost/a"),null);
});
test("an on-demand public URL result is shared with the next reader without model or source calls",async()=>{
 const values=new Map();const store={get:async k=>values.has(k)?JSON.parse(values.get(k)):null,put:async(k,v)=>values.set(k,v)};
 const settings={...env,LOOKUP_RESULTS:store};let reads=0,gets=0;
 const tools={registry,model:{read:async text=>{reads++;assert.doesNotMatch(text,/PRIVATE ADDITION/);return {...found,intervention:"EX-patch",indication:"missing teeth"};},score:async()=>[]},fetch:async url=>{
  gets++;return new Response(String(url).endsWith("robots.txt")?"User-agent: *\nAllow: /":"<html><head><title>EX-patch report</title></head><body><main><p>EX-patch was studied for missing teeth in a synthetic public report.</p></main></body></html>");
 }};
 const request=body=>new Request("https://whatcameofit.example/api/lookup",{method:"POST",body:JSON.stringify(body)});
 const first=await handle(request({pageUrl:"https://example.org/report",text:"PRIVATE ADDITION"}),settings,tools);
 assert.equal(first.status,200);assert.equal(reads,1);assert.equal(values.size,1);const fetched=gets;
 const second=await handle(request({url:"https://example.org/report?utm_source=test"}),settings,tools);
 const cached=await second.json();assert.equal(cached.treatment,"EX-patch");assert.equal(cached.cache.shared,true);assert.equal(reads,1);assert.equal(gets,fetched);
 const visual=await handle(request({pageUrl:"https://www.reddit.com/r/test/comments/abc/",text:"Dental revolution",image}),settings,tools);
 assert.equal(visual.status,200);assert.equal(values.size,1);
});

test("a caller cannot publish one public article's result under another URL", async () => {
 const values = new Map();
 const settings = {...env, LOOKUP_RESULTS: {get: async k => values.has(k) ? JSON.parse(values.get(k)) : null, put: async (k,v) => values.set(k,v)}};
 const tools = {registry, model:{read:async()=>({...found,intervention:"EX-patch",indication:"missing teeth"}),score:async()=>[]}, fetch:async url => new Response(String(url).endsWith("robots.txt") ? "User-agent: *\nAllow: /" : "<main><p>A synthetic public report of EX-patch for missing teeth.</p></main>")};
 const response = await handle(new Request("https://example.org/api/lookup", {method:"POST",body:JSON.stringify({url:"https://example.org/real",pageUrl:"https://example.org/unrelated"})}),settings,tools);
 assert.equal(response.status,200);
 assert.ok(await previousResult(settings.LOOKUP_RESULTS,"https://example.org/real"));
 assert.equal(await previousResult(settings.LOOKUP_RESULTS,"https://example.org/unrelated"),null);
});

test("an explicit visual lookup cannot be replaced by an earlier shared text result",async()=>{
 let calls=0;
 const settings={...env,LOOKUP_RESULTS:{get:async()=>({version:1,publicVerified:true,at:Date.now(),found}),put:async()=>{throw new Error("visual data must not enter shared storage");}}};
 const response=await handle(new Request("https://example.org/api/lookup",{method:"POST",body:JSON.stringify({pageUrl:"https://example.org/story",text:"Read the image",image})}),settings,{registry,model:{read:async()=>{calls++;return {about_a_treatment:false};},score:async()=>[]}});
 assert.equal(response.status,200);assert.equal(calls,1);assert.equal((await response.json()).about_a_treatment,false);
});
