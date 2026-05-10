import { describe, expect, it } from "bun:test";
import { generateBranchName } from "../src/utils/branch";
import { sanitizeContent } from "../src/utils/sanitize";

describe("generateBranchName", () => {
  it("generates a valid branch name", () => {
    const name = generateBranchName({
      prefix: "cortex-code/",
      entityType: "pr",
      entityNumber: 42,
    });
    expect(name).toMatch(/^cortex-code\/pr-42-\d+$/);
  });

  it("uses issue entity type", () => {
    const name = generateBranchName({
      prefix: "cortex-code/",
      entityType: "issue",
      entityNumber: 7,
    });
    expect(name).toMatch(/^cortex-code\/issue-7-\d+$/);
  });
});

describe("sanitizeContent", () => {
  it("redacts GitHub personal access tokens", () => {
    const input = "Token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij";
    expect(sanitizeContent(input)).toContain("[REDACTED]");
    expect(sanitizeContent(input)).not.toContain("ghp_");
  });

  it("redacts GitHub App installation tokens", () => {
    const input = "ghs_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij";
    expect(sanitizeContent(input)).not.toContain("ghs_");
  });

  it("leaves normal text unchanged", () => {
    const input = "This is a normal comment about a pull request.";
    expect(sanitizeContent(input)).toBe(input);
  });
});
