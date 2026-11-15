import assert from 'node:assert/strict';
import {parseHTML} from '../../site/node_modules/linkedom/esm/index.js';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {test} from 'node:test';
const root=fileURLToPath(new URL('../../',import.meta.url)).replace(/\/$/,'');
const {collectFromPage,composeRequest}=await import(pathToFileURL(root+'/extension/src/open-page.js'));
const {readAddress}=await import(pathToFileURL(root+'/site/src/lib/lookup-match.mjs'));
const {readPage,pageAsText}=await import(pathToFileURL(root+'/site/worker/page.mjs'));
const {inspectVisible,capturePage}=await import(pathToFileURL(root+'/extension/src/visual.js'));
function read(url,head,body,selection='') {
 const {document,window}=parseHTML('<html><head>'+head+'</head><body>'+body+'</body></html>');
 Object.assign(globalThis,{document,window,location:new URL(url),getSelection:()=>selection,innerWidth:1000,innerHeight:800,getComputedStyle:()=>({display:'block',visibility:'visible'})});
 window.HTMLElement.prototype.getBoundingClientRect=function(){const top=Number(this.getAttribute('data-top')??0);return {x:0,y:top,left:0,top,right:600,bottom:top+700,width:600,height:700};};
 const captured=collectFromPage();
 return {captured,request:composeRequest(captured,url,{readAddress,readPage,pageAsText})};
}
test('social corpus reads only the requested post and rejects stale identities', () => {
const trials='EX-17 and EX-29 were studied in a randomized trial for bladder cancer.';
let x=read('https://www.threads.com/@journal/post/ABC123/long-slug','<meta property="og:url" content="https://www.threads.com/@journal/post/ABC123"><meta property="og:description" content="'+trials+'">','<main>Log in<div>'+trials+'</div><section>Related threads UNRELATED_REPLY_DRUG</section></main>');
assert.ok(x.request?.text.includes('EX-17'),'Threads must read the addressed post');
assert.ok(!x.request.text.includes('UNRELATED_REPLY_DRUG'),'Threads must exclude related threads');
x=read('https://www.instagram.com/p/ABC123/','<meta property="og:url" content="https://www.instagram.com/journal/p/ABC123/"><meta property="og:description" content="8 likes, 2 comments - journal on November 1, 2026: &quot;'+trials+'&quot;.">','<main>Log in<div>'+trials+'</div><section>COMMENT_OTHER_DRUG</section></main>');
assert.ok(x.request?.text.includes('EX-17'),'Instagram must read the caption');
assert.ok(!x.request.text.includes('COMMENT_OTHER_DRUG'),'Instagram must exclude comments');
x=read('https://www.instagram.com/p/NEW123/','<meta property="og:url" content="https://www.instagram.com/journal/p/OLD123/"><meta property="og:description" content="'+trials+'">','<main>STALE_POST '+trials+'</main>');
assert.equal(x.request,null,'Mismatched Instagram identity must not read old post');
x=read('https://www.instagram.com/p/NEW123/','<meta property="og:description" content="8 likes: &quot;'+trials+'&quot;.">','<main>'+trials+'</main>');
assert.equal(x.request,null,'Missing Instagram identity must not authorize a caption');
x=read('https://t.me/s/journal/10951','','<main><div data-post="journal/10940"><div class="tgme_widget_message_text">NEIGHBOUR_WRONG_DRUG for cancer</div></div><div class="tgme_widget_message" data-post="journal/10951"><div class="tgme_widget_message_text">'+trials+'</div><div>100 views</div></div></main>');
assert.ok(x.request?.text.includes('EX-17'),'Telegram must read addressed message');
assert.ok(!x.request.text.includes('NEIGHBOUR_WRONG_DRUG'),'Telegram must exclude other messages');
x=read('https://t.me/s/journal/99999','','<main><div data-post="journal/10940"><div class="tgme_widget_message_text">'+trials+'</div></div></main>');
assert.equal(x.request,null,'Missing Telegram message must fail closed');
const tturl='https://www.tiktok.com/@journal/video/1234567890123456789';
const ttbody='<article id="one-column-item-0" data-scroll-index="0" data-e2e="recommend-list-item-container"><section data-e2e="feed-video"><div data-e2e="video-desc">'+trials+'</div><a href="/@journal">journal</a><video></video></section></article><article id="one-column-item-1" data-scroll-index="1" data-e2e="recommend-list-item-container" data-top="900"><div data-e2e="video-desc">'+('WRONG_VIDEO '.repeat(40))+'</div><a href="/@journal">journal</a></article>';
x=read(tturl,'<link rel="canonical" href="'+tturl+'">',ttbody);
assert.ok(x.request?.text.includes('EX-17'),'TikTok must choose the visible current post');
assert.ok(!x.request.text.includes('WRONG_VIDEO'),'TikTok must not choose largest recommendation');
x=read(tturl,'<link rel="canonical" href="https://www.tiktok.com/@journal/video/9999999999999999999">',ttbody);
assert.equal(x.request,null,'Mismatched TikTok identity must fail closed');
const chosen='I selected a specific sentence about EX-42 treating a condition.';
x=read('https://www.instagram.com/p/NEW123/','<meta property="og:url" content="https://www.instagram.com/journal/p/OLD123/">','<main>Unrelated content.</main>',chosen);
assert.equal(x.request.text,chosen,'Explicit selection retains precedence');
assert.deepEqual(x.request.links,[]);
x=read(tturl,'<link rel="canonical" href="'+tturl+'"><meta property="og:url" content="'+tturl+'"><meta property="og:description" content="'+trials+'">','<article id="one-column-item-0" data-scroll-index="0" data-e2e="recommend-list-item-container"><div>Video could not play</div></article>');
assert.ok(x.request?.text.includes('EX-17'),'A current TikTok public caption remains readable when video playback fails');
});

