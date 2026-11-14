// What a phone or a launcher needs to show the site as its own: the name from the
// brand config and the icons drawn from the one mark (scripts/brand-icons.mjs).
import type { APIRoute } from "astro";
import { SITE } from "../../site.config.mjs";
import { THEME_COLOR, brandAsset } from "../lib/brand";

export const GET: APIRoute = () =>
  new Response(
    JSON.stringify(
      {
        name: SITE.name,
        short_name: SITE.name,
        description: SITE.tagline,
        start_url: "/",
        display: "browser",
        background_color: "#ffffff",
        theme_color: THEME_COLOR,
        icons: [
          { src: brandAsset("/icon-192.png"), sizes: "192x192", type: "image/png" },
          { src: brandAsset("/icon-512.png"), sizes: "512x512", type: "image/png" },
          { src: brandAsset("/icon-maskable-512.png"), sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      null,
      2,
    ),
    { headers: { "Content-Type": "application/manifest+json; charset=utf-8" } },
  );
