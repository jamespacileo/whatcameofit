# Tasks

Accepted by the operator on 2026-11-13.

## 1. Site

- [x] 1.1 Write the calendar-file builder as a pure function with tests; verify each of the four choices gives one valid event linking to the claim page
- [x] 1.2 Add the reminder control to the claim page following DESIGN.md; verify the promise choice is absent on a claim with no dated promise and that saving sends no request
- [ ] 1.3 Publish the status changes feed and the per-claim feed; verify entries carry both labels and the event date, and that the verdict-wording check covers them
- [ ] 1.4 Add the extension's kept data to the privacy page once the extension keeps it (the calendar reminder is described there as of 2026-11-13); verify the page builds

## 2. Extension

- [ ] 2.1 Write follow, reminder and recently-checked storage as pure functions with tests; verify changed, unchanged, removed-claim, cap-of-ten and clear cases
- [ ] 2.2 Add the `alarms` and `notifications` permissions and the background handler; verify one notification per due reminder and per changed claim
- [ ] 2.3 Build the popup views (follow control, reminder choices, recently checked, changed marker) following DESIGN.md; verify every state on the states page at the popup's width
- [ ] 2.4 Confirm nothing new leaves the browser; verify the network test shows only the lookup file and the existing lookup service calls

## 3. In a real browser

- [ ] 3.1 Load `extension/dist` in Chrome; verify a reminder set one minute ahead fires and opens the claim page
- [ ] 3.2 Change a followed claim's status in a local lookup file; verify the notification and the popup marker
- [ ] 3.3 The operator rebuilds the Safari project; verify reminders are shown when the popup opens
