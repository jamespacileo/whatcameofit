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
 Object.assign(globalThis,{document,window,location:new URL(url),getSelection:()=>selection,innerWidth:1000,innerHeight:800,getComputedStyle:node=>({display:node.hidden?'none':'block',visibility:'visible',overflowX:node.getAttribute('data-overflow-x')??'visible',overflowY:node.getAttribute('data-overflow-y')??'visible'})});
 window.HTMLElement.prototype.getBoundingClientRect=function(){const top=Number(this.getAttribute('data-top')??0),left=Number(this.getAttribute('data-left')??0),width=Number(this.getAttribute('data-width')??600),height=Number(this.getAttribute('data-height')??700);return {x:left,y:top,left,top,right:left+width,bottom:top+height,width,height};};
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

test('an Instagram carousel captures only its unique visible slide inside the bound viewport', () => {
 const url='https://www.instagram.com/p/ABC123/?img_index=2';
 const head='<meta property="og:url" content="https://www.instagram.com/p/ABC123/"><meta property="og:image" content="https://media.example/current.jpg">';
 const image=(src,left)=>'<img src="https://media.example/'+src+'.jpg" data-left="'+left+'" data-width="480" data-height="600">';
 const carousel=(first,second,extra='')=>'<main><div data-left="300" data-width="480" data-height="600" data-overflow-x="auto" data-overflow-y="hidden"><div><ul><li>'+image('current',first)+'</li><li>'+image('second',second)+'</li></ul></div></div>'+extra+'</main>';
 let x=read(url,head,carousel(-180,300,image('recommendation',0)));
 let view=inspectVisible(x.captured.mediaScope);
 assert.equal(view.crop?.identity,'https://media.example/second.jpg');
 assert.deepEqual([view.crop.left,view.crop.width],[300,480]);
 x=read(url,head,carousel(60,540));
 assert.equal(inspectVisible(x.captured.mediaScope).unavailable,true,'two visible slides are ambiguous');
 x=read(url,head,carousel(-180,300).replace('<li>','<li><a href="/p/OTHER123/">Another post</a>'));
 assert.equal(inspectVisible(x.captured.mediaScope).unavailable,true,'a list of posts is not a carousel');
 x=read(url,head,'<main><div data-left="300" data-width="360" data-height="600" data-overflow-x="hidden">'+image('current',250)+'</div></main>');
 view=inspectVisible(x.captured.mediaScope);
 assert.deepEqual([view.crop.left,view.crop.width],[300,360],'crop excludes clipped neighbour pixels');
 x=read(url,head,carousel(-180,300).replace('<main>','<main hidden>'));
 assert.equal(inspectVisible(x.captured.mediaScope).unavailable,true,'hidden ancestors exclude media');
});