test('a scoped social post without visible media never captures neighbouring content', async () => {
 for (const [url,head,body] of [
  ['https://t.me/s/journal/123','',
   '<div data-post="journal/123"><div class="tgme_widget_message_text">A text-only report.</div></div><div data-post="journal/124"><img src="https://media.example/other.jpg"></div>'],
  ['https://www.tiktok.com/@journal/video/123',
   '<link rel="canonical" href="https://www.tiktok.com/@journal/video/123">',
   '<article data-e2e="recommend-list-item-container" data-scroll-index="0"><div data-e2e="video-desc">A caption without a playable video.</div></article><article><video src="https://media.example/other.mp4"></video></article>'],
 ]) {
  const {captured}=read(url,head,body);
  const visible=inspectVisible(captured.mediaScope);
  assert.equal(visible.unavailable,true);
  assert.equal(visible.crop,null);
  let captures=0;
  const tab={id:1,windowId:1,url};
  const api={tabs:{query:async()=>[tab],captureVisibleTab:async()=>{captures++;return 'pixels';}},
   scripting:{executeScript:async({func,args=[]})=>[{result:func(...args)}]}};
  await assert.rejects(capturePage(api,tab,null,async()=>({})),e=>e.code==='capture_unavailable');
  assert.equal(captures,0);
 }
});

test('social media needs its own identity even when it is the only visible video', () => {
 for (const [url,description] of [
  ['https://www.instagram.com/p/ABC123/','8 likes: &quot;EX-17 was studied for missing teeth in a synthetic randomized clinical trial.&quot;.'],
  ['https://www.threads.com/@journal/post/ABC123','EX-17 was studied for missing teeth in a synthetic randomized clinical trial.'],
 ]) {
  const head='<meta property="og:url" content="'+url+'"><meta property="og:description" content="'+description+'"><meta property="og:image" content="https://media.example/current.jpg">';
  let x=read(url,head,'<main><article>Current post</article><article><video src="https://media.example/unrelated.mp4" poster="https://media.example/other.jpg"></video></article></main>');
  assert.ok(x.request?.text.includes('EX-17'));
  assert.equal(inspectVisible(x.captured.mediaScope).unavailable,true);
  x=read(url,head,'<main><video poster="https://media.example/current.jpg" src="blob:current"></video></main>');
  assert.equal(inspectVisible(x.captured.mediaScope).crop.kind,'video');
 }
});

test('an identity-matched image-only post retains its bounded visual fallback', () => {
 const url='https://www.instagram.com/p/ABC123/';
 const x=read(url,'<meta property="og:url" content="'+url+'"><meta property="og:image" content="https://media.example/current.jpg">',
  '<main><img src="https://media.example/current.jpg"><video src="https://media.example/other.mp4"></video></main>');
 assert.equal(x.request,null);
 const visible=inspectVisible(x.captured.mediaScope);
 assert.equal(visible.unavailable,false);
 assert.equal(visible.crop.kind,'img');
 assert.equal(visible.crop.identity,'https://media.example/current.jpg');
});

