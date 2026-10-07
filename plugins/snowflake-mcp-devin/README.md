# Snowflake Plugin for Devin

Connect any Devin session (Cloud, CLI, Desktop) to Snowflake via a **Managed MCP Server** — governed Cortex Agents, Analyst, Search, and SQL execution with zero local dependencies.

## How it works

```
Devin session ──MCP over HTTPS──▶ Snowflake MCP server ──▶ Cortex Code agent ──▶ Snowflake sandbox
   (Devin VM)                     (tool: cortex_code_agent)                     (runs SQL, Python, dbt)
```

Devin sends a task to the `cortex_code_agent` tool. A Cortex Code agent runs it in a sandbox inside Snowflake, under the access role you grant, and returns the result.

Devin's VM and the Snowflake sandbox are separate machines. Files in Devin's workspace aren't visible to the agent, so Devin passes SQL in the request, or pushes code to Git for Snowflake to pull (see [Pipelines and dbt](#pipelines-and-dbt)).

Running the agent uses warehouse credits and Cortex AI credits on your account.

## Prerequisites

A Snowflake admin with ACCOUNTADMIN, or equivalent privileges, sets up these objects once. Replace these placeholders throughout:

| Placeholder | Meaning |
|---|---|
| `MY_DB`, `MY_DB.MCP_SCHEMA` | Database and schema for the agent and MCP server |
| `MY_WH` | Warehouse the agent's queries run on |
| `MY_DB.DATA_SCHEMA` | Data Devin may read |
| `MY_USER` | Snowflake user who signs in with OAuth |
| `MCP_ACCESS_ROLE` | Role Devin runs as. Everything Devin can do comes from this role |

### 1. Create schema and agent

```sql
CREATE DATABASE IF NOT EXISTS MY_DB;
CREATE SCHEMA IF NOT EXISTS MY_DB.MCP_SCHEMA;

-- Cortex Coding Agent with full toolset
CREATE OR REPLACE AGENT MY_DB.MCP_SCHEMA.SNOWFLAKE_AGENT
  FROM SPECIFICATION $$
models:
  orchestration: auto
tools:
  - tool_spec:
      type: code_toolset_all
      name: sandbox
tool_resources:
  sandbox:
    permission_policy:
      type: always_allow
$$;
```

### 2. Create the MCP server

```sql
CREATE OR REPLACE MCP SERVER MY_DB.MCP_SCHEMA.SNOWFLAKE_MCP
  FROM SPECIFICATION $$
tools:
  - name: cortex_code_agent
    title: Cortex Code Cloud Agent
    type: CORTEX_AGENT_RUN
    identifier: MY_DB.MCP_SCHEMA.SNOWFLAKE_AGENT
    description: >-
      Delegate authorized tasks to a hosted Cortex Code sandbox.
$$;
```

### 3. Create access role and grants

```sql
CREATE ROLE IF NOT EXISTS MCP_ACCESS_ROLE;

GRANT DATABASE ROLE SNOWFLAKE.CORTEX_AGENT_USER TO ROLE MCP_ACCESS_ROLE;
GRANT USAGE ON WAREHOUSE MY_WH TO ROLE MCP_ACCESS_ROLE;
GRANT USAGE ON DATABASE MY_DB TO ROLE MCP_ACCESS_ROLE;
GRANT USAGE ON SCHEMA MY_DB.MCP_SCHEMA TO ROLE MCP_ACCESS_ROLE;
GRANT USAGE ON MCP SERVER MY_DB.MCP_SCHEMA.SNOWFLAKE_MCP TO ROLE MCP_ACCESS_ROLE;
GRANT USAGE ON AGENT MY_DB.MCP_SCHEMA.SNOWFLAKE_AGENT TO ROLE MCP_ACCESS_ROLE;

-- Grant data access as needed
GRANT USAGE ON SCHEMA MY_DB.DATA_SCHEMA TO ROLE MCP_ACCESS_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA MY_DB.DATA_SCHEMA TO ROLE MCP_ACCESS_ROLE;

-- OAuth only: the person who signs in
GRANT ROLE MCP_ACCESS_ROLE TO USER MY_USER;
ALTER USER MY_USER SET DEFAULT_WAREHOUSE = 'MY_WH';
```

