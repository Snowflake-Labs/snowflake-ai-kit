# Remote Cortex Code through managed MCP

Remote mode delegates Snowflake-side tasks to a hosted Coding Agent through your
AI agent's native MCP connection. It needs Python for the plugin hooks, but **no
local Cortex Code or Snowflake CLI**. Local mode remains the default.

```text
Claude Code / Codex / Devin CLI or Desktop + plugin
  -> host-authenticated Snowflake-managed MCP tool (CODING_AGENT)
  -> Snowflake-hosted CoCo sandbox
```

This is an opt-in integration, not full local CLI parity. The plugin does not
host an MCP server, implement OAuth, store tokens, or provision account resources.
Database migrations (Snowflake AIM) need the local CLI, so they don't run in remote
mode: a migration prompt stops and asks you to set `CORTEX_PLUGIN_BACKEND=local`.

## 1. Prepare the server and host

Have your Snowflake administrator create a
[Snowflake-managed MCP server](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-mcp)
with a `CODING_AGENT` tool. It runs the hosted Cortex Code agent with its full
toolset (bash, files, SQL, skills). You don't create an agent object: the agent's
settings live in the tool's `config`. Use a role restricted to the intended data
and operations. The caller needs access to the MCP server and the underlying resources.

### Example specification

```sql
CREATE OR REPLACE MCP SERVER <database>.<schema>.<server>
  FROM SPECIFICATION $$
tools:
  - name: cortex_code_agent
    title: Cortex Code Cloud Agent
    type: CODING_AGENT
    description: >-
      Delegate authorized coding tasks to a hosted Cortex Code sandbox.
      Honor the configured approval policy. Approval-requiring operations
      may pause because this plugin does not relay permission decisions.
    config:
      models:
        orchestration: auto
      tool_resources:
        code_toolset_all:
          permission_policy:
            type: always_ask
$$;
```

`CODING_AGENT` is the **MCP tool type**. Snowflake adds the full coding toolset
(`code_toolset_all`) to every run; `tool_resources.code_toolset_all` sets its approval
policy. `cortex_code_agent` is the administrator-chosen **MCP wire name**; another
name works too. The plugin uses the host's namespaced identifier for that wire name,
not the type string. `CORTEX_AGENT_RUN` also works if you already manage a Cortex
Agent object; the plugin matches the tool by its input schema, not its type.

### Verify the server

Before enabling the plugin, an administrator should run `DESCRIBE MCP SERVER` and:

1. Find the intended tool by its exact wire name. Verify its type is `CODING_AGENT`.
2. Check its `config`: the approval policy and any workspace mounts. Preserve
   `always_ask` unless a different policy has been independently authorized.
3. Confirm the caller's access.

A tool name, description, or compatible `text` schema is **not proof** of the tool
type: a data agent can advertise the same interface. The plugin's offline checks
cannot inspect server objects. The administrator must verify it.

### Connect the host

Connect that server in Claude Code, Codex, or Devin using its native remote MCP setup and
authenticate there. In Devin, add it as a custom MCP; the
[Snowflake Managed MCP plugin guide](../snowflake-mcp-devin/README.md) covers the URL,
`User-Agent` header, and OAuth or PAT setup. Prefer OAuth; never place credentials in this plugin's files.
Use the account-specific server URL supplied by your administrator:

```text
https://<account-host>/api/v2/databases/<database>/schemas/<schema>/mcp-servers/<server>
```

> **Important:** Use hyphens (`-`) instead of underscores (`_`) in the account
> hostname. For example, use `my-org-my-account.snowflakecomputing.com`, not
> `my_org-my_account.snowflakecomputing.com`. MCP servers have known connection
> issues with underscored hostnames.

Confirm the host lists the agent tool and inspect its input schema: it should
accept `text` as a string. Copy its **full host-visible tool identifier**,
including the server namespace. Do not copy just the server name or its URL.
Do not point this mode at `cortex mcp serve`: that is a different local transport
and has a different task-input contract.

For example, register the URL with a local host alias `snowflake-cloud`:

```bash
claude mcp add --transport http snowflake-cloud "https://<account-host>/api/v2/databases/<database>/schemas/<schema>/mcp-servers/<server>"
# Or:
codex mcp add snowflake-cloud --url "https://<account-host>/api/v2/databases/<database>/schemas/<schema>/mcp-servers/<server>"
```

Registration alone does **not** authenticate. Complete the host's supported
Snowflake OAuth configuration (including an admin-provisioned OAuth integration
where required); the plugin does not create one. A successful test using a
Snowflake connector session token does not establish host OAuth compatibility.
After connecting, copy the actual tool identifier from the host; do not assume
it is the same as the unqualified `cortex_code_agent` wire name.

### Configure access role and grants

Create a dedicated least-privilege role for MCP access. Do not use ACCOUNTADMIN
or SECURITYADMIN — these are blocked by default in custom OAuth integrations.

