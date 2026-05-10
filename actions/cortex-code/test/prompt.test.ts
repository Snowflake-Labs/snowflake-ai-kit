import { describe, expect, it } from "bun:test";
import { extractUserRequest } from "../src/create-prompt";

describe("extractUserRequest", () => {
  it("extracts text after trigger phrase", () => {
    const result = extractUserRequest(
      "@cortex-code fix the null pointer exception in auth.ts",
      "@cortex-code",
    );
    expect(result).toBe("fix the null pointer exception in auth.ts");
  });

  it("handles trigger at start of body", () => {
    const result = extractUserRequest(
      "@cortex-code refactor this",
      "@cortex-code",
    );
    expect(result).toBe("refactor this");
  });

  it("returns full body when trigger not found", () => {
    const result = extractUserRequest("Please fix this bug", "@cortex-code");
    expect(result).toBe("Please fix this bug");
  });

  it("handles trigger with nothing after it", () => {
    const result = extractUserRequest("@cortex-code", "@cortex-code");
    // Falls back to full body since nothing after trigger
    expect(result).toBe("@cortex-code");
  });

  it("is case insensitive for trigger detection", () => {
    const result = extractUserRequest(
      "@Cortex-Code add tests for utils",
      "@cortex-code",
    );
    expect(result).toBe("add tests for utils");
  });
});
