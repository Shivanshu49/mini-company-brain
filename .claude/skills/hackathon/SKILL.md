---
name: hackathon
description: Use for ALL work in the paytm-hackathon project — planning, building, debugging, reviewing. Sets hackathon mode: ship a working demo fast with tight scope, no TDD, reasonable (not extreme) scalability. Overrides superpowers process skills like test-driven-development.
---

# Hackathon Mode

We are in a hackathon. **Finishing beats perfection.** A working, demoable product at the deadline is the only thing that counts. Every decision should be judged by: *does this get us to a working demo faster?*

## Hard rules

1. **No TDD.** Do NOT use `superpowers:test-driven-development`. Do not write tests first. Do not block progress on test coverage. Write a test only when it's the fastest way to verify something tricky (e.g. a payment calculation) — otherwise verify by running the app.
2. **Skip heavyweight process.** Don't run long brainstorming loops, multi-stage plan documents, git worktrees, or formal code-review cycles unless the user explicitly asks. A short bullet plan in chat is enough.
3. **Tight scope, always.** Before building anything, state the smallest version that demos the idea. Push back on scope creep. If a feature isn't in the demo path, it's a "later" item — list it, don't build it.
4. **Scalable within reason.** Sensible structure (clean modules, env-based config, a real DB if data matters, stateless API where it's free) — but no microservices, message queues, Kubernetes, sharding, caching layers, or custom infra. Design for hundreds/thousands of users, not millions.
5. **No long-term maintenance burden.** Don't build admin panels, migration frameworks, plugin systems, abstraction layers "for later", or anything we'd have to babysit. We won't be maintaining this.

## How to build

- **Boring, familiar tech.** Use what the team already knows and what has the best docs. No new frameworks for fun.
- **Managed services over self-hosting.** Hosted DB (Supabase/Firebase/Neon/SQLite file), hosted auth, one-click deploys (Vercel/Render/Railway). Use SDKs and APIs instead of reimplementing.
- **Libraries over custom code.** If a well-known package does it, use it. UI kits (shadcn, Tailwind, MUI) over hand-rolled components.
- **Vertical slices.** Get one end-to-end flow working (UI → API → DB → back) before widening. Always keep the app in a runnable state.
- **Mock what isn't core.** Fake external integrations, seed data, hardcode config, stub non-demo features. Real payment rails/KYC/etc. can be sandboxed or mocked if the real one costs time. Clearly mark mocks with `// MOCK:` comments.
- **Happy path first.** Handle errors that would crash the demo; ignore exotic edge cases. A try/catch with a friendly message beats a full error taxonomy.
- **Minimal files, minimal layers.** Prefer fewer files and direct code over repositories/services/factories. Duplication is fine if it saves time.
- **Verify by running it.** After each change, run the app / hit the endpoint / check the UI. That's the test.

## Time management

- Timebox anything uncertain. If an approach isn't working after a couple of attempts, propose a simpler fallback instead of digging deeper.
- Flag risks early: "this integration could eat 2 hours — want me to mock it?"
- Prioritize in this order: **working core flow → demo polish (UI, sample data) → nice-to-haves.**
- Don't refactor working code unless it blocks the next feature.

## Demo readiness (keep in mind throughout)

- The demo path must be rock solid; everything else can be rough.
- Seed realistic sample data so the demo looks alive.
- Make the UI look decent — judges see the UI, not the code.
- Keep a short README: what it does, how to run it, tech stack, and what's mocked.
- Deployment/run steps should be one command where possible.

## When responding

- Be concise. Propose, then do. Don't list five options — recommend one.
- When a request is ambiguous, pick the simplest reasonable interpretation and mention it, rather than stopping to ask.
- If the user asks for something that blows scope or adds long-term complexity, say so in one line and offer the lean alternative.
