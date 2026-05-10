import { describe, expect, it } from "bun:test";
import { containsTrigger, isHumanActor } from "../src/github/context";

describe("containsTrigger", () => {
  it("detects trigger phrase in comment", () => {
    expect(
      containsTrigger("Hey @cortex-code fix this bug", "@cortex-code"),
    ).toBe(true);
  });

  it("is case insensitive", () => {
    expect(containsTrigger("Hey @Cortex-Code fix this", "@cortex-code")).toBe(
      true,
    );
  });

  it("returns false when trigger is absent", () => {
    expect(containsTrigger("Just a normal comment", "@cortex-code")).toBe(
      false,
    );
  });

  it("handles empty body", () => {
    expect(containsTrigger("", "@cortex-code")).toBe(false);
  });
});

describe("isHumanActor", () => {
  it("returns true for human users", () => {
    expect(isHumanActor("mcastro")).toBe(true);
  });

  it("returns false for bots", () => {
    expect(isHumanActor("dependabot[bot]")).toBe(false);
  });
});
