// Lucide 1.72.0 icon nodes, copied from the site's @lucide/astro package.
// See lucide-LICENSE.txt. Adjacent labels always carry each icon's meaning.
const nodes = {
  "external": [["path", { "d": "M15 3h6v6" }], ["path", { "d": "M10 14 21 3" }], ["path", { "d": "M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" }]],
  "bell": [["path", { "d": "M10.268 21a2 2 0 0 0 3.464 0" }], ["path", { "d": "M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326" }]],
  "check": [["path", { "d": "M20 6 9 17l-5-5" }]],
  "search": [
    [
      "path",
      {
        "d": "m21 21-4.34-4.34"
      }
    ],
    [
      "circle",
      {
        "cx": "11",
        "cy": "11",
        "r": "8"
      }
    ]
  ],
  "target": [
    [
      "circle",
      {
        "cx": "12",
        "cy": "12",
        "r": "10"
      }
    ],
    [
      "line",
      {
        "x1": "22",
        "x2": "18",
        "y1": "12",
        "y2": "12"
      }
    ],
    [
      "line",
      {
        "x1": "6",
        "x2": "2",
        "y1": "12",
        "y2": "12"
      }
    ],
    [
      "line",
      {
        "x1": "12",
        "x2": "12",
        "y1": "6",
        "y2": "2"
      }
    ],
    [
      "line",
      {
        "x1": "12",
        "x2": "12",
        "y1": "22",
        "y2": "18"
      }
    ]
  ],
  "phase": [
    [
      "path",
      {
        "d": "M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2"
      }
    ],
    [
      "path",
      {
        "d": "M6.453 15h11.094"
      }
    ],
    [
      "path",
      {
        "d": "M8.5 2h7"
      }
    ]
  ],
  "people": [
    [
      "path",
      {
        "d": "M18 21a8 8 0 0 0-16 0"
      }
    ],
    [
      "circle",
      {
        "cx": "10",
        "cy": "8",
        "r": "5"
      }
    ],
    [
      "path",
      {
        "d": "M22 20c0-3.37-2-6.5-4-8a5 5 0 0 0-.45-8.3"
      }
    ]
  ],
  "info": [
    [
      "circle",
      {
        "cx": "12",
        "cy": "12",
        "r": "10"
      }
    ],
    [
      "path",
      {
        "d": "M12 16v-4"
      }
    ],
    [
      "path",
      {
        "d": "M12 8h.01"
      }
    ]
  ],
  "chevron": [
    [
      "path",
      {
        "d": "m6 9 6 6 6-6"
      }
    ]
  ],
  "refresh": [
    [
      "path",
      {
        "d": "M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"
      }
    ],
    [
      "path",
      {
        "d": "M21 3v5h-5"
      }
    ]
  ],
  "image": [
    [
      "rect",
      {
        "width": "18",
        "height": "18",
        "x": "3",
        "y": "3",
        "rx": "2",
        "ry": "2"
      }
    ],
    [
      "circle",
      {
        "cx": "9",
        "cy": "9",
        "r": "2"
      }
    ],
    [
      "path",
      {
        "d": "m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"
      }
    ]
  ],
  "settings": [
    [
      "path",
      {
        "d": "M10 5H3"
      }
    ],
    [
      "path",
      {
        "d": "M12 19H3"
      }
    ],
    [
      "path",
      {
        "d": "M14 3v4"
      }
    ],
    [
      "path",
      {
        "d": "M16 17v4"
      }
    ],
    [
      "path",
      {
        "d": "M21 12h-9"
      }
    ],
    [
      "path",
      {
        "d": "M21 19h-5"
      }
    ],
    [
      "path",
      {
        "d": "M21 5h-7"
      }
    ],
    [
      "path",
      {
        "d": "M8 10v4"
      }
    ],
    [
      "path",
      {
        "d": "M8 12H3"
      }
    ]
  ],
  "clock": [
    [
      "circle",
      {
        "cx": "12",
        "cy": "12",
        "r": "10"
      }
    ],
    [
      "path",
      {
        "d": "M12 6v6l4 2"
      }
    ]
  ],
  "book": [
    [
      "path",
      {
        "d": "M12 5v16"
      }
    ],
    [
      "path",
      {
        "d": "M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z"
      }
    ]
  ]
};

/**
 * The mark for a wait: the glass over the capsule, as on the site, with the capsule
 * held inside the lens so that it can pass beneath the glass while the reader waits.
 * The drawing is the site's public/mark-symbol.svg.
 */
export function waitMark() {
  const ns = "http://www.w3.org/2000/svg";
  const make = (tag, attributes, children = []) => {
    const node = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    node.append(...children);
    return node;
  };
  return make("svg", { viewBox: "8 8 48 48", "aria-hidden": "true", focusable: "false", class: "wait-mark" }, [
    make("clipPath", { id: "wait-lens" }, [make("circle", { cx: "30.5", cy: "30.5", r: "16.5" })]),
    make("path", { fill: "#16477d", "fill-rule": "evenodd", d: "M42.38 49.02A22 22 0 1 1 49.02 42.38A1.2 1.2 0 0 0 49.18 43.88L54.36 49.06A3.75 3.75 0 0 1 49.06 54.36L43.88 49.18A1.2 1.2 0 0 0 42.38 49.02ZM47 30.5A16.5 16.5 0 1 0 14 30.5A16.5 16.5 0 1 0 47 30.5Z" }),
    make("g", { "clip-path": "url(#wait-lens)" }, [
      make("g", { class: "capsule" }, [
        make("path", { d: "M29.7 23.75h-6.2a6.75 6.75 0 0 0 0 13.5h6.2z", fill: "#f28a62" }),
        make("path", { d: "M31.3 23.75h6.2a6.75 6.75 0 0 1 0 13.5h-6.2z", fill: "#1687da" }),
      ]),
    ]),
  ]);
}

export function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  for (const [key, value] of Object.entries({ viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "1.8", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true", focusable: "false", class: "icon" })) svg.setAttribute(key, value);
  for (const [tag, attributes] of nodes[name]) {
    const child = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attributes)) child.setAttribute(key, value);
    svg.append(child);
  }
  return svg;
}
