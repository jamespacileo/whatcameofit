// A file of rows (openspec landing-rows-on-demand): one component drawn on its own, as
// the home page draws it, and served as text. The home page already carries each
// component's styles and script, so the file holds neither: a script tag the renderer
// leaves behind names a source file, not a built one, and is taken out.
import { experimental_AstroContainer as AstroContainer } from "astro/container";

type Component = Parameters<AstroContainer["renderToString"]>[0];

export async function rowFile(component: Component, props: Record<string, unknown>): Promise<Response> {
  const container = await AstroContainer.create();
  const rows = await container.renderToString(component, { props });
  return new Response(rows.replace(/<script\b[^>]*>[\s\S]*?<\/script>/g, ""), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
