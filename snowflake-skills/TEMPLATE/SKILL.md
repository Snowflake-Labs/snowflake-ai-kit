---
name: my-skill-name
description: "What this skill does. Use for: X, Y, Z. Triggers: keyword1, keyword2, keyword3."
---

# Skill Name

Brief description (1-2 sentences) of what this skill does and why.

## When to Use

- When the user asks about X
- When working with Y
- When setting up Z

## Tools Used

- `snowflake_sql_execute` — Describe what SQL operations are needed
- `ask_user_question` — Describe what decisions need user input
- `read` / `write` / `edit` — Describe what files are configured

## Bundled Files

```
my-skill-name/
├── SKILL.md                        # This file (agent instructions)
├── README.md                       # Human-facing docs
└── templates/
    ├── setup.sql                   # Describe what this sets up
    └── example.sql                 # Describe what this does
```

## Stopping Points

- Phase 0: User approves the workflow before any action
- Step 1: User confirms configuration choices
- Step N: User reviews results before next action

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Skill Name — What This Skill Does
>
> Describe the workflow at a high level:
>
> 1. **Step 1** — What happens first
> 2. **Step 2** — What happens next
> 3. **Step 3** — What happens last
>
> **Requires:** List any required roles, permissions, or prerequisites
>
> **Billable:** Note any cost implications (if applicable)

**⚠️ MANDATORY STOPPING POINT**: Do NOT proceed until user explicitly approves.

---

## Step 1: Gather Configuration

Ask the user for their preferences using `ask_user_question`:

**Setting 1:** Description and options

**Setting 2:** Description and options

**⚠️ MANDATORY STOPPING POINT**: Confirm all settings with the user before executing any SQL.

---

## Step 2: Create Resources

Using the configuration from Step 1, execute the necessary SQL or commands.

```sql
-- Example SQL
CREATE OR REPLACE ... ;
```

---

## Step 3: Verify and Test

Show results to the user. Run validation queries or test commands.

**⚠️ MANDATORY STOPPING POINT**: Confirm results with the user before proceeding.

---

## Common Issues

| Issue | Solution |
|-------|----------|
| **Problem description** | How to fix it |
| **Another problem** | Another solution |

## Output

- What the skill produces (e.g., running service, configured resource)
- Any artifacts created (e.g., connection strings, credentials)
- Optional outputs (e.g., sample data loaded)

## References

- [Link to relevant docs](https://docs.snowflake.com/...)
