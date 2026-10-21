# Phoenix

Phoenix works every night on a set of public projects. It listens to what real people do, gives each job to the best-value AI model, and shows all of its work here.

**Status:** plan stage. Nothing runs yet. Read [the plan](PLAN.md).

## How a night works

1. **Listen.** Collect what people did: visits, stars, issues, comments.
2. **Choose.** Pick one useful change per project and write it as a public issue.
3. **Build.** An AI agent works the issue inside that project and opens a pull request.
4. **Check.** Tests, a privacy filter, and a second AI from a different company review the change.
5. **Ship or hold.** Safe changes go live. Anything else waits for a person.
6. **Report.** One short message each morning.
7. **Learn and prune.** Keep what works. Retire what nobody uses, judged by a pass mark set in advance.

## Projects

- [Global Observatory](https://github.com/guillearria/global-observatory): world events, long-term threats and history's worst disasters, checked against approved sources.
- [Vertical Agent Solutions](https://github.com/guillearria/vertical-agent-solutions): plain-English guides to AI agents for small businesses.
- [Swing Lab](https://github.com/guillearria/swing-lab): an AI's stock predictions, made in public and scored.

## Rules

- Everything Phoenix does is public: issues, pull requests, costs and results.
- A stranger's issue is feedback. It becomes work only when a person or Phoenix labels it.
- Each job goes to the model that does it best for the price. The table is [models.json](models.json).

A personal project by [Guillermo Arria-Devoe](https://github.com/guillearria).
