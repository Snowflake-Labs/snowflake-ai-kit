# Contributing to Snowflake AI Kit

We welcome contributions from the community — new skills, builder app improvements, bug fixes, or documentation.

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/<your-username>/snowflake-ai-kit.git
   cd snowflake-ai-kit
   ```

2. Create a feature branch:
   ```bash
   git checkout -b add-my-skill
   ```

## Adding a New Skill

1. **Copy the template:**
   ```bash
   cp -r snowflake-skills/TEMPLATE snowflake-skills/my-skill-name
   # or for general-purpose skills:
   cp -r general-skills/TEMPLATE general-skills/my-skill-name
   ```

2. **Edit `SKILL.md`** — this is the agent-facing entry point. See [Skill Best Practices](#skill-best-practices) below for required sections and formatting.

3. **Edit `README.md`** — this is the human-facing documentation:
   - Prerequisites and setup
   - Usage examples with Cortex Code JSON config
   - Links to external docs

4. **Add supporting files** as needed:
   - `templates/` — SQL or code templates the agent can scaffold
   - `references/` — detailed guides, schemas, troubleshooting
   - `scripts/` — helper scripts the agent can execute

5. **Register the skill in installers:**
   - `snowflake-skills/install_skills.sh` — add to `SNOWFLAKE_SKILLS` list, `get_skill_description()`, and `get_skill_files()`
   - `install.ps1` — add to `$skills` array in `Install-SkillsDirect`

6. **Run the automation pipeline:**
   ```bash
   # Validate structure and frontmatter
   .github/scripts/validate-skill.sh snowflake-skills/my-skill-name

   # Sync SKILL.md to all agent rule directories (.cursor, .claude, .windsurf, .gemini)
   .github/scripts/sync-agent-rules.sh

   # Regenerate the skills table in snowflake-skills/README.md
   .github/scripts/generate-skills-table.sh
   ```

## Skill Best Practices

Skills are markdown files that teach AI coding agents how to complete tasks. The agent follows them literally — clarity and structure matter.

### Required Sections

Every `SKILL.md` must include these sections:

| Section | Purpose | CI Enforced? |
|---------|---------|:---:|
| **YAML frontmatter** (`name`, `description`) | Identifies the skill and triggers activation | Yes |
| **`## When to Use`** | Lists conditions for when the skill applies | Yes |
| **`## Tools Used`** | Documents which tools the skill uses and why | No |
| **`## Stopping Points`** | Lists where the workflow pauses for user input | No |
| **`## Output`** | Describes what the skill produces | No |

### Frontmatter

The `description` field is the primary trigger mechanism. Include:
1. What the skill does (purpose)
2. When to use it (trigger conditions)
3. Specific keywords that should activate it

```yaml
---
name: my-skill-name
description: "What this skill does. Use for: X, Y, Z. Triggers: keyword1, keyword2, keyword3."
---
```

### Stopping Points

Skills that create resources, execute SQL, or make billable changes **must** include stopping points. Use this exact format:

```markdown
**⚠️ MANDATORY STOPPING POINT**: Do NOT proceed until user explicitly approves.
```

Place stopping points at:
- **Phase 0** — Before any action (consent gate for destructive/billable workflows)
- **After configuration** — User confirms settings before SQL executes
- **After credential display** — User saves credentials before moving on
- **After resource creation** — User verifies results before next step

Do **not** use `**STOP**`, `> **STOP.**`, or other informal variants — the `⚠️ MANDATORY STOPPING POINT` format is the standard.

### Phase 0: Briefing and Consent

Skills that create billable resources or modify infrastructure should start with a Phase 0 briefing:

```markdown
## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Skill Name — What This Skill Does
>
> 1. **Step 1** — What happens
> 2. **Step 2** — What happens
>
> **Requires:** Required roles or permissions
>
> **Billable:** Cost implications (if any)

**⚠️ MANDATORY STOPPING POINT**: Do NOT proceed until user explicitly approves.
```

### Output Section

Describe what the skill produces when complete:

```markdown
## Output

- A running service/resource with description
- Connection credentials or configuration
- Optional: sample data loaded
```

### Line Budget

Keep `SKILL.md` under **500 lines**. If a skill exceeds this:
- Move detailed reference material to `references/` files
- Split distinct workflows into sub-skills
- Cortex Code is already smart — only include what it doesn't already know

### Reference Skill Exception

Skills that are purely reference-based (like `snowflake-docs`) don't need stopping points or Phase 0. They still need `## When to Use` and frontmatter.

## Contributing to Builder Apps

Builder apps live under `builder-apps/`. Each app has its own README with setup instructions.

- **`builder-apps/claude-agent/`** — Claude Code agent with Snowflake MCP tools
- **`builder-apps/cortex-agent/`** — Cortex Agent chat UI

When contributing to builder apps:
- Follow the existing code patterns in the app you're modifying
- Test both backend and frontend changes from the browser (not just curl)
- Never commit credentials, `.env` files, or API keys
- Keep `projects/` directories out of version control (gitignored)

## Code Standards

- Use lowercase with hyphens for directory names (e.g., `my-new-skill`)
- Include realistic, working code examples (no placeholders)
- Use environment variables for any credentials in examples
- No credentials — never commit tokens, keys, `.env` files, or secrets
- Self-contained — each skill directory should work independently
- Agent-agnostic — skills are plain markdown, no proprietary format

## Pull Request Process

1. Create a feature branch from `main`
2. Make changes with clear, descriptive commits
3. Run the full automation pipeline locally:
   ```bash
   .github/scripts/validate-skill.sh          # Validate all skills
   .github/scripts/sync-agent-rules.sh        # Sync to agent rule dirs
   .github/scripts/generate-skills-table.sh   # Update skills table
   ```
4. Open a PR with:
   - Brief description of the skill or change
   - Why it's useful
   - How you tested it
5. Address review feedback

The CI pipeline will automatically:
- Validate skill structure (`validate-skill.sh`)
- Check that the skills table in README.md is current
- Verify agent rules are in sync

## Updating Existing Skills

When improving an existing skill:
- Keep backward compatibility in mind (don't break existing agent workflows)
- Update both `SKILL.md` and `README.md` if the change affects usage
- Re-run `sync-agent-rules.sh` after any `SKILL.md` change
- Test with at least one AI coding agent before submitting

## License

By submitting a contribution, you agree that your contributions will be licensed under the same terms as the project (Apache 2.0). See [LICENSE](LICENSE).
