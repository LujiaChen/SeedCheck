# SeedCheck

SeedCheck tests whether an AI reviewer can catch mistakes in another AI's writing.

A report is written from a source document. Known mistakes are planted in it on purpose. A reviewer AI then checks the report. Because the locations of the mistakes are known, the following can be measured:

- how many of the planted mistakes the reviewer finds,
- how often the reviewer complains about a report that has no planted mistakes,
- how much API usage each found mistake costs.

## Why this matters

Many AI tools include a checker step, and it is often assumed that the checker works. Few projects measure this. SeedCheck provides a small, repeatable test.

## Out of scope

- Ranking AI companies or models.
- Security testing.
- Judging writing quality.
- Checking facts that are not in the source document.

## Status

Early stage. The planning and setup documents are in place. No test results yet.

- Decision record: [docs/adr/0001-project-init.md](docs/adr/0001-project-init.md)
- Predictions written before testing: [docs/hypotheses.md](docs/hypotheses.md)
- Progress notes: [docs/log/](docs/log/)

## License

MIT. See [LICENSE](LICENSE).
