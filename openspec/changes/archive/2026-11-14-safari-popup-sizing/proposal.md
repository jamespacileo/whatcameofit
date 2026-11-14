# Restore Safari popup sizing

## Why
The installed 0.6.0 popup can appear as a blank, narrow glass strip. Its accessibility content still contains the answer, including on a reviewed page without an AI request. A new viewport-relative body cap allows a 100px starting viewport to measure only 100px of intrinsic content, instead of the intended 360px.

## Changes
Restore the fixed body width used before 0.6.0, without a viewport-relative cap. Add a development regression page that starts the actual popup renderer and stylesheet at 100px and 360px and checks the measured content width before and after host resizing. Publish as 0.6.1 only after native Safari verification. No lookup, consent, cache or budget changes.
