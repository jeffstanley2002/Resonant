# Resonant UX Contract

## Scope And Sources

This contract covers the public account entry flow and authenticated career workspace. Business rules come from `PRD.md`, `ARCHITECTURE_ESSENTIALS.md`, `SECURITY_CHECKLIST.md`, and the API schemas in `apps/api/app/schemas.py`.

## Canonical Owners

- Visual tokens and responsive behavior: `DESIGN.md` → `apps/web/app/globals.css`.
- Session and Supabase state: `apps/web/app/page.tsx` and `apps/web/lib/supabase.ts`.
- Authentication form and validation: `apps/web/app/components/auth-dialog.tsx`.
- Search setup, tabs, result lists, and delete dialog: `apps/web/app/components/workspace.tsx`.
- API request and response mapping: `apps/web/lib/api.ts`.

## Canonical UI Map

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Select/Listbox | Native HTML select | `DESIGN.md`, this contract | Native for the four fixed recommendation limits | Keyboard and Playwright E2E |
| Form | Auth dialog and workspace search form | This contract | Sign in, sign up, job search | Validation and Playwright E2E |
| Scrollbar | Global application stylesheet | `DESIGN.md` | Stable gutter on horizontal tabs | Computed browser and responsive review |
| CRUD | Workspace actions and API client | API schemas, this contract | Save role, rate run, delete application data | Full-flow and failure-path E2E |

## Flow Ledger

| Operation | Trigger | Pending | Success | Failure recovery | Focus outcome | Source |
|---|---|---|---|---|---|---|
| Sign in | Log in form | Fixed-size busy button | Authenticated workspace | Generic inline credentials error, values retained | Email on open; workspace after session | `PRD.md`, Supabase Auth |
| Sign up | Sign up form with confirmation | Fixed-size busy button | Workspace or email-confirmation notice | Associated field or provider error | First invalid field | `PRD.md`, Supabase Auth |
| Resume upload | Native file picker | Upload button shows progress | AI-verified facts update | Parsed-but-failed AI state; retry through picker | Picker remains available | `PRD.md`, `/resumes/analyze` |
| Find matches | Search form | Submit disabled with loader | Matches tab with result count | Failed/partial stage summary; form values retained | Results live region | `PRD.md`, `/agent/matches` |
| Save role | Save role button | Pessimistic request | Button and Saved tab update | Inline error, retry on same role | Trigger retained | `PRD.md`, `/saved-jobs` |
| Rate run | Named usefulness button | Pessimistic request | Selected rating and status | Inline error, rating may be retried | Rating button retained | `PRD.md`, `/feedback` |
| Delete application data | Danger-zone link then dialog | Final action disabled with loader | Data views reset and deletion status announced | Dialog remains available and error is shown | Safe cancel action initially focused | `SECURITY_CHECKLIST.md`, `/account/data` |

## Navigation And Lists

Signed-out visitors see only the landing page and account entry. Signed-in users see the workspace. Tabs are transient view state because they contain sensitive, session-bound resume analysis and should not be shareable through URLs. Arrow keys, Home, and End move between tabs. Match results show eight initially and use an explicit “Show more recommendations” action until all returned roles are visible.

## Async And Recovery

Requests are pessimistic. Duplicate form submissions are disabled while pending. Model failure produces an explicit failed or partial stage and never synthetic AI content. Provider-to-provider failover is allowed; curated demo jobs require explicit configuration and remain labeled. Session expiry returns the user to the landing experience through Supabase auth-state changes. No resume text, password, token, or secret is placed in URLs, analytics, status messages, or persistent client storage.

## Accessibility

Target WCAG 2.2 AA. Native fields have labels, validation errors are associated and focusable, visible focus is required, reduced motion is respected, and native dialogs provide modal keyboard behavior. Mobile uses document scrolling with no clipped application regions.

## Verification

Required checks are frontend lint/typecheck/build, API tests, Playwright E2E, premium strict static audit, dark-theme color scan, and browser coverage for landing, auth modes, empty, loading, success, tabs, save, feedback, deletion, narrow viewport, keyboard, and reduced motion.
