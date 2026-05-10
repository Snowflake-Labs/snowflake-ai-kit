/**
 * Sanitize content to remove potential secrets before posting publicly.
 */

const SECRET_PATTERNS: Array<[RegExp, string]> = [
  // GitHub tokens
  [/ghp_[A-Za-z0-9_]{36,}/g, "[REDACTED_GITHUB_PAT]"],
  [/ghs_[A-Za-z0-9_]{36,}/g, "[REDACTED_GITHUB_SERVER]"],
  [/gho_[A-Za-z0-9_]{36,}/g, "[REDACTED_GITHUB_OAUTH]"],
  [/github_pat_[A-Za-z0-9_]{22,}/g, "[REDACTED_GITHUB_PAT]"],

  // AWS keys
  [/AKIA[A-Z0-9]{16}/g, "[REDACTED_AWS_KEY]"],
  [
    /(?:aws_secret_access_key|aws_session_token)\s*[:=]\s*['"]?[^\s'"]{20,}/gi,
    "[REDACTED_AWS_SECRET]",
  ],

  // JWTs (three dot-separated base64url segments)
  [
    /eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}/g,
    "[REDACTED_JWT]",
  ],

  // Bearer tokens in headers
  [/Bearer\s+[A-Za-z0-9._~+\/=-]{20,}/gi, "[REDACTED_BEARER]"],

  // Snowflake connection strings
  [/snowflake:\/\/[^\s'"]+/gi, "[REDACTED_SF_URI]"],

  // PEM private key blocks
  [
    /-----BEGIN (?:RSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA )?PRIVATE KEY-----/g,
    "[REDACTED_PRIVATE_KEY]",
  ],

  // Slack tokens
  [/xoxb-[0-9-]+[a-zA-Z0-9-]+/g, "[REDACTED_SLACK]"],
  [/xoxp-[0-9-]+[a-zA-Z0-9-]+/g, "[REDACTED_SLACK]"],

  // Generic key=value patterns (api_key, token, secret, password assignments)
  [
    /(?:api[_-]?key|token|secret|password)\s*[:=]\s*['"]?[^\s'"]{8,}/gi,
    "[REDACTED]",
  ],

  // Large base64 blobs (likely keys/certs)
  [/[A-Za-z0-9+/]{100,}={0,2}/g, "[REDACTED_KEY]"],
];

export function sanitizeContent(content: string): string {
  let result = content;
  for (const [pattern, replacement] of SECRET_PATTERNS) {
    result = result.replace(pattern, replacement);
  }
  return result;
}
