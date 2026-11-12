#!/bin/sh
# Wraps the built extension in the app Safari requires, then compiles that app
# without signing to prove it builds. Run `make extension-safari` from the repository root.
#
# Apple's converter writes an Xcode project to extension/safari, which is not checked in.
# Compiled output goes to the machine's build cache, not the repository.
# The converter adds ".Extension" to the app's bundle identifier. The display name
# and release version come from the built extension's manifest.
set -eu

app_name="WhatCameOfIt"
bundle_id="${SAFARI_BUNDLE_ID:-com.whatcameofit.WhatCameOfIt}"
if command -v devcache >/dev/null 2>&1; then
  build_dir="$(devcache path thenwhat)/safari"
else
  build_dir="${TMPDIR:-/tmp}/thenwhat-safari-build"
fi

xcrun safari-web-extension-converter extension/dist \
  --project-location extension/safari \
  --app-name "$app_name" \
  --bundle-identifier "$bundle_id" \
  --macos-only --swift --copy-resources --no-open --no-prompt --force

# Xcode's converter defaults the containing app to its current SDK version and
# gives it version 1.0. Persist our settings so opening the generated project in
# Xcode produces the same app as this script. Support both Xcode project formats.
node --input-type=module - "extension/safari/$app_name/$app_name.xcodeproj" <<'NODE'
import fs from "node:fs";
import path from "node:path";

const manifest = JSON.parse(fs.readFileSync("extension/dist/manifest.json", "utf8"));
if (typeof manifest.name !== "string" || !manifest.name.trim() ||
    !/^\d+\.\d+\.\d+(?:\.\d+)?$/.test(manifest.version)) {
  throw new Error("The built extension needs a name and numeric release version.");
}
const project = process.argv[2];
const modern = path.join(project, "project.xcproj");
const modernFormat = fs.existsSync(modern);
const file = modernFormat ? modern : path.join(project, "project.pbxproj");
let source = fs.readFileSync(file, "utf8");
const settings = {
  INFOPLIST_KEY_CFBundleDisplayName: manifest.name,
  MARKETING_VERSION: manifest.version,
  MACOSX_DEPLOYMENT_TARGET: "12.0",
};
for (const [key, value] of Object.entries(settings)) {
  const pattern = modernFormat
    ? new RegExp(`("${key}"\\s*:\\s*)"(?:\\\\.|[^"\\\\])*"`, "g")
    : new RegExp(`(\\b${key}\\s*=\\s*)(?:"(?:\\\\.|[^"\\\\])*"|[^;\\r\\n]*);`, "g");
  let replacements = 0;
  source = source.replace(pattern, (_match, prefix) => {
    replacements += 1;
    return prefix + JSON.stringify(value) + (modernFormat ? "" : ";");
  });
  if (replacements === 0) throw new Error(`Generated project has no ${key} setting.`);
}
fs.writeFileSync(file, source);
NODE

xcodebuild -project "extension/safari/$app_name/$app_name.xcodeproj" \
  -scheme "$app_name" -configuration Release -destination 'generic/platform=macOS' \
  -derivedDataPath "$build_dir" \
  CODE_SIGNING_ALLOWED=NO build

echo "Built without signing. App: $build_dir/Build/Products/Release/$app_name.app"