The agent above uses `always_allow`, so Devin's requests run without an approval step. `always_ask` doesn't work over MCP. See [Security](#security) for why the role is the control that matters.

### 4. Choose an auth method

Pick one. Both run as `MCP_ACCESS_ROLE`, so they can do exactly the same things. The difference is who Snowflake sees and how the credential is managed:

| | OAuth (recommended) | PAT |
|---|---|---|
| Runs as | `MY_USER`, a real person | `DEVIN_MCP_SVC`, a service user |
| Connected through | A custom MCP you add in Devin | The plugin's built-in **snowflake** MCP |
| Sign-in | Browser sign-in to Snowflake, once | None. Paste a token |
| Credential lifetime | Refresh token (90 days by default), then reconnect | 30 days as written below, then rotate |
| Locked to Devin's IPs | No | Yes, via network policy |
| Audit trail | Queries show the person who signed in | Queries show the service user |


**OAuth (recommended).** Devin's custom MCP form takes a client ID but no secret, so it signs in as a public client using PKCE. The redirect URI below is for app.devin.ai. Dedicated Devin deployments use a different one, so copy the callback URL shown in Devin's custom MCP form.

```sql
CREATE SECURITY INTEGRATION DEVIN_MCP_OAUTH
  TYPE = OAUTH
  OAUTH_CLIENT = CUSTOM
  ENABLED = TRUE
  OAUTH_CLIENT_TYPE = 'PUBLIC'
  OAUTH_REDIRECT_URI = 'https://api.devin.ai/mcp/oauth/callback'
  OAUTH_USE_SECONDARY_ROLES = NONE
  OAUTH_ISSUE_REFRESH_TOKENS = TRUE
  ALLOWED_ROLES_LIST = ('MCP_ACCESS_ROLE');

-- Lets MCP clients request this role. Without it, Devin asks for role ALL, which Snowflake blocks
ALTER SCHEMA MY_DB.MCP_SCHEMA SET OAUTH_SCOPES_SUPPORTED = 'session:role:MCP_ACCESS_ROLE';

-- Copy the OAUTH_CLIENT_ID value for Devin
DESCRIBE SECURITY INTEGRATION DEVIN_MCP_OAUTH;
```

`ALLOWED_ROLES_LIST` limits sign-ins to the access role. Snowflake blocks ACCOUNTADMIN and SECURITYADMIN for OAuth by default. `MY_USER` also needs the grants marked "OAuth only" in step 3.

**PAT.** Use a dedicated service user, locked to Devin's published egress IPs, with a PAT restricted to the access role. Don't use a personal PAT: if it has no role restriction, it runs as your default role, which may be ACCOUNTADMIN.

```sql
-- Devin's egress IPs: https://docs.devin.ai/admin/common-issues
CREATE NETWORK RULE MY_DB.MCP_SCHEMA.DEVIN_EGRESS_RULE
  MODE = INGRESS
  TYPE = IPV4
  VALUE_LIST = ('100.20.50.251', '44.238.19.62', '52.10.84.81', '52.183.72.253',
                '20.172.46.235', '52.159.232.99', '4.204.199.103', '140.232.64.0/26');

CREATE NETWORK POLICY DEVIN_MCP_POLICY
  ALLOWED_NETWORK_RULE_LIST = ('MY_DB.MCP_SCHEMA.DEVIN_EGRESS_RULE');

CREATE USER DEVIN_MCP_SVC
  TYPE = SERVICE
  DEFAULT_ROLE = MCP_ACCESS_ROLE
  DEFAULT_WAREHOUSE = MY_WH
  NETWORK_POLICY = DEVIN_MCP_POLICY;
GRANT ROLE MCP_ACCESS_ROLE TO USER DEVIN_MCP_SVC;

ALTER USER DEVIN_MCP_SVC ADD PROGRAMMATIC ACCESS TOKEN DEVIN_MCP_PAT
  ROLE_RESTRICTION = 'MCP_ACCESS_ROLE'
  DAYS_TO_EXPIRY = 30;
```

Copy `token_secret` from the output. Snowflake shows it only once.

- **Expiry:** the token expires after 30 days. Before then, run `ALTER USER DEVIN_MCP_SVC ROTATE PROGRAMMATIC ACCESS TOKEN DEVIN_MCP_PAT;` and paste the new `token_secret` into Devin.
- **IPs:** the network rule allows Devin Cloud only. If you run the plugin from Devin CLI or Desktop, requests come from your own machine, so add its egress IP to the rule. Devin can change its IPs, so check the list when the connection starts failing.

### 5. Get your MCP server URL

```sql
SELECT LOWER(CURRENT_ORGANIZATION_NAME() || '-' || CURRENT_ACCOUNT_NAME()) AS account_host;
```

Replace any underscores in the result with hyphens. The URL is:

```
https://<account_host>.snowflakecomputing.com/api/v2/databases/MY_DB/schemas/MCP_SCHEMA/mcp-servers/SNOWFLAKE_MCP
```

See the [Snowflake Managed MCP Server docs](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-mcp) for full setup instructions.

## Quick start

### 1. Install the plugin

Choose one. All three install the same skills, rule, and **snowflake** MCP.

**From the repository (recommended).** No download needed, and Reindex picks up updates.
1. Go to [Customize](https://app.devin.ai/customize) → Plugins → Add plugin → From repository.
2. Enter `https://github.com/Snowflake-Labs/snowflake-ai-kit` with subdirectory `plugins/snowflake-mcp-devin`.
3. Devin reads the default branch. To install from another branch, open Plugins → gear icon → Edit manifest, add `"ref": "<branch>"` to the plugin's `requiredPlugins` entry, save, and click Reindex.

**Upload a .zip:**
1. From a clone of this repo: `cd plugins && zip -r snowflake-mcp-devin.zip snowflake-mcp-devin -x '*.DS_Store'`
2. Go to Customize → Plugins → Add plugin → Upload .zip, and upload it to your Personal scope.

**Devin CLI** (from the root of a clone of this repo):
```bash
devin plugins install --local ./plugins/snowflake-mcp-devin
```

### 2. Connect the MCP server

Use the method you chose in Prerequisites step 4. Enable only one Snowflake MCP at a time, so Devin doesn't see two servers. MCP changes apply to new sessions only; running sessions keep what they loaded at start.

#### OAuth (recommended)

The plugin's MCP can't hold OAuth settings (see [Caveats](#caveats)), so add the server as a custom MCP. Keep the plugin installed for its skills, and turn off the toggle on its **snowflake** MCP under Customize → MCPs.

1. Go to Customize → MCPs → Add MCP → Add custom MCP, and fill in:

   | Field | Value |
   |---|---|
   | Name | Anything except `snowflake`, for example `snowflake-oauth` |
   | Transport type | HTTP |
   | Server URL | The URL from Prerequisites step 5 |
   | Authentication | OAuth |
   | Custom headers | `User-Agent: Devin-Snowflake-MCP/0.1` |
   | OAuth client ID | `OAUTH_CLIENT_ID` from `DESCRIBE SECURITY INTEGRATION` |
   | OAuth scope | `session:role:MCP_ACCESS_ROLE refresh_token` |

2. Click Add. Devin replaces the header value with a `${USER_AGENT}` placeholder, so open the MCP's settings and save a `USER_AGENT` credential with the value `Devin-Snowflake-MCP/0.1`. Without it, the server fails at startup.
3. Click Connect, sign in to Snowflake as `MY_USER`, and approve.
4. Click Test tools. You should see `cortex_code_agent`.

When the refresh token expires, Devin's calls fail with an auth error. Click Connect again and sign in.

For organization-scope OAuth, sign in with a service account rather than a personal one. Every member's sessions share that connection.

#### PAT

1. Go to Customize → MCPs, and open **snowflake** under "From plugins".
2. Click Connect MCP and fill in:

   | Variable | Value |
   |---|---|
   | `SNOWFLAKE_MCP_URL` | The URL from Prerequisites step 5 |
   | `SNOWFLAKE_PAT` | The `token_secret` for `DEVIN_MCP_PAT` from Prerequisites step 4. Not a personal PAT |

3. Make sure the toggle is on, and turn off any OAuth custom MCP.

To replace the token later, edit `SNOWFLAKE_PAT` on the same screen and start a new session.

#### Verify

In a new session, ask Devin to run `SELECT CURRENT_USER(), CURRENT_ROLE()`.

| Path | Expected result |
|---|---|
| OAuth | `MY_USER`, `MCP_ACCESS_ROLE` |
| PAT | `DEVIN_MCP_SVC`, `MCP_ACCESS_ROLE` |

If it returns another user or ACCOUNTADMIN, stop: the wrong credential is connected (see [Troubleshooting](#troubleshooting)). Snowflake's login history confirms what connected:

```sql
SELECT event_timestamp, user_name, first_authentication_factor, client_ip
FROM TABLE(INFORMATION_SCHEMA.LOGIN_HISTORY(DATEADD('hour', -1, CURRENT_TIMESTAMP()), CURRENT_TIMESTAMP()))
ORDER BY event_timestamp DESC LIMIT 10;
```

### 3. Use it

Start a new Devin session and ask naturally:

```
Query the top 10 customers by revenue from MY_DB.DATA_SCHEMA.ORDERS
```

Devin picks a skill automatically, or you can call one directly with the commands below. Devin sees only what `MCP_ACCESS_ROLE` can see, so tables without a `SELECT` grant won't appear.

### Available skills

| Skill | Command | What it does |
|---|---|---|
| Query | `/snowflake:snowflake-query` | Run SQL queries |
| Explore | `/snowflake:snowflake-explore` | Discover databases, tables, columns |
| Cortex | `/snowflake:snowflake-cortex` | Cortex Analyst, Search, Agents |
| Pipelines | `/snowflake:snowflake-pipelines` | Dynamic Tables, streams, tasks, dbt |
| Governance | `/snowflake:snowflake-governance` | Access audit, policies, tags, roles |
| Semantic Views | `/snowflake:snowflake-semantic-views` | Create and manage semantic models |
| DCM | `/snowflake:snowflake-dcm` | Database Change Management projects |

## Pipelines and dbt

Devin can build Dynamic Tables, streams, tasks, and dbt projects through MCP. Everything runs inside Snowflake, so Devin needs no local Snowflake credentials.

### Set up a dev schema

An admin gives the access role write privileges on one dev schema only. The role reads sources through the `SELECT` grants in Prerequisites step 3.

```sql
CREATE SCHEMA IF NOT EXISTS MY_DB.DEVIN_DEV;
GRANT USAGE ON SCHEMA MY_DB.DEVIN_DEV TO ROLE MCP_ACCESS_ROLE;
GRANT CREATE TABLE, CREATE VIEW, CREATE DYNAMIC TABLE, CREATE STREAM, CREATE TASK, CREATE DBT PROJECT
  ON SCHEMA MY_DB.DEVIN_DEV TO ROLE MCP_ACCESS_ROLE;
GRANT EXECUTE TASK ON ACCOUNT TO ROLE MCP_ACCESS_ROLE;
-- So admins can see objects Devin creates
GRANT ROLE MCP_ACCESS_ROLE TO ROLE SYSADMIN;
-- Streams and incremental Dynamic Tables need change tracking; the source owner runs this per table
ALTER TABLE MY_DB.DATA_SCHEMA.<source_table> SET CHANGE_TRACKING = TRUE;
```

Then ask Devin for a pipeline in `MY_DB.DEVIN_DEV`, for example: "Create a Dynamic Table that counts orders by day." Tasks are created suspended. Ask Devin to resume one only when you want it to run on schedule.

### Set up dbt

Devin can't hand files to the Snowflake sandbox directly. Instead, Devin pushes the dbt project to GitHub, and Snowflake pulls it through a Git repository object.

1. **Create an empty GitHub repo.** This example assumes it's public. For a private repo, also create a secret and add it to the API integration with `ALLOWED_AUTHENTICATION_SECRETS`.
2. **Give Devin push access.** Linking GitHub under Devin's personal Connections only sets your identity. Install the Devin GitHub app on the account or organization that owns the repo, and connect it in Devin's organization settings → Integrations → GitHub. Without it, pushes fail with HTTP 403.
3. **Connect Snowflake to the repo.** An admin runs this. The API integration needs ACCOUNTADMIN or the `CREATE INTEGRATION` privilege:

```sql
CREATE API INTEGRATION DEVIN_GIT_API
  API_PROVIDER = GIT_HTTPS_API
  API_ALLOWED_PREFIXES = ('https://github.com/<owner>/<repo>')
  ENABLED = TRUE;
GRANT USAGE ON INTEGRATION DEVIN_GIT_API TO ROLE MCP_ACCESS_ROLE;

CREATE GIT REPOSITORY MY_DB.DEVIN_DEV.DEVIN_DBT_REPO
  API_INTEGRATION = DEVIN_GIT_API
  ORIGIN = 'https://github.com/<owner>/<repo>';   -- no .git suffix
GRANT READ, WRITE ON GIT REPOSITORY MY_DB.DEVIN_DEV.DEVIN_DBT_REPO TO ROLE MCP_ACCESS_ROLE;
```

4. **Ask Devin to build and push the project** to `main`. The project needs a `profiles.yml` at its root. Its top-level name must match `profile:` in `dbt_project.yml`. Snowflake ignores `account` and `user`, but they must be present:

```yaml
my_project:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: placeholder
      user: placeholder
      role: MCP_ACCESS_ROLE
      warehouse: MY_WH
      database: MY_DB
      schema: DEVIN_DEV
```

5. **Ask Devin to deploy and run it:**

```sql
ALTER GIT REPOSITORY MY_DB.DEVIN_DEV.DEVIN_DBT_REPO FETCH;
CREATE DBT PROJECT MY_DB.DEVIN_DEV.DEVIN_DBT FROM '@MY_DB.DEVIN_DEV.DEVIN_DBT_REPO/branches/main';
EXECUTE DBT PROJECT MY_DB.DEVIN_DEV.DEVIN_DBT ARGS = 'build';
```

After later changes, Devin pushes again, runs `FETCH`, then `ALTER DBT PROJECT MY_DB.DEVIN_DEV.DEVIN_DBT DEPLOY FROM '@MY_DB.DEVIN_DEV.DEVIN_DBT_REPO/branches/main'`, then `EXECUTE` again.

## Security

The Snowflake role is the main control. Devin Cloud has no per-tool approval for MCP calls, and the agent above uses `always_allow`, so anything the role can do, Devin can do without asking. That includes DDL and DML: in testing, the agent created tables through this path.

- **Grant the access role only what Devin needs.** Prefer read-only grants. Add write privileges on specific schemas only when Devin should build objects there.
- **Never connect as ACCOUNTADMIN.** Use OAuth with the access role, or a role-restricted PAT on a service user.
- **Limit where the PAT works.** Use the network policy in Prerequisites step 4 so the token only authenticates from Devin's IPs.
- **`always_ask` isn't a fix.** Over MCP, a write that needs approval stops without running, but MCP still reports the call as successful. Devin can't tell the write never happened.
- **The agent sandbox has internet access.** Agent-generated code can reach external hosts, so treat prompts and fetched content as untrusted.
- **Use Devin security profiles for organizations.** They can limit sessions to approved MCP servers and network destinations.
- **Rotate tokens.** Keep PATs short-lived. Use `SHOW USER PROGRAMMATIC ACCESS TOKENS FOR USER DEVIN_MCP_SVC` to review them.

### Revoke access

To cut Devin off immediately, run whichever applies:

```sql
ALTER USER DEVIN_MCP_SVC REMOVE PROGRAMMATIC ACCESS TOKEN DEVIN_MCP_PAT;  -- PAT
ALTER SECURITY INTEGRATION DEVIN_MCP_OAUTH SET ENABLED = FALSE;           -- OAuth
REVOKE USAGE ON MCP SERVER MY_DB.MCP_SCHEMA.SNOWFLAKE_MCP FROM ROLE MCP_ACCESS_ROLE;  -- both
```

## Caveats

- **Why OAuth isn't in the plugin:** Devin rejects OAuth secrets in plugin files, and it substitutes `${…}` values only in a plugin MCP's URL and headers, not its OAuth client ID or scopes. Each Snowflake account has its own client ID, so the plugin can't ship one. The plugin MCP uses a PAT header, and OAuth uses a custom MCP.
- **User-Agent header required:** Snowflake rejects MCP requests without a User-Agent header (HTTP 400, code 391903). The plugin manifest includes it. For the OAuth custom MCP, you add it yourself (Quick start step 2).
- **Hostname format:** Use hyphens in the account URL (`my-org-my-account`), not underscores. Underscored hostnames silently break MCP connections.
- **Admin setup required:** A Snowflake admin must create the agent, the MCP server, and either the OAuth integration or the PAT service user before this plugin can connect.
- **Skill portability:** These skills use generic SQL instructions, not CoCo-specific tool calls. They work in any MCP-compatible host.
- **Response truncation:** MCP tool responses truncate at 250KB. Use LIMIT and aggregation for large result sets.

## Plugin contents

```
plugins/snowflake-mcp-devin/
├── .devin-plugin/plugin.json              # Devin manifest → HTTP MCP (PAT header)
├── .claude-plugin/plugin.json             # Claude Code fallback
├── AGENTS.md                              # Always-on Snowflake context
├── logo.svg                               # Snowflake icon
├── README.md                              # This file
└── skills/
    ├── snowflake-query/SKILL.md           # SQL queries
    ├── snowflake-explore/SKILL.md         # Data discovery
    ├── snowflake-cortex/SKILL.md          # Cortex AI services
    ├── snowflake-pipelines/SKILL.md       # Dynamic Tables, streams, tasks, dbt
    ├── snowflake-governance/SKILL.md      # Access and policy audit
    ├── snowflake-semantic-views/SKILL.md  # Semantic view management
    └── snowflake-dcm/SKILL.md             # Infrastructure as code
```

**Zero local dependencies.** No Python, no Node.js, no Docker, no hooks. The plugin is purely declarative — it points Devin at the remote Managed MCP Server and provides context via `AGENTS.md` and skills.

## Troubleshooting

| Symptom | Fix |
|---|---|
| HTTP 400, "Invalid or empty User-Agent header" | PAT: the plugin manifest sets it, so reinstall the unmodified plugin. OAuth: save the `USER_AGENT` credential on the custom MCP |
| `CURRENT_USER()` returns your own user, or the role is ACCOUNTADMIN | A personal PAT is in `SNOWFLAKE_PAT`, or the wrong MCP is on. Replace it with the `DEVIN_MCP_PAT` secret, check that only one Snowflake MCP is enabled, and start a new session. Rotate the personal PAT, since it was stored in Devin |
| Changes to MCPs or secrets have no effect | Running sessions keep the config they started with. Start a new session |
| Repo install: "No plugin manifest found" | Devin read the default branch, where the plugin doesn't exist. Add `ref` in Edit manifest (see Quick start step 1) and Reindex |
| OAuth worked, then stopped | The refresh token expired. Click Connect on the custom MCP and sign in again |
| HTTP 401, "Programmatic access token is invalid" | The PAT expired or was copied incorrectly. Create a new one on `DEVIN_MCP_SVC` and update `SNOWFLAKE_PAT` |
| "The role ALL requested has been explicitly blocked" | Set the OAuth scope to `session:role:<access role>` in the custom MCP form, and set `OAUTH_SCOPES_SUPPORTED` on the schema |
| "OAuth client integration with the given client id is not found" | The custom MCP has a stale client ID. `CREATE OR REPLACE SECURITY INTEGRATION` generates a new one. Delete the custom MCP and add it again with the current ID |
| "Could not set up snowflake: configuration differs" | Two MCP entries share the name. On Customize → MCPs, remove the stale one under "Not in use", then reconnect |
| MCP server hostname connection failure | Use hyphens (`-`) not underscores (`_`) in the account hostname |
| "Session failed to initialize" | Set `DEFAULT_WAREHOUSE` on the user (`MY_USER` or `DEVIN_MCP_SVC`) |
| OAuth MCP fails at startup, or the header shows `${USER_AGENT}` | Save a `USER_AGENT` credential on the custom MCP (value `Devin-Snowflake-MCP/0.1`) |
| HTTP 401 / login blocked for the service user | The client IP isn't in `DEVIN_EGRESS_RULE`. Check `client_ip` in login history against Devin's published list. Devin CLI and Desktop connect from your machine's IP |
| A write "succeeds" but nothing changed | The agent uses `always_ask`. Over MCP, approvals can't be relayed, so the write never ran |
| Devin push fails with HTTP 403 | Install the Devin GitHub app on the repo owner, and connect it in Devin org settings → Integrations → GitHub |
| "Connect GitHub Organization" loops back to Connect | The app is already installed. Uninstall it on GitHub (Settings → Applications → Installed GitHub Apps), then connect again from Devin |
| `CREATE GIT REPOSITORY` rejects the origin | The origin must match `API_ALLOWED_PREFIXES`. Drop the `.git` suffix |
| Stream or Dynamic Table creation fails on a source table | The source owner must run `ALTER TABLE ... SET CHANGE_TRACKING = TRUE` |
| Admins can't see objects Devin created | Run `GRANT ROLE MCP_ACCESS_ROLE TO ROLE SYSADMIN` |
| Tools not visible after connecting | Verify `GRANT USAGE ON MCP SERVER` and `GRANT USAGE ON AGENT` to `MCP_ACCESS_ROLE` |
| `CREATE DBT PROJECT` or `EXECUTE DBT PROJECT` fails on the profile | Add a `profiles.yml` to the project root (see [Set up dbt](#set-up-dbt)), push, and run `FETCH` again |
| "This plugin's MCP server is disabled or misconfigured" | Don't put `oauthClientId`/`oauthClientSecret` in the plugin manifest. Devin rejects OAuth secrets in plugin files. |
