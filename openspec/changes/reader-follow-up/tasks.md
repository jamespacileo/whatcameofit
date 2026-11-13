# Tasks

Accepted by the operator on 2026-11-13.

## 1. Site

- [x] 1.1 Write the calendar-file builder as a pure function with tests; verify each of the four choices gives one valid event linking to the claim page
- [x] 1.2 Add the reminder control to the claim page following DESIGN.md; verify the promise choice is absent on a claim with no dated promise and that saving sends no request
- [ ] 1.3 Publish the status changes feed and the per-claim feed; verify entries carry both labels and the event date, and that the verdict-wording check covers them
- [x] 1.4 Say on the privacy page what a calendar reminder does; verify the page builds

## 2. Extension, in the popup (no new permission)

- [x] 2.1 Write follow and recently-checked storage as pure functions with tests; verify changed, unchanged, removed-claim, cap-of-ten and one-entry-per-page cases
- [x] 2.2 Keep both lists from the popup's controller; verify a check is kept, the lists open and clear without a request, and a change is shown once
- [x] 2.3 Build the popup views (follow control, recently checked, one check's candidates, following, changed marker) following DESIGN.md; verify every state on the states page at the popup's width
- [x] 2.4 Say on the privacy page what the extension keeps; verify the page builds
- [x] 2.5 Confirm nothing new leaves the browser; verify the controller test sees only the lookup file requested

## 3. Extension, in the background (new permissions: `alarms`, `notifications`)

- [ ] 3.1 Add the permissions and a background handler that refreshes the lookup file; verify one notification per changed claim
- [ ] 3.2 Reminders in the extension: the four choices, kept in the browser, one notification when due; verify due, removed and Safari-on-open cases
- [ ] 3.3 Popup controls for reminders; verify on the states page

## 4. In a real browser

- [ ] 4.1 Load `extension/dist` in Chrome; verify a checked page appears in the list, follow and stop, and the changed marker with a local lookup file
- [ ] 4.2 The operator rebuilds the Safari project and does the same
