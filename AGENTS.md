# AGENTS.md

## Before Coding
- Read `PRD.md`.
- Read `ARCHITECTURE_ESSENTIALS.md`.
- Consult `ARCHITECTURE.md` for deeper context.
- Read `DESIGN.md` before changing user-facing UI or demo copy.
- Read `SECURITY_CHECKLIST.md`, `COST_CONTROL.md`, and `EVALUATION_AND_GOVERNANCE.md` before security, AI, or deployment work.
- Inspect existing code before modifying anything.
- Do not introduce new architecture without checking existing decisions.

## Coding Principles
- Prefer simple implementations.
- Avoid unnecessary abstractions.
- Avoid premature optimization.
- Follow the existing project structure and conventions.
- Keep functions and modules focused.
- Use clear names.
- Add types where appropriate.
- Do not duplicate logic.
- Avoid giant files.
- Keep configuration separate from business logic.
- Never hardcode secrets.

## Change Discipline
Before implementing a substantial feature:
1. Understand the relevant existing code.
2. Identify which files need modification.
3. Verify how the change fits the architecture.
4. Implement the smallest complete change.
5. Add or update tests.
6. Run the appropriate tests.
7. Fix failures before considering the task complete.

## Architecture Discipline
Do not:
- Change the chosen database casually.
- Introduce another framework without justification.
- Add unnecessary dependencies.
- Create parallel abstractions for something that already exists.
- Bypass established service boundaries.
- Put business logic in presentation/UI layers.

If an architectural change is genuinely necessary, update the architecture documentation.

## Testing
For new functionality:
- Test normal behavior.
- Test important edge cases.
- Test expected failure behavior.
- Mock external systems where appropriate.
- Prefer deterministic tests.

## AI-Specific Rules
- Keep prompts versionable and easy to locate.
- Prefer structured model outputs.
- Validate model outputs before using them.
- Treat model output as untrusted input.
- Never assume an LLM response is factually correct.
- Add graceful fallbacks for model/API failures.
- Avoid unnecessary LLM calls.
- Log relevant metadata without exposing sensitive information.

## Documentation
Update documentation when implementation changes important behavior or architecture.

## Demo Discipline
- Keep `DEMO_GUIDE.md` and `PORTFOLIO_BRIEF.md` aligned with shipped behavior.
- Prefer safe sample data from `examples/` during demos.
- Never use real personal resume data in tests, analytics fixtures, or screenshots.
