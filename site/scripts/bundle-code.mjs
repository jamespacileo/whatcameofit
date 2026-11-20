// The code the site makes from a bundle's schemas (openspec pairs-site, decision 1 and task
// 2.2): one compiled validator a page model, written as plain JavaScript with no runtime
// `eval`, so the Worker can check a page file it reads from D1; and the TypeScript types of
// each page model. The bundle's schemas are the only definition; nothing here is kept by hand.
//
//   node scripts/bundle-code.mjs <bundle folder> <out folder>
//
// writes <out>/validators.mjs (one export a page model: `validatePairPage`, ...) and
// <out>/types/<Model>.d.ts. A build that reads a bundle writes them to .bundle-code/.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020.js";
import standaloneCode from "ajv/dist/standalone/index.js";
import { compile } from "json-schema-to-typescript";

// The formats the lab's schemas name, as patterns, so the compiled code carries them itself.
// A time is read with or without an offset: the lab writes `PairOrigin.created_at` with none
// (task 2.5), as `readBundle` also allows. Both allowances go when tests/bundle-strict.test.mjs
// finds no failing file.
const FORMATS = {
  date: /^\d{4}-\d{2}-\d{2}$/,
  "date-time": /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$/i,
};

/** The page models a bundle has schemas for, each with its schema. */
export function bundleSchemas(bundle) {
  const folder = path.join(bundle, "schemas");
  if (!fs.existsSync(folder)) throw new Error(`${bundle} holds no schemas/ folder: it is not a bundle of page files.`);
  return fs
    .readdirSync(folder)
    .filter((name) => name.endsWith(".json"))
    .sort()
    .map((name) => ({ model: name.slice(0, -".json".length), schema: JSON.parse(fs.readFileSync(path.join(folder, name), "utf8")) }));
}

/** The compiled validators of a bundle's page models, as the text of one ES module. */
export function validatorsModule(bundle) {
  const ajv = new Ajv2020({ code: { source: true, esm: true }, allErrors: false, strict: false });
  for (const [name, pattern] of Object.entries(FORMATS)) ajv.addFormat(name, pattern);
  const exports = {};
  for (const { model, schema } of bundleSchemas(bundle)) {
    ajv.addSchema({ ...schema, $id: model });
    exports[`validate${model}`] = model;
  }
  return `// Written by scripts/bundle-code.mjs from the bundle's schemas. Do not edit.\n${standaloneCode(ajv, exports)}`;
}

/** Write the validators and the types of a bundle's page models into a folder. */
export async function writeBundleCode(bundle, out) {
  fs.mkdirSync(path.join(out, "types"), { recursive: true });
  fs.writeFileSync(path.join(out, "validators.mjs"), validatorsModule(bundle));
  for (const { model, schema } of bundleSchemas(bundle)) {
    const types = await compile(schema, model, {
      bannerComment: "// Written by scripts/bundle-code.mjs from the bundle's schemas. Do not edit.",
      additionalProperties: false,
      format: false,
    });
    fs.writeFileSync(path.join(out, "types", `${model}.d.ts`), types);
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [bundle, out] = process.argv.slice(2);
  if (!bundle || !out) {
    console.error("Usage: node scripts/bundle-code.mjs <bundle folder> <out folder>");
    process.exit(2);
  }
  await writeBundleCode(path.resolve(bundle), path.resolve(out));
  console.log(`Wrote the validators and types of ${bundleSchemas(path.resolve(bundle)).length} page models to ${out}.`);
}
