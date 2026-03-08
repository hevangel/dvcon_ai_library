# Contribution Guide

Thanks for your interest in contributing to this project.

## Ways To Contribute

- Report bugs and request features through GitHub Issues.
- Improve code, tests, documentation, or developer tooling.
- Help review pull requests and reproduce reported problems.

## Before You Start

- Read `README.md` for the project overview and local run instructions.
- Read `AGENTS.md` for repository-specific implementation notes and current architecture.
- Check existing GitHub Issues before opening a new one to avoid duplicates.

## Filing Issues

Please use GitHub Issues for:

- bug reports
- feature requests
- documentation problems
- usability feedback

When possible, include:

- a clear summary
- steps to reproduce
- expected behavior
- actual behavior
- relevant logs, screenshots, or environment details

## Development Workflow

Use a fork-and-pull-request workflow:

1. Fork the repository on GitHub.
2. Create a branch in your fork for the change.
3. Make focused changes with clear commit history.
4. Run the relevant local checks before opening a pull request.
5. Open a pull request back to this repository.

## Local Checks

For backend changes, run:

```bash
uv run --project backend pytest
```

For local development, use the existing project scripts described in `README.md`.

## Pull Request Expectations

Please keep pull requests:

- focused on one logical change
- clearly described
- linked to the related GitHub Issue when applicable
- updated with docs when behavior or workflow changes

Helpful pull request details include:

- what changed
- why it changed
- how it was tested
- any follow-up work still needed

## Code Style

- Use `uv` for Python dependency management and Python commands.
- Prefer snake_case and 4-space indentation.
- Avoid committing secrets, `.env`, generated corpus data, or local machine state.
- Follow the existing structure and naming patterns in the repo.

## Community Expectations

- Be respectful and constructive.
- Assume good intent.
- Give feedback on the work, not the person.
- Welcome new contributors and different experience levels.

## Questions

If you are unsure where to start, open a GitHub Issue and describe the problem or idea before writing code.
