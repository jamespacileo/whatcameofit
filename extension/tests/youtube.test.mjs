// Synthetic page fixtures: never real video descriptions, transcripts or account data.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { test } from "node:test";
import { collectFromPage, composeRequest } from "../src/open-page.js";
import { capturePage, inspectVisible, publicPageUrl } from "../src/visual.js";
import { articleKey } from "../../site/src/lib/article-key.mjs";
import { readAddress } from "../../site/src/lib/lookup-match.mjs";
import { readPage, pageAsText } from "../../site/worker/page.mjs";

const { parseHTML } = createRequire(new URL("../../site/package.json", import.meta.url))("linkedom");
const video = "EX_test0001";
const other = "EX_test0002";
const address = `https://www.youtube.com/watch?v=${video}`;
const shared = { readAddress, readPage, pageAsText };
const watch = `<ytd-watch-flexy video-id="${video}">
  <div id="title"><h1>EX-patch studied for missing teeth</h1></div>
  <ytd-watch-metadata><div id="description">A synthetic report of EX-patch for missing teeth.
    <a href="https://www.youtube.com/redirect?q=https%3A%2F%2Fresearch.example.org%2Freport">Source report</a>
  </div></ytd-watch-metadata>
  <div id="movie_player"><video data-box="20,20,640,360" src="https://media.example.org/video"></video>
    <span class="ytp-caption-segment">The current caption names EX-patch.</span>
  </div>
  <ytd-transcript-segment-renderer><span class="segment-text">A loaded transcript describes the synthetic study.</span></ytd-transcript-segment-renderer>
  <ytd-comments><p>UNRELATED COMMENT</p><a href="https://unrelated.example.org/comment">Other treatment</a></ytd-comments>
  <div id="related"><h2>UNRELATED RECOMMENDATION</h2><img data-box="0,0,900,700" src="https://unrelated.example.org/thumb" /><video data-box="0,0,900,700" src="https://unrelated.example.org/preview"></video></div>
</ytd-watch-flexy>`;

