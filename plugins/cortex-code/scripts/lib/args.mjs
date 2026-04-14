export function parseArgs(argv, config = {}) {
  const valueOptions = new Set(config.valueOptions || []);
  const booleanOptions = new Set(config.booleanOptions || []);
  const aliasMap = config.aliasMap || {};
  const options = {};
  const positionals = [];

  let i = 0;
  while (i < argv.length) {
    const arg = argv[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      if (valueOptions.has(key) && i + 1 < argv.length) {
        options[key] = argv[++i];
      } else {
        options[key] = true;
      }
    } else if (arg.startsWith("-") && arg.length === 2) {
      const alias = arg[1];
      const resolved = aliasMap[alias] || alias;
      if (valueOptions.has(resolved) && i + 1 < argv.length) {
        options[resolved] = argv[++i];
      } else {
        options[resolved] = true;
      }
    } else {
      positionals.push(arg);
    }
    i++;
  }
  return { options, positionals };
}

export function splitRawArgumentString(raw) {
  const tokens = [];
  let current = "";
  let inQuote = null;
  for (const ch of raw) {
    if (inQuote) {
      if (ch === inQuote) { inQuote = null; } else { current += ch; }
    } else if (ch === '"' || ch === "'") {
      inQuote = ch;
    } else if (ch === " " || ch === "\t") {
      if (current) { tokens.push(current); current = ""; }
    } else {
      current += ch;
    }
  }
  if (current) tokens.push(current);
  return tokens;
}
