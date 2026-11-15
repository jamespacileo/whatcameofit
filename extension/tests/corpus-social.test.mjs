import assert from 'node:assert/strict';
import {parseHTML} from '../../site/node_modules/linkedom/esm/index.js';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {test} from 'node:test';
const root=fileURLToPath(new URL('../../',import.meta.url)).replace(/\/$/,'');
const {collectFromPage,composeRequest}=await import(pathToFileURL(root+'/extension/src/open-page.js'));
const {readAddress}=await import(pathToFileURL(root+'/site/src/lib/lookup-match.mjs'));
const {readPage,pageAsText}=await import(pathToFileURL(root+'/site/worker/page.mjs'));
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

