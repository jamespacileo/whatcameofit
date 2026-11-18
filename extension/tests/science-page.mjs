export const SCIENCE = "https://www.sciencealert.com/scientists-identified-a-biological-signature-of-tinnitus-and-its-in-your-blood";
export const PARAGRAPHS = [
  "Researchers examining blood samples from people with persistent ringing in the ears report a set of molecular markers that appear far more often in those with the condition than in people without it.",
  "The team compared hundreds of volunteers, some with chronic tinnitus and some without, and measured a panel of proteins and small molecules associated with inflammation and nerve signalling.",
  "Several of these markers differed consistently between the groups, and the differences were larger in volunteers who described their symptoms as more severe or longer lasting.",
  "The authors caution that the work identifies a possible biological signature rather than a cause, and that a blood test for clinical use would need validation in larger and more varied groups.",
  "They also note that hearing loss, stress and sleep problems often accompany the condition and may influence the same markers, which makes untangling cause and effect difficult.",
  "Independent researchers not involved in the study said the findings were interesting because the condition currently has no objective measure, and diagnosis relies on what patients report.",
  "The study was published in a peer-reviewed journal, and the researchers say their next step is to follow volunteers over time to see whether the markers change as symptoms change.",
].map((words) => `<p>${words}</p>`).join("\n");
export const STRUCTURED = JSON.stringify({ "@context": "https://schema.org", "@graph": [
  { "@type": "WebPage", "@id": `${SCIENCE}#webpage` },
  { "@type": "ImageObject", "@id": `${SCIENCE}#primaryimage`, url: "https://www.sciencealert.com/images/ear.jpg" },
  { "@type": "NewsArticle", headline: "Scientists identified a biological signature of tinnitus, and it's in your blood", datePublished: "2026-11-10" },
] });
export const sciencePage = (more = {}) => ({
  address: SCIENCE,
  title: "Scientists identified a biological signature of tinnitus, and it's in your blood : ScienceAlert",
  selection: "",
  head: `<head><title>Tinnitus signature</title><meta property="og:type" content="article"><meta property="og:title" content="Scientists identified a biological signature of tinnitus"><script type="application/ld+json">${STRUCTURED}</script></head>`,
  focusHtml: `<article><h1>Scientists identified a biological signature of tinnitus, and it's in your blood</h1><figure><img src="https://www.sciencealert.com/images/ear.jpg" alt="An ear"><figcaption>(Example Photo Agency)</figcaption></figure>${PARAGRAPHS}<p>Read the paper: <a href="https://doi.org/10.1000/example.tinnitus">the study</a>.</p></article>`,
  focusText: "",
  links: [{ href: "https://doi.org/10.1000/example.tinnitus", text: "the study" }],
  postTitle: null,
  contentHref: null,
  structured: [STRUCTURED],
  ...more,
});
export const heroPhoto = [{ left: 0, top: 120, width: 800, height: 450, kind: "img", identity: "https://www.sciencealert.com/images/ear.jpg", time: null }];
