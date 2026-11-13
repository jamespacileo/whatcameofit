import assert from "node:assert/strict";
import { test } from "node:test";
import { createPopupController } from "../src/controller.js";
import { capturePage, publicPageUrl } from "../src/visual.js";
import { remember, reusable, RESULT_TTL } from "../src/results.js";
const image={dataUrl:"data:image/jpeg;base64,fixture",width:100,height:100};
const tab={id:7,windowId:3,url:"https://www.reddit.com/r/science/comments/abc/report/",key:"reddit.com/r/science/comments/abc/report"};
const found={about_a_treatment:true,treatment:"EX-patch",candidates:[],source:{kind:"screenshot"}};
function setup(extra={}) {
 const saved={},calls={paid:[],capture:0,states:[]};
 const controller=createPopupController({storage:{get:async key=>typeof key==="string"?{}:saved,set:async value=>Object.assign(saved,value)},site:{url:"https://whatcameofit.example"},
 readTab:async()=>tab,readPage:async()=>({text:"Dental revolution",links:[],visualCandidate:true,contentFingerprint:"page-fingerprint"}),
 capturePage:async()=>{calls.capture++;return {image,pageUrl:tab.url};},isCurrentPage:async()=>true,
 fetch:async(url,options)=>{if(options.method!=="POST")return {ok:true,json:async()=>({articles:{},claims:{},live:"/api/lookup"})};const body=JSON.parse(options.body);if(body.cacheOnly)return {ok:true,json:async()=>({cacheMiss:true})};calls.paid.push(body);return {ok:true,json:async()=>found};},
 describeAnswer:f=>({...f,marked:"Automatic search just now"}),present:s=>calls.states.push(s),...extra});
 return {controller,calls,saved};
}
test("image-only post automatically sends one bounded image lookup; another opening reuses the local result",async()=>{
 const {controller,calls,saved}=setup();await controller.open();
 assert.equal(calls.capture,1);assert.equal(calls.paid.length,1);assert.deepEqual(calls.paid[0].image,image);
 assert.equal(calls.paid[0].visualCandidate,undefined);assert.equal(calls.paid[0].contentFingerprint,undefined);
 assert.doesNotMatch(JSON.stringify(saved),/data:image|Dental revolution/);
 await controller.open();assert.equal(calls.capture,2);assert.equal(calls.paid.length,1);
 assert.ok(calls.states.at(-1).cachedAt);assert.doesNotMatch(calls.states.at(-1).shown.marked,/just now/);
 await controller.search();assert.equal(calls.paid.length,2);
 await controller.clearRecent();assert.deepEqual(saved.results,[]);
});
test("shared cache hit avoids screenshot and paid lookup",async()=>{
 const {controller,calls}=setup({readPage:async()=>({text:"Dental revolution",links:[],visualCandidate:true,pageUrl:tab.url}),
 fetch:async(_url,options)=>({ok:true,json:async()=>options.method==="POST"?{...found,cache:{shared:true,checkedAt:1234}}:{articles:{},claims:{},live:"/api/lookup"}})});
 await controller.open();assert.equal(calls.capture,0);assert.equal(calls.states.at(-1).cachedAt,1234);
});
test("a shared miss makes one probe and one lookup; navigation during the probe stops capture",async()=>{
 for (const navigate of [false,true]) {
  let current=true;const requests=[];
  const {controller,calls}=setup({readPage:async()=>({text:"Dental revolution",links:[],visualCandidate:true,pageUrl:tab.url}),
   isCurrentPage:async()=>current,fetch:async(_url,options)=>{
    if(options.method!=="POST")return {ok:true,json:async()=>({articles:{},claims:{},live:"/api/lookup"})};
    const body=JSON.parse(options.body);requests.push(body);
    if(body.cacheOnly){if(navigate)current=false;return {ok:true,json:async()=>({cacheMiss:true})};}
    return {ok:true,json:async()=>found};
   }});
  await controller.open();assert.equal(requests.length,navigate?1:2);assert.equal(calls.capture,navigate?0:1);
  if(navigate)assert.equal(calls.states.at(-1).code,"page_changed");
 }
});
test("an inconclusive text lookup tries the visible image once",async()=>{
 const requests=[];
 const {controller,calls}=setup({readPage:async()=>({text:"A caption with no readable intervention name. ".repeat(8),links:[],visualCandidate:true}),
  fetch:async(_url,options)=>{
   if(options.method!=="POST")return {ok:true,json:async()=>({articles:{},claims:{},live:"/api/lookup"})};
   const body=JSON.parse(options.body);requests.push(body);
   return {ok:true,json:async()=>body.image?found:{about_a_treatment:false}};
  }});
 await controller.open();assert.equal(requests.length,2);assert.equal(calls.capture,1);assert.ok(requests[1].image);
});
test("selected words suppress automatic capture and cache reuse",async()=>{
 const {controller,calls}=setup({readPage:async()=>({text:"The selected report says EX-1 restored missing teeth.",links:[],selectionOnly:true,visualCandidate:true})});
 await controller.open();assert.equal(calls.capture,0);assert.equal(calls.paid.length,1);assert.equal(calls.paid[0].image,undefined);
});
test("a capture resolving after popup close sends and stores nothing",async()=>{
 let finish,started;const ready=new Promise(r=>started=r);
 const {controller,calls,saved}=setup({capturePage:()=>{started();return new Promise(r=>finish=r);}});
 const opening=controller.open();await ready;controller.close();finish({image,pageUrl:tab.url});await opening;
 assert.equal(calls.paid.length,0);assert.equal(saved.results,undefined);
});
test("failed or negative lookups cannot poison a reusable answer; changed content and expired results miss",()=>{
 const now=Date.now(),entries=remember([],"page","fingerprint",found,now);
 assert.ok(reusable(entries,"page","fingerprint",now+1));
 assert.equal(reusable(entries,"page","different",now+1),null);
 assert.equal(reusable(entries,"page","fingerprint",now+RESULT_TTL),null);
 assert.deepEqual(remember([],"page","f",{about_a_treatment:false},now),[]);
});
test("capture uses the requested window and rejects tab switches before transmitting pixels",async()=>{
 let active={...tab};let captures=0;
 const metadata={address:tab.url,sensitive:false,hidden:false,width:100,height:100,crop:null};
 const api={tabs:{query:async()=>[active],captureVisibleTab:async windowId=>{assert.equal(windowId,3);captures++;active={...tab,id:9};return "data:image/jpeg;base64,fixture";}},scripting:{executeScript:async()=>[{result:metadata}]}};
 await assert.rejects(capturePage(api,tab,new AbortController().signal,async()=>image),e=>e.code==="page_changed");
 assert.equal(captures,1);
 active={...tab,id:9};await assert.rejects(capturePage(api,tab,null,async()=>image),e=>e.code==="page_changed");assert.equal(captures,1);
});
test("capture refuses private windows, password forms and non-web or local addresses",async()=>{
 const api={tabs:{query:async()=>[tab],captureVisibleTab:async()=>{throw new Error("must not capture");}},scripting:{executeScript:async()=>[{result:{address:tab.url,sensitive:true,hidden:false}}]}};
 await assert.rejects(capturePage(api,tab,null),e=>e.code==="capture_sensitive");
 await assert.rejects(capturePage(api,{...tab,incognito:true},null),e=>e.code==="capture_unavailable");
 for(const address of ["file:///tmp/x","https://127.0.0.1/x","https://user:secret@example.org/x","chrome://extensions","http://box.local/x"])assert.equal(publicPageUrl(address),null);
 assert.equal(publicPageUrl("https://www.reddit.com/r/science/comments/abc/title/?token=secret#private"),null);
 assert.notEqual(publicPageUrl("https://example.org/?p=1"), publicPageUrl("https://example.org/?p=2"));
});

