import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const WORKDIR = process.cwd();
const PROJECT_ROOT = path.resolve(WORKDIR, "..");
const RELATIONS_PATH = path.join(WORKDIR, "data", "relations.json");
const OUT_PATH = path.join(WORKDIR, "data", "impact-report.json");
const OUT_JS_PATH = path.join(WORKDIR, "data", "impact-report.js");

function parseArgs(argv) {
  const args = { changed: [], depth: 2 };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === "--changed" && argv[i + 1]) {
      args.changed = argv[i + 1]
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((p) => p.split(path.sep).join("/"));
      i += 1;
      continue;
    }
    if (token === "--depth" && argv[i + 1]) {
      const parsed = Number.parseInt(argv[i + 1], 10);
      if (Number.isFinite(parsed) && parsed > 0 && parsed <= 6) {
        args.depth = parsed;
      }
      i += 1;
    }
  }
  return args;
}

function autoDetectChangedFiles() {
  try {
    const stdout = execSync("git diff --name-only --relative HEAD", {
      cwd: PROJECT_ROOT,
      stdio: ["ignore", "pipe", "ignore"],
      encoding: "utf8"
    });
    return stdout
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((p) => p.split(path.sep).join("/"));
  } catch {
    return [];
  }
}

function autoDetectChangedLineMap() {
  const lineMap = new Map();
  let changedFiles = [];
  try {
    const stdout = execSync("git diff --unified=0 --relative HEAD", {
      cwd: PROJECT_ROOT,
      stdio: ["ignore", "pipe", "ignore"],
      encoding: "utf8"
    });

    const lines = stdout.split(/\r?\n/);
    let currentFile = null;

    for (const line of lines) {
      if (line.startsWith("+++ b/")) {
        currentFile = line
          .slice(6)
          .trim()
          .split(path.sep)
          .join("/");
        changedFiles.push(currentFile);
        if (!lineMap.has(currentFile)) {
          lineMap.set(currentFile, []);
        }
        continue;
      }

      if (!currentFile || !line.startsWith("@@")) {
        continue;
      }

      const m = line.match(/@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@/);
      if (!m) {
        continue;
      }

      const start = Number.parseInt(m[1], 10);
      const len = m[2] ? Number.parseInt(m[2], 10) : 1;
      const end = len === 0 ? start : start + Math.max(0, len - 1);
      lineMap.get(currentFile).push({ start, end });
    }
  } catch {
    return { changedFiles: [], lineMap: new Map() };
  }

  changedFiles = [...new Set(changedFiles)].map((p) => p.split(path.sep).join("/"));
  return { changedFiles, lineMap };
}

function loadRelations() {
  if (!fs.existsSync(RELATIONS_PATH)) {
    throw new Error("relations.json not found. Run npm run build:data first.");
  }
  return JSON.parse(fs.readFileSync(RELATIONS_PATH, "utf8"));
}

function buildIndex(data) {
  const nodeMap = new Map(data.nodes.map((n) => [n.id, n]));
  const outAdj = new Map();
  const inAdj = new Map();

  for (const link of data.links) {
    if (!nodeMap.has(link.source)) {
      continue;
    }
    if (!outAdj.has(link.source)) {
      outAdj.set(link.source, []);
    }
    outAdj.get(link.source).push(link);

    if (!inAdj.has(link.target)) {
      inAdj.set(link.target, []);
    }
    inAdj.get(link.target).push(link);
  }

  return { nodeMap, outAdj, inAdj };
}

function lineInRange(line, node) {
  const start = Number.isFinite(node?.lineStart) ? node.lineStart : null;
  const end = Number.isFinite(node?.lineEnd) ? node.lineEnd : null;
  if (!start || !end) {
    return false;
  }
  return line >= start && line <= end;
}

function pickHeadingSeedForRange(nodes, range) {
  let best = null;
  for (const node of nodes) {
    if (!lineInRange(range.start, node) && !lineInRange(range.end, node)) {
      continue;
    }
    if (!best) {
      best = node;
      continue;
    }
    const currentSpan = (best.lineEnd || best.lineStart) - (best.lineStart || 0);
    const candidateSpan = (node.lineEnd || node.lineStart) - (node.lineStart || 0);
    if (candidateSpan <= currentSpan) {
      best = node;
    }
  }
  return best;
}

function resolveSeeds(changedFiles, changedLineMap, nodeMap) {
  const seeds = new Set();
  const docs = [...nodeMap.values()].filter((n) => n.type === "document" || !n.type);
  const byPath = new Map(docs.map((n) => [n.path, n.id]));
  const byPathHeadings = new Map();

  for (const node of nodeMap.values()) {
    if (node.type !== "heading") {
      continue;
    }
    if (!byPathHeadings.has(node.path)) {
      byPathHeadings.set(node.path, []);
    }
    byPathHeadings.get(node.path).push(node);
  }

  for (const filePath of changedFiles) {
    const normalized = filePath.split(path.sep).join("/");
    let seededByRange = false;

    if (normalized.endsWith(".md") && changedLineMap.has(normalized)) {
      const headingNodes = byPathHeadings.get(normalized) || [];
      for (const range of changedLineMap.get(normalized)) {
        const selected = pickHeadingSeedForRange(headingNodes, range);
        if (selected) {
          seeds.add(selected.id);
          seededByRange = true;
        }
      }
    }

    if (byPath.has(normalized)) {
      if (!seededByRange || !normalized.endsWith(".md")) {
        seeds.add(byPath.get(normalized));
      }
    }

    for (const node of nodeMap.values()) {
      if (node.type === "trace_id" && node.parent === normalized) {
        seeds.add(node.id);
      }
    }
  }

  return [...seeds];
}

