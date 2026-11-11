#!/bin/sh
# Wraps the built extension in the app Safari requires, then compiles that app
# without signing to prove it builds. Run `make extension-safari` from the repository root.
#
# Apple's converter writes an Xcode project to extension/safari, which is not checked in.
# Compiled output goes to the machine's build cache, not the repository.
# The bundle identifier is a placeholder: set SAFARI_BUNDLE_ID before distributing.
# Its last part must be the app name; the converter adds ".Extension" for the extension,
# which must begin with the app's identifier.
set -eu

bundle_id="${SAFARI_BUNDLE_ID:-local.thenwhat.thenwhat}"
if command -v devcache >/dev/null 2>&1; then
  build_dir="$(devcache path thenwhat)/safari"
else
  build_dir="${TMPDIR:-/tmp}/thenwhat-safari-build"
fi

xcrun safari-web-extension-converter extension/dist \
  --project-location extension/safari \
  --app-name thenwhat \
  --bundle-identifier "$bundle_id" \
  --macos-only --swift --copy-resources --no-open --no-prompt --force

xcodebuild -project extension/safari/thenwhat/thenwhat.xcodeproj \
  -scheme thenwhat -configuration Debug \
  -derivedDataPath "$build_dir" \
  CODE_SIGNING_ALLOWED=NO build

echo "Built without signing. App: $build_dir/Build/Products/Debug/thenwhat.app"