```sql
CREATE ROLE <mcp_access_role>;

GRANT DATABASE ROLE SNOWFLAKE.CORTEX_AGENT_USER TO ROLE <mcp_access_role>;
GRANT USAGE ON WAREHOUSE <warehouse> TO ROLE <mcp_access_role>;
GRANT USAGE ON DATABASE <database> TO ROLE <mcp_access_role>;
GRANT USAGE ON SCHEMA <database>.<schema> TO ROLE <mcp_access_role>;
GRANT USAGE ON MCP SERVER <database>.<schema>.<server> TO ROLE <mcp_access_role>;

GRANT ROLE <mcp_access_role> TO USER <username>;
```

Grant additional data access as needed (SELECT on tables, USAGE on schemas).

### Claude Code OAuth setup

Claude Code uses a loopback OAuth flow with these constraints:

- The redirect URI is hardcoded to `http://localhost:<PORT>/callback` — only the
  port is configurable (via `--callback-port`). The path `/callback` cannot be
  changed.
- Claude Code requests `scope=session:role:all`, which resolves to the connecting
  user's `DEFAULT_ROLE`. It does **not** mean "all roles."
- The default `BLOCKED_ROLES_LIST` (ACCOUNTADMIN, SECURITYADMIN) cannot be removed
  from custom OAuth integrations.

Create the security integration:

```sql
CREATE SECURITY INTEGRATION <integration_name>
  TYPE = OAUTH
  OAUTH_CLIENT = CUSTOM
  ENABLED = TRUE
  OAUTH_CLIENT_TYPE = 'CONFIDENTIAL'
  OAUTH_REDIRECT_URI = 'http://localhost:10106/callback'
  OAUTH_ALLOW_NON_TLS_REDIRECT_URI = TRUE
  OAUTH_USE_SECONDARY_ROLES = NONE
  OAUTH_ISSUE_REFRESH_TOKENS = TRUE
  ALLOWED_ROLES_LIST = ('<mcp_access_role>');
```

Set each user's default role and warehouse. This is **required** — if
`DEFAULT_ROLE` is ACCOUNTADMIN, the OAuth consent fails with "The role ALL
requested has been explicitly blocked":

```sql
ALTER USER <username> SET DEFAULT_ROLE = '<mcp_access_role>'
                          DEFAULT_WAREHOUSE = '<warehouse>';
```

Retrieve the client credentials:

```sql
SELECT SYSTEM$SHOW_OAUTH_CLIENT_SECRETS('<INTEGRATION_NAME>');
```

Register the MCP server in Claude Code with the OAuth credentials:

```bash
export MCP_CLIENT_SECRET='<OAUTH_CLIENT_SECRET>'
claude mcp add --transport http \
  --client-id '<OAUTH_CLIENT_ID>' \
  --client-secret \
  --callback-port 10106 \
  snowflake-cloud \
  "https://<account-host>/api/v2/databases/<database>/schemas/<schema>/mcp-servers/<server>"
```

Then authenticate with `/mcp` in Claude Code or by starting a new session.

> **Caution:** `CREATE OR REPLACE SECURITY INTEGRATION` regenerates the client ID
> and secret. You must re-register the MCP server in Claude Code after each
> recreation.

## 2. Select remote mode before launching the host

macOS/Linux example (replace the example tool identifier with the actual one):

```bash
export CORTEX_PLUGIN_BACKEND=remote
export CORTEX_PLUGIN_MCP_TOOL=mcp__snowflake__cortex_code_agent
claude
# Or launch codex or devin from this environment.
```

PowerShell:

```powershell
$env:CORTEX_PLUGIN_BACKEND = "remote"
$env:CORTEX_PLUGIN_MCP_TOOL = "mcp__snowflake__cortex_code_agent"
codex
# Or launch claude or devin from this environment.
```

Host naming conventions can differ. The example is not an assumed tool name.
Accepted identifiers start with a letter and contain up to 256 letters, digits,
underscores, dots or hyphens. Settings are inherited by plugin hooks and helper
commands. Restart the host after changing them; for graphical hosts, configure
their launch environment rather than assuming shell exports are inherited.

| Setting | Meaning |
| --- | --- |
| `CORTEX_PLUGIN_BACKEND` | `local` (default) or `remote`; other values block routing |
| `CORTEX_PLUGIN_MCP_TOOL` | Exact native MCP tool identifier, required in remote mode |

These transport settings are separate from the local security-envelope YAML.
No personal connection files are read to configure the remote transport. Selecting
local ignores the MCP tool setting. To switch back, set `CORTEX_PLUGIN_BACKEND=local`
and restart the host; existing local prerequisites and MCP conflict checks apply.
Switching never transfers session IDs between backends.

Check configuration without connecting to Snowflake:

```bash
bash /path/to/plugin/scripts/run_python.sh /path/to/plugin/scripts/router/backend.py
```