test('LinkedIn and Bluesky bind the requested post without profile sidebars or replies', () => {
 const url='https://www.linkedin.com/posts/author_trial-activity-1234567890123456789-abcd/';
 const claim='EX-17 was studied for missing teeth in a randomized clinical trial.';
 let x=read(url,'','<main><aside>PRIVATE_PROFILE_ANALYTICS</aside><div role="listitem" componentkey="update-card-focus-current"><a href="'+url+'"><div aria-labelledby="reactions">Reactions</div></a><span data-testid="expandable-text-box">'+claim+'</span><div componentkey="comment-nested">NESTED_REPLY_OTHER_DRUG</div><div componentkey="commentBox-draft">PRIVATE_DRAFT</div></div><div role="listitem" componentkey="comment-current"><a href="'+url+'">Reply</a>REPLY_OTHER_DRUG</div></main>');
 assert.ok(x.request?.text.includes('EX-17'));
 assert.ok(!x.request.text.includes('PRIVATE_PROFILE_ANALYTICS'));
 assert.ok(!x.request.text.includes('REPLY_OTHER_DRUG'));
 assert.ok(!x.request.text.includes('PRIVATE_DRAFT'));
 assert.equal(inspectVisible(x.captured.mediaScope).unavailable,true,'text-only post cannot capture the sidebar');
 x=read(url,'','<main>PRIVATE_PROFILE_ANALYTICS<div role="listitem" componentkey="update-card-focus-other"><a href="/posts/author_other-activity-9999999999999999999-abcd/">Other post</a>'+claim+'</div></main>');
 assert.equal(x.request,null,'stale post identity fails closed');
 x=read(url,'<meta property="og:url" content="'+url+'"><meta property="og:description" content="'+claim+'">',
  '<main>Sign in PRIVATE_PROFILE_ANALYTICS<img src="https://media.example/unrelated.jpg"></main>');
 assert.ok(x.request?.text.includes('EX-17'),'identity-bound public caption works in another layout');
 assert.equal(inspectVisible(x.captured.mediaScope).unavailable,true,'public metadata alone cannot bind unrelated pixels');
 x=read(url,'<meta property="og:url" content="https://www.linkedin.com/posts/author_other-activity-9999999999999999999-abcd/"><meta property="og:description" content="'+claim+'">','<main>Sign in</main>');
 assert.equal(x.request,null);
 const bsky='https://bsky.app/profile/journal.example/post/3abcdef12345';
 x=read(bsky,'','<main><div data-testid="postThreadItem-by-journal.example"><div>'+claim+'</div><a href="'+bsky+'/liked-by"><div data-testid="likeCount-expanded">Likes</div></a></div><div data-testid="postThreadItem-by-other.example">REPLY_OTHER_DRUG<a href="/profile/other.example/post/3abc99999999">Reply</a></div></main>');
 assert.ok(x.request?.text.includes('EX-17'));
 assert.ok(!x.request.text.includes('REPLY_OTHER_DRUG'));
 x=read(bsky,'','<main><div data-testid="postThreadItem-by-journal.example">STALE_OTHER_DRUG<a href="/profile/journal.example/post/3abc99999999/liked-by">Likes</a></div></main>');
 assert.equal(x.request,null);
 x=read(bsky,'','<main><div data-testid="postThreadItem-by-journal.example">STALE_OTHER_DRUG<a href="/profile/journal.example/post/3abc99999999/liked-by"><div data-testid="likeCount-expanded">Likes</div></a><a href="'+bsky+'">Replying to original</a></div></main>');
 assert.equal(x.request,null,'an inline link cannot impersonate the requested post');
 x=read(url,'','<main><div role="listitem" componentkey="update-card-focus-other"><a href="/posts/author_other-activity-9999999999999999999-abcd/"><div aria-labelledby="reactions">Reactions</div></a><span data-testid="expandable-text-box">STALE_OTHER_DRUG<a href="'+url+'">Cited original</a></span></div></main>');
 assert.equal(x.request,null,'a cited post cannot identify the containing LinkedIn post');
 const chosen='Selected EX-42 report for the named condition.';
 x=read(url,'','<main>PRIVATE_PROFILE_ANALYTICS</main>',chosen);
 assert.equal(x.request.text,chosen);
 assert.deepEqual(x.request.links,[]);
});

test('an image-only LinkedIn post keeps only its uniquely owned attachment', () => {
 const url='https://www.linkedin.com/posts/author_trial-activity-1234567890123456789-abcd/';
 const image='<a href="'+url+'"><figure><img src="https://media.example/current.jpg"></figure></a>';
 const root=inside=>'<main><aside><img src="https://media.example/sidebar.jpg"></aside><div role="listitem" componentkey="update-card-focus-current">'+inside+'<div componentkey="comment-nested"><img src="https://media.example/reply.jpg"></div></div></main>';
 let x=read(url,'',root(image));
 assert.equal(x.request,null);
 assert.equal(inspectVisible(x.captured.mediaScope).crop?.identity,'https://media.example/current.jpg');
 x=read(url,'',root(image+image.replace('current.jpg','second.jpg')));
 assert.equal(inspectVisible(x.captured.mediaScope).unavailable,true,'two owned attachments remain ambiguous');
});