test("changed pixels at an unchanged canvas or image URL do not reuse the prior visual answer", async () => {
 let pixels = "first frame";
 const {controller,calls} = setup({capturePage:async()=>({image:{...image,dataUrl:pixels},pageUrl:tab.url})});
 await controller.open();assert.equal(calls.paid.length,1);
 pixels = "second frame";
 await controller.open();assert.equal(calls.paid.length,2);
});

test("a short social caption with an article link keeps the reviewed-article path before screenshots",async()=>{
 const {controller,calls}=setup({readPage:async()=>({text:"Read this",links:["https://example.org/report"],platform:"Reddit",visualCandidate:true})});
 await controller.open();assert.equal(calls.capture,0);assert.equal(calls.paid[0].image,undefined);assert.deepEqual(calls.paid[0].links,["https://example.org/report"]);
});

test("an embedded document intersecting capture is refused before pixels are taken",async()=>{
 const api={tabs:{query:async()=>[tab],captureVisibleTab:async()=>{throw new Error("must not capture");}},scripting:{executeScript:async()=>[{result:{address:tab.url,sensitive:false,embedded:true,hidden:false}}]}};
 await assert.rejects(capturePage(api,tab,null),e=>e.code==="capture_embedded");
});

test("first use asks before reading or sending; permission persists and can be withdrawn",async()=>{
 let reads=0;
 const {controller,calls,saved}=setup({requiresSharingConsent:true,readPage:async()=>{reads++;return {text:"Dental revolution",links:[],visualCandidate:true};}});
 await controller.open();assert.equal(reads,0);assert.equal(calls.capture,0);assert.equal(calls.paid.length,0);assert.equal(calls.states.at(-1).kind,"sharing");
 await controller.enableSharing();assert.equal(reads,1);assert.equal(calls.paid.length,1);assert.equal(saved.sharing.enabled,true);
 await controller.disableSharing();await controller.open();assert.equal(reads,1);assert.equal(saved.sharing.enabled,false);
 await controller.previewVisual();assert.equal(calls.capture,1);
});

test("failed permission writes never silently enable or claim a durable withdrawal",async()=>{
 const saved={sharing:{version:1,enabled:true}};
 const {controller,calls}=setup({requiresSharingConsent:true,storage:{get:async key=>typeof key==="string"?{}:saved,set:async value=>{if(value.sharing)throw Error("disk full");}}});
 await controller.open();assert.equal(calls.paid.length,1);
 await controller.disableSharing();assert.equal(calls.states.at(-1).kind,"sharing-error");
 await controller.open();assert.equal(calls.paid.length,1);
 await controller.enableSharing();assert.equal(calls.states.at(-1).kind,"sharing-error");assert.equal(calls.paid.length,1);
});
