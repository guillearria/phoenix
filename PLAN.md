# The plan

Started 2026-10-20. Steps 1, 2 and the first night shift are running; the rest is a plan.

## The idea

The projects in the README already have most parts of a living system. They run on schedules, check their own output, publish, and keep records. Four things are missing: ears, one brain across projects, more than one AI model family, and permission to act at night inside safe limits. Phoenix adds those four and connects the rest into one nightly loop.

## What already exists

| Part | Job | Already built |
|---|---|---|
| Eyes | Notice what changed | A daily dashboard, alarms when a job goes quiet, safety checks |
| Brain | Choose one move | A nightly editor that decides, then obeys rules written in code |
| Hands | Do the work | AI agent sessions inside each project |
| Immune system | Block bad output | A banned-words filter, a fact checker, a no-selling check, a design standard |
| Memory | Remember what worked | Logs, findings and ledgers, all in git |
| Heartbeat | Run on time | Schedules, a weekly run budget, alarms |
| Voice | Reach people | Three live websites and a daily message |
| Pruning | Retire what fails | Set the pass mark first, judge once, accept the result |

## What is missing

1. **Ears.** Nothing reads what people do. In the last two weeks the three repos had 11 views on GitHub and no stars. One site's visitor stats are switched on but never read.
2. **One brain.** Each project decides alone, or waits for a person.
3. **More than one model family.** Every AI call today goes to one company's models.
4. **Permission to act at night.** Work only happens when someone opens a session.

## The nightly loop

| Step | What happens | Built from |
|---|---|---|
| Listen | A script records visits, stars, issues and comments into a public ledger. No AI. | The daily dashboard |
| Choose | One AI run reads the ledger and open issues, then writes tonight's work as labeled issues. | The nightly editor's decide-then-guard pattern |
| Build | Anthropic's official GitHub Action works each labeled issue and opens a pull request. | Agent sessions inside each project |
| Check | Tests, the banned-words filter, and a review by a model from a different company. | The existing gates |
| Ship or hold | Safe changes merge. Everything else waits for a person. | The fact checker's auto-merge rule |
| Report | One morning message: what changed, what people did, what is waiting. | The daily message rules |
| Learn and prune | Results go into the ledger. A project or idea that misses its pass mark is retired. | The pre-registered pass mark |

## Models: best value per job

[Arena](https://arena.ai/leaderboard) ranks more than 360 models from millions of blind human votes, separately for each kind of job, and lists their prices. [OpenRouter](https://openrouter.ai) calls almost any of those models with one key. So Arena picks and OpenRouter calls. Rankings read on 2026-10-20:

| Job | Best | Best value |
|---|---|---|
| Build and fix code as an agent | Claude Opus 5.5, #1 on Agent | GPT-6.1 Sol, #4 at about 1/8 the cost per task |
| Web pages and interfaces | Claude Opus 5.5, #1 on WebDev | Claude Sonnet 5.5 at half the price; DeepSeek V4.1 Flash, the best open model, about 15 times cheaper |
| Reading and writing text | Gemini 4 Argon, #1 on Text | GLM-5.3 Flash, a step behind and about 17 times cheaper |
| Web research | GPT-5.6 Sol, #1 on Search | Qwen3.8 Max, tied for #1 at less than half the price |
| Long documents | Claude Opus 5, #1 on Document | Claude models hold the top seven places |
| Images | GPT-Image-2.5, #1 on Text-to-Image | Not on OpenRouter; called directly |

Three rules:

- The model that checks the work comes from a different company than the model that did it. Arena's own research found AI judges favor their own answers 70% more often than people do.
- When two choices are close, both run on real tasks, blind, for a week. The winner stays.
- Agent work runs on a flat monthly subscription. Outside models cost money per use, so they get a weekly dollar cap and a public cost ledger. Night jobs use batch prices, often half price. Providers that keep or train on data are switched off.

Next: Arena's own router, called Max, picks a model for each task. In Arena's test it matched the top model at 37% lower cost. Its API has a waitlist. When it opens, Phoenix can hand Max the hard jobs.

## Safe to ship

A change ships without a person only if all of these hold:

- It collects no personal data.
- It takes no payments and needs no sign-ins.
- It sends nothing to anyone.
- One git revert undoes it.
- It passes every check.

Anything else waits for a person.

## The morning

One message. What changed, what people did, what is waiting. The target is a 15-minute review from a phone, mostly by merging pull requests.

## Steps

1. **Ears.** Done 2026-10-21. A daily job with no AI keeps [the ledger](ledger/signals.csv) and [STATE.md](STATE.md). Visits and the names of people who star need a read token.
2. **Simple front pages.** Done 2026-10-21. Every project README fits on one screen.
3. **Hands.** Anthropic's official GitHub Action in each project, so an agent can work an issue and open a pull request.
4. **More models.** One OpenRouter key, a weekly cap, a cost ledger, and a second-opinion review on every pull request.
5. **Night shift.** Running from 2026-10-22: one nightly run finds a real problem and builds a small tool for it in its own folder, then opens a pull request with a preview link. It cannot publish on its own, and it rests while two pull requests wait for review. Its instructions are [brain/NIGHT.md](brain/NIGHT.md); working across the other projects is still [the plan](brain/BRAIN.md).
6. **New prototypes.** Find problems real people describe, in job posts and forums. Build small tests. Retire the ones nobody uses.

## Not decided yet

- How many AI runs a week Phoenix may use.
- Whether several agents may work at once.
- How the first new prototype is chosen.
