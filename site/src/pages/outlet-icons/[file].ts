// One file per outlet icon in the export, written at build time.
import type { APIRoute } from "astro";
import { outletIcons, type OutletIcon } from "../../lib/outlets";

export function getStaticPaths() {
  return outletIcons.map((icon) => ({ params: { file: icon.file }, props: { icon } }));
}

export const GET: APIRoute = ({ props }) => {
  const { icon } = props as { icon: OutletIcon };
  return new Response(new Uint8Array(icon.bytes), { headers: { "Content-Type": icon.mediaType } });
};