Then try `$cortex-run show my Snowflake warehouses`. Auto-routed Snowflake prompts
also use remote mode. Local file/git work remains with your host agent. If the
configured tool cannot be found or its schema is incompatible, delegation stops;
the plugin does not automatically choose another tool or fall back to the CLI.

## Approval and data boundaries

Before its first delegation, the routing workflow asks for consent to remote
execution and explains that **the local RO/RW/RESEARCH/DEPLOY envelopes do not
apply**. The host controls approval of the outer MCP call. The configured agent
policy governs commands inside it. The plugin cannot inspect or enforce each
inner command, and its local YAML policy and audit logger do not cover them.
Workflow consent is an instruction to the host agent, not a programmatic gate.
Organizations requiring local envelope enforcement should not enable this mode.

The workflow runs a credential-path preflight before delegation and prohibits
automatic upload of local files or transcripts. That check is not a general
secret detector. Send only task text and minimal context authorized for the
selected Snowflake destination; use host and Snowflake access controls for
enforcement.

Do not change the tool's policy to `always_allow` to work around a failed or paused run.
`always_ask` may automatically execute operations classified as safe, such as
`SELECT 1` or harmless shell output. It does not mean every call must pause.
Such probes do not establish that state-changing operations have been tested.
The plugin does not relay approvals: it never sends the tool's
`permission_decisions` argument, even though `CODING_AGENT` accepts it. If a run pauses for approval, stop and use a supported
approval workflow rather than sending "approved" as another task. A task labeled
"read only" and an MCP `readOnlyHint` are not security controls.

## Conversation and file behavior

- **Continuation is capability-dependent.** When the server advertises optional
  `thread_id` and returns an ID, the host can retain it in the current conversation
  and pass it on follow-ups to the same tool/account, with every field the helper
  lists in `thread_arguments` (`CODING_AGENT` also needs `parent_message_id`).
  The thread keeps the hosted sandbox. New topics start fresh.
  The plugin does not persist remote IDs in the CLI session-state file.
- **Older servers remain stateless.** No advertised/returned ID means no assumed
  continuity. The host explains this and can send a short authorized summary
  with user agreement. Deployment availability varies; inspect the actual schema.
- **Files live remotely.** A sandbox cannot implicitly read or edit a local
  checkout. Persistent files require a configured Snowflake workspace. User-local
  skills, CLI settings and MCP connections are not automatically copied remotely.
- **Results are not automatic downloads.** The host summarizes returned text and
  actual artifact references. Rich resource-based artifact delivery and detailed
  streaming progress are not guaranteed by this integration.
- **No automatic replay.** After a timeout or connection loss the result may be
  unknown. Verify what completed before deciding whether to retry a write.

The complete host-agent contract is in
[Remote MCP delegation](skills/cortex-router/references/remote-mcp.md).

### Check the advertised input contract

The remote workflow runs `backend.py --check-tool` with the configured
host-visible tool's descriptor on stdin. A minimal supported descriptor is:

```json
{
  "name": "mcp__snowflake__cortex_code_agent",
  "inputSchema": {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"]
  }
}
```

Use the actual host identifier and advertised schema, not this example verbatim.
The helper checks the name, a string `text` and unsupported required arguments.
`text` may be optional only when the schema also declares `permission_decisions`,
as `CODING_AGENT` does, because that argument replaces `text` on an approval reply.
It returns `supports_thread_id: false` for this text-only contract. This is a
valid deployment: call with `{"text": "..."}` and treat every call as independent.
For a `CODING_AGENT` tool it returns `supports_thread_id: true`,
`thread_id_type: "string"` and `thread_arguments: ["thread_id", "parent_message_id"]`:
a follow-up sends both, with the `thread_id` and `message_id` from the prior result. The helper reports `agent_identity_verified: false` deliberately;
it does not replace the administrator's server verification.

## Validation checklist

Offline tests run in the regular macOS/Linux and Windows harnesses. They exercise
actual hook subprocesses with an isolated home and no Cortex CLI, not a live MCP
server. For release qualification, also run this manual checklist in **each host**
against a dedicated test account and its configured native MCP connection:

1. With no Cortex CLI installed, start remote mode and verify no installation or
   Snowflake MCP conflict warning appears.
2. Consent to the approval boundary; delegate a read-only warehouse listing.
   Verify the intended account/role and successful SQL execution, not just agent text.
3. Verify a representative hosted skill is available; do not assume local skill parity.
4. If thread support is advertised, ask a follow-up and confirm the returned ID is
   reused; start a new topic and confirm it is omitted. On an older server, verify
   the stateless explanation instead.
5. Ask to edit a local file and verify it stays with the host. Verify a remote artifact
   is not reported as a downloaded local file.
6. Exercise an approval-requiring operation in a disposable environment: a paused
   result must be reported as blocked, not approved by text or retried automatically.
7. Disconnect/rename the tool and verify a clear failure without CLI fallback.
8. Restart in local mode and verify the existing CLI flow still works.

The PR's test record should distinguish offline checks from these live checks.