function bfsImpact(seeds, outAdj, inAdj, depth, nodeMap) {
  const queue = seeds.map((id) => ({ id, d: 0 }));
  const visited = new Map();
  const previous = new Map();

  for (const id of seeds) {
    visited.set(id, 0);
    previous.set(id, null);
  }

  while (queue.length) {
    const cur = queue.shift();
    if (cur.d >= depth) {
      continue;
    }

    const nextLinks = [...(outAdj.get(cur.id) || []), ...(inAdj.get(cur.id) || [])];
    for (const link of nextLinks) {
      const nextId = link.source === cur.id ? link.target : link.source;
      if (!nodeMap.has(nextId)) {
        continue;
      }
      const nd = cur.d + 1;
      if (!visited.has(nextId) || visited.get(nextId) > nd) {
        visited.set(nextId, nd);
        previous.set(nextId, cur.id);
        queue.push({ id: nextId, d: nd });
      }
    }
  }

  return { visited, previous };
}

function classifySuspect(node, isSeed) {
  if (isSeed) {
    return "changed";
  }
  if (node.type === "trace_id") {
    return "suspect_trace";
  }
  if (node.type === "heading") {
    return "suspect_paragraph";
  }
  if (node.type === "spec_clause") {
    return "suspect_clause";
  }
  if (node.type === "checklist_item") {
    return "suspect_checklist";
  }
  return "suspect_document";
}

function materializePath(nodeId, previous) {
  const pathIds = [];
  let cur = nodeId;
  while (cur) {
    pathIds.push(cur);
    cur = previous.get(cur) || null;
  }
  return pathIds.reverse();
}

function buildNavigation(nodeId, previous, nodeMap, changedSeedSet) {
  const pathIds = materializePath(nodeId, previous);
  const fromChanged = pathIds.find((id) => changedSeedSet.has(id));
  const hops = pathIds.length > 1 ? pathIds.slice(1).map((id) => nodeMap.get(id)?.label || id) : [];
  return {
    from: fromChanged || pathIds[0] || null,
    to: nodeId,
    returnTo: fromChanged || pathIds[0] || null,
    hops,
    pathIds
  };
}

function createReport(data, changedFiles, depth) {
  const { nodeMap, outAdj, inAdj } = buildIndex(data);
  const { lineMap } = autoDetectChangedLineMap();
  const seeds = resolveSeeds(changedFiles, lineMap, nodeMap);
  const { visited: distances, previous } = bfsImpact(seeds, outAdj, inAdj, depth, nodeMap);
  const seedSet = new Set(seeds);

  const items = [...distances.entries()]
    .map(([id, d]) => {
      const node = nodeMap.get(id);
      if (!node) {
        return null;
      }
      return {
        id,
        label: node.label,
        path: node.path,
        type: node.type || "document",
        distance: d,
        status: classifySuspect(node, seedSet.has(id)),
        navigation: buildNavigation(id, previous, nodeMap, seedSet),
        reason: seedSet.has(id)
          ? "Directly changed in current diff"
          : "Connected via relation graph within selected depth"
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.distance - b.distance || a.path.localeCompare(b.path));

  const suspectItems = items.filter((i) => i.status !== "changed");

  return {
    generatedAt: new Date().toISOString(),
    input: {
      changedFiles,
      depth,
      seedCount: seeds.length,
      seedMode: "git-hunk-paragraph-aware"
    },
    summary: {
      totalImpacted: items.length,
      suspectCount: suspectItems.length,
      changedCount: items.length - suspectItems.length
    },
    items,
    guidance: [
      "Review suspect_paragraph first for direct content alignment impact.",
      "Review suspect_trace for traceability consistency and link completeness.",
      "After review completion, clear SUSPECT status with reviewer and timestamp evidence."
    ]
  };
}

function save(report) {
  fs.writeFileSync(OUT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  fs.writeFileSync(
    OUT_JS_PATH,
    `window.IMPACT_REPORT = ${JSON.stringify(report, null, 2)};\n`,
    "utf8"
  );
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const changedFiles = args.changed.length ? args.changed : autoDetectChangedFiles();
  if (!changedFiles.length) {
    throw new Error(
      "No changed files detected. Pass --changed fileA.md,fileB.py or create a git diff first."
    );
  }
  const data = loadRelations();
  const report = createReport(data, changedFiles, args.depth);
  save(report);
  console.log(
    `Impact report generated: ${report.summary.totalImpacted} impacted, ${report.summary.suspectCount} suspect items`
  );
  console.log(`Saved to: ${path.relative(WORKDIR, OUT_PATH)}`);
}

main();