async function onPage(html, url, action, selection = "") {
  const names = ["document", "location", "getSelection", "getComputedStyle", "innerWidth", "innerHeight"];
  const saved = new Map(names.map(name => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
  const { document } = parseHTML(`<html><head><title>STALE TAB TITLE - YouTube</title></head><body>${html}<p>PRIVATE ACCOUNT MENU</p></body></html>`);
  try {
    Object.assign(globalThis, { document, location: new URL(url), getSelection: () => selection, innerWidth: 1000, innerHeight: 800,
      getComputedStyle: node => ({ visibility: "visible", display: node.hidden ? "none" : "block" }) });
    for (const node of document.querySelectorAll("*")) {
      // LinkeDOM has no document location and its href getter re-escapes %. Use
      // browser URL resolution; selectors and text extraction still use its DOM.
      if (node.matches("a[href]")) Object.defineProperty(node, "href", { get: () => new URL(node.getAttribute("href"), url).href });
      node.getBoundingClientRect = () => {
        const [left, top, width, height] = (node.getAttribute("data-box") ?? "0,0,0,0").split(",").map(Number);
        return { left, top, width, height, right: left + width, bottom: top + height };
      };
    }
    return await action(document);
  } finally {
    for (const [name, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor);
      else delete globalThis[name];
    }
  }
}

test("watch lookup reads the current title, description, loaded captions and source links only", async () => {
  await onPage(watch, address, () => {
    const collected = collectFromPage();
    const request = composeRequest(collected, address, shared);
    assert.equal(request.platform, "YouTube");
    assert.match(request.text, /EX-patch studied for missing teeth/);
    assert.match(request.text, /current caption/);
    assert.match(request.text, /loaded transcript/);
    assert.doesNotMatch(JSON.stringify(collected), /UNRELATED|PRIVATE|STALE TAB/);
    assert.deepEqual(request.links, ["https://research.example.org/report"]);
    const visible = inspectVisible(collected.mediaScope);
    assert.equal(visible.unavailable, false);
    assert.equal(visible.media.length, 1);
    assert.equal(visible.crop.kind, "video");
    assert.equal(visible.crop.width, 640);
  });
});

test("current transcript components provide spoken text without timestamps", async () => {
  const html = watch.replace('<ytd-transcript-segment-renderer><span class="segment-text">A loaded transcript describes the synthetic study.</span></ytd-transcript-segment-renderer>',
    '<transcript-segment-view-model><div class="ytwTranscriptSegmentViewModelTimestamp">0:42</div><div class="ytwTranscriptSegmentViewModelTimestampA11yLabel">42 seconds</div><span role="text" class="ytAttributedStringHost">The spoken claim concerns EX-spoken for a synthetic indication.</span></transcript-segment-view-model>');
  await onPage(html, address, () => {
    const request = composeRequest(collectFromPage(), address, shared);
    assert.match(request.text, /EX-spoken for a synthetic indication/);
    assert.doesNotMatch(request.text, /0:42|42 seconds/);
  });
});

test("YouTube's generated description help links are not article sources", async () => {
  const html = watch.replace('</div></ytd-watch-metadata>',
    '<a href="https://support.google.com/youtube/answer/15569972">Learn more</a></div></ytd-watch-metadata>');
  await onPage(html, address, () => {
    const request = composeRequest(collectFromPage(), address, shared);
    assert.deepEqual(request.links, ["https://research.example.org/report"]);
  });
});

test("Shorts reads only the active video even when the next video is preloaded", async () => {
  const html = `<ytd-reel-video-renderer video-id="${other}"><h2>UNRELATED NEXT VIDEO</h2><video data-box="0,0,900,700"></video></ytd-reel-video-renderer>
    <ytd-reel-video-renderer is-active video-id="${video}"><h2>EX-patch studied for missing teeth in a synthetic trial</h2>
      <video data-box="10,10,300,600"></video></ytd-reel-video-renderer>`;
  const url = `https://www.youtube.com/shorts/${video}`;
  await onPage(html, url, () => {
    const collected = collectFromPage();
    assert.match(composeRequest(collected, url, shared).text, /^EX-patch/);
    assert.doesNotMatch(JSON.stringify(collected), /UNRELATED/);
    assert.equal(inspectVisible(collected.mediaScope).crop.width, 300);
  });
});

test("current desktop Shorts identifies its video through the player's title link without an active marker", async () => {
  const url = `https://www.youtube.com/shorts/${video}`;
  await onPage(`<ytd-reel-video-renderer><h1 class="ytShortsVideoTitleViewModelShortsVideoTitle">EX-patch studied for missing teeth in a synthetic trial</h1><div id="shorts-player"><a class="ytp-title-link" href="https://www.youtube.com/shorts/${video}">Player title</a><video data-box="10,10,300,600"></video></div></ytd-reel-video-renderer>`, url, () => {
    const collected = collectFromPage();
    assert.match(composeRequest(collected, url, shared).text, /EX-patch/);
    assert.equal(inspectVisible(collected.mediaScope).media.length, 1);
  });
});

test("a recommendation permalink cannot bind an ID-less watch page or Short to the current video", async () => {
  for (const [tag, url] of [["ytd-watch-flexy", address], ["ytd-reel-video-renderer", `https://www.youtube.com/shorts/${video}`]]) {
    await onPage(`<${tag} is-active><h1>STALE OTHER VIDEO</h1><div id="related"><a href="/shorts/${video}">Recommendation</a></div><video data-box="10,10,640,360"></video></${tag}>`, url, () => {
      const collected = collectFromPage();
      assert.equal(composeRequest(collected, url, shared), null);
      assert.equal(inspectVisible(collected.mediaScope).unavailable, true);
    });
  }
});

test("a changed video URL, missing renderer or non-video page never reads stale content or thumbnails", async () => {
  for (const url of [`https://www.youtube.com/watch?v=${other}`, "https://www.youtube.com/", "https://www.youtube.com/results?search_query=teeth", "https://www.youtube.com/@example", "https://www.youtube.com/watch?v=bad"]) {
    await onPage(watch, url, () => {
      const collected = collectFromPage();
      assert.equal(composeRequest(collected, url, shared), null);
      assert.deepEqual(collected.links, []);
      const visible = inspectVisible(collected.mediaScope);
      assert.equal(visible.unavailable, true);
      assert.equal(visible.crop, null);
      assert.deepEqual(visible.media, []);
      assert.equal(inspectVisible().unavailable, true);
    });
  }
});

test("selected words remain the only submitted text, without description links", async () => {
  const selection = "EX-selected is being studied for a different synthetic condition.";
  await onPage(watch, address, () => {
    const collected = collectFromPage();
    const request = composeRequest(collected, address, shared);
    assert.equal(request.text, selection);
    assert.deepEqual(request.links, []);
    assert.equal(inspectVisible(collected.mediaScope).selectionOnly, true);
  }, selection);
});

test("YouTube's public search box behaves like a search input; comment drafts and passwords still prevent capture", async () => {
  const search = '<input type="text" name="search_query" role="combobox" value="synthetic research" data-box="20,0,200,20" />';
  await onPage(watch + search, address, document => {
    const scope = collectFromPage().mediaScope;
    assert.equal(inspectVisible(scope).sensitive, false);
    document.querySelector('input').setAttribute("name", "comment");
    assert.equal(inspectVisible(scope).sensitive, true);
    document.querySelector('input').setAttribute("name", "search_query");
    document.querySelector('input').setAttribute("type", "password");
    assert.equal(inspectVisible(scope).sensitive, true);
  });
});

test("an ad or offscreen player cannot fall back to an unrelated full-page screenshot", async () => {
  for (const html of [watch.replace('id="movie_player"', 'id="movie_player" class="ad-showing"'), watch.replace('data-box="20,20,640,360"', 'data-box="20,900,640,360"')]) {
    await onPage(html, address, () => {
      const collected = collectFromPage();
      assert.equal(inspectVisible(collected.mediaScope).unavailable, true);
      assert.equal(inspectVisible(collected.mediaScope).crop, null);
    });
  }
});

test("visible end-screen and recommendation overlays refuse capture; a finished video is ineligible", async () => {
  for (const classes of ["ytp-endscreen-content", "ytp-ce-element-show", "ytp-pause-overlay"]) {
    await onPage(watch.replace('<div id="movie_player">', `<div id="movie_player"><div class="${classes}" data-box="20,20,640,360"><img data-box="20,20,200,150" /></div>`), address, document => {
      const scope = collectFromPage().mediaScope;
      assert.equal(inspectVisible(scope).unavailable, true);
      document.querySelector(`.${classes}`).hidden = true;
      assert.equal(inspectVisible(scope).unavailable, false);
      Object.defineProperty(document.querySelector("#movie_player video"), "ended", { value: true });
      assert.equal(inspectVisible(scope).unavailable, true);
    });
  }
});

test("YouTube capture rechecks video scope and refuses an ad that starts during capture", async () => {
  await onPage(watch, address, async document => {
    const tab = { id: 7, windowId: 3, url: address };
    let captures = 0, encodes = 0;
    const api = { tabs: { query: async () => [tab], captureVisibleTab: async () => {
      captures++;
      document.querySelector("#movie_player").classList.add("ad-showing");
      return "data:image/jpeg;base64,fixture";
    } }, scripting: { executeScript: async ({ func, args = [] }) => [{ result: func(...args) }] } };
    await assert.rejects(capturePage(api, tab, null, async () => { encodes++; }), error => error.code === "capture_unavailable");
    assert.equal(captures, 1);
    assert.equal(encodes, 0);
  });
});

test("YouTube aliases share a video key and a clean source URL without playback or sharing context", () => {
  const aliases = [address, `${address}&t=30&list=private-playlist&index=2`, `https://youtu.be/${video}?si=sharing-token`,
    `https://m.youtube.com/watch?v=${video}&feature=share`, `https://www.youtube.com/shorts/${video}?app=desktop`,
    `https://www.youtube.com/live/${video}`, `https://www.youtube.com/embed/${video}`];
  for (const url of aliases) {
    assert.equal(articleKey(url), `youtube.com/watch?v=${video}`);
    assert.equal(publicPageUrl(url), address);
    assert.equal(readAddress(url).platform, "YouTube");
    assert.equal(readAddress(url).readable, false);
  }
  assert.notEqual(articleKey(address), articleKey(`https://youtu.be/${other}`));
  for (const url of [`${address}&token=private`, `${address}&v=${other}`, "https://www.youtube.com/watch?v=bad", `https://www.youtube.com.evil.example/watch?v=${video}`, `https://user:password@youtube.com/watch?v=${video}`]) {
    assert.equal(publicPageUrl(url), null);
  }
});
