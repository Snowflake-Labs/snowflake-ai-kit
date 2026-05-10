import * as core from "@actions/core";

export interface RetryOptions {
  maxAttempts?: number;
  delayMs?: number;
  backoffMultiplier?: number;
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  label: string,
  options: RetryOptions = {},
): Promise<T> {
  const { maxAttempts = 3, backoffMultiplier = 2 } = options;
  let { delayMs = 2000 } = options;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : String(error);
      if (attempt === maxAttempts) {
        core.error(`${label} failed after ${maxAttempts} attempts: ${errMsg}`);
        throw error;
      }
      core.warning(
        `${label} attempt ${attempt}/${maxAttempts} failed: ${errMsg}. Retrying in ${delayMs}ms...`,
      );
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      delayMs *= backoffMultiplier;
    }
  }
  throw new Error("Unreachable");
}
