import fs from "node:fs";
import path from "node:path";

const PROJECT_ROOT = path.resolve(process.cwd(), "..");
const OUT_JSON = path.resolve(process.cwd(), "data", "relations.json");
const OUT_JS = path.resolve(process.cwd(), "data", "relations.js");

const IGNORED_DIRS = new Set([
  ".git",
  ".venv",
  "node_modules",
  "__pycache__",
  ".pytest_cache",
  "dist",
  "build"
]);

const ROOT_GROUPS = ["backend", "frontend", "specs", "migrations", "docs"];

const HEADING_RE = /^(#{1,6})\s+(.+)$/gm;
const MD_LINK_RE = /(?<!\!)\[[^\]]*\]\(([^)]+)\)/gm;
const CHECKLIST_RE = /^\s*[-*]\s+\[( |x|X)\]\s+(.+)$/;

function slugify(input) {
  return input
    .toLowerCase()
    .trim()
    .replace(/<[^>]*>/g, "")
    .replace(/[^a-z0-9\u4e00-\u9fff\s\-_]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

function normalizeMdLink(linkRaw) {
  const trimmed = linkRaw.trim().replace(/^<|>$/g, "");
  if (!trimmed || /^https?:\/\//i.test(trimmed) || /^mailto:/i.test(trimmed)) {
    return null;
  }

  const [filePart, fragment] = trimmed.split("#", 2);
  return {
    filePart,
    fragment: fragment || ""
  };
}

function parseTraceabilityBlocks(content) {
  const traceBlocks = [];
  const fenceRe = /```json\s*([\s\S]*?)```/g;
  let match;
  while ((match = fenceRe.exec(content)) !== null) {
    const body = match[1].trim();
    if (!body) {
      continue;
    }
    let parsed;
    try {
      parsed = JSON.parse(body);
    } catch {
      continue;
    }
    if (!parsed || parsed.type !== "traceability" || typeof parsed.id !== "string") {
      continue;
    }

    const before = content.slice(0, match.index);
    const lineStart = before.split(/\r?\n/).length;
    const bodyLines = match[0].split(/\r?\n/).length;

    traceBlocks.push({
      data: parsed,
      lineStart,
      lineEnd: Math.max(lineStart, lineStart + bodyLines - 1)
    });
  }
  return traceBlocks;
}

function parseHeadingsWithRange(content, relPath, group) {
  const lines = content.split(/\r?\n/);
  const result = [];
  const headingSeen = new Set();

  for (let i = 0; i < lines.length; i += 1) {
    const m = lines[i].match(/^(#{1,6})\s+(.+)$/);
    if (!m) {
      continue;
    }
    const level = m[1].length;
    const title = m[2].trim();
    const slugBase = slugify(title) || `heading-${level}`;
    let slug = slugBase;
    let idx = 2;
    while (headingSeen.has(slug)) {
      slug = `${slugBase}-${idx}`;
      idx += 1;
    }
    headingSeen.add(slug);

    result.push({
      id: `${relPath}#${slug}`,
      label: title,
      path: relPath,
      group,
      type: "heading",
      level,
      anchor: slug,
      parent: relPath,
      lineStart: i + 1,
      lineEnd: i + 1
    });
  }

  for (let i = 0; i < result.length; i += 1) {
    const next = result[i + 1];
    result[i].lineEnd = next ? Math.max(result[i].lineStart, next.lineStart - 1) : lines.length;
  }

  return result;
}

function parseChecklistItems(content, relPath, group) {
  const lines = content.split(/\r?\n/);
  const items = [];
  let index = 1;
  for (let i = 0; i < lines.length; i += 1) {
    const m = lines[i].match(CHECKLIST_RE);
    if (!m) {
      continue;
    }

    const checked = m[1].toLowerCase() === "x";
    const text = m[2].trim();
    const itemId = `${relPath}#check-${index}`;
    index += 1;

    items.push({
      id: itemId,
      label: text.slice(0, 100),
      path: relPath,
      group,
      type: "checklist_item",
      checked,
      parent: relPath,
      lineStart: i + 1,
      lineEnd: i + 1
    });
  }

  return items;
}

function isChecklistPath(relPath) {
  return /checklist/i.test(relPath) || /\/checklists\//i.test(relPath);
}

function isSpecClauseNode(relPath, headingNode) {
  if (!relPath.startsWith("specs/")) {
    return false;
  }
  return /^(\d+(\.\d+)*)\b/.test(headingNode.label) || headingNode.level <= 3;
}

function walk(dir, files = []) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.name.startsWith(".")) {
      continue;
    }

    const abs = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!IGNORED_DIRS.has(entry.name)) {
        walk(abs, files);
      }
      continue;
    }

    const ext = path.extname(entry.name).toLowerCase();
    if ([".py", ".md", ".yaml", ".yml", ".csv"].includes(ext)) {
      files.push(abs);
    }
  }
  return files;
}

function toProjectPath(absPath) {
  return path.relative(PROJECT_ROOT, absPath).split(path.sep).join("/");
}

function getGroup(projectPath) {
  const top = projectPath.split("/")[0];
  if (ROOT_GROUPS.includes(top)) {
    return top;
  }
  return "other";
}

function parsePythonImports(content) {
  const targets = [];
  const importRegex = /^\s*import\s+([a-zA-Z0-9_\. ,]+)$/gm;
  const fromRegex = /^\s*from\s+([a-zA-Z0-9_\.]+)\s+import\s+/gm;

  let match;
  while ((match = importRegex.exec(content)) !== null) {
    const parts = match[1].split(",").map((s) => s.trim().split(" ")[0]);
    for (const part of parts) {
      if (part && !part.startsWith("app") && !part.startsWith("backend")) {
        continue;
      }
      targets.push(part);
    }
  }

  while ((match = fromRegex.exec(content)) !== null) {
    const moduleName = match[1].trim();
    if (moduleName.startsWith("app") || moduleName.startsWith("backend")) {
      targets.push(moduleName);
    }
  }

  return targets;
}

function normalizeImportToPath(moduleName) {
  if (!moduleName) {
    return null;
  }
  const maybePath = moduleName.split(".").join("/");
  if (maybePath.startsWith("app/")) {
    return `backend/${maybePath}.py`;
  }
  if (maybePath.startsWith("backend/")) {
    return `${maybePath}.py`;
  }
  return null;
}

function collect() {
  const sourceFiles = walk(PROJECT_ROOT);

  const docNodes = sourceFiles.map((abs) => {
    const rel = toProjectPath(abs);
    return {
      id: rel,
      label: path.basename(rel),
      path: rel,
      group: getGroup(rel),
      type: "document"
    };
  });

  const nodes = [...docNodes];

  const knownPaths = new Set(nodes.map((n) => n.path));
  const links = [];
  const traceDeclMap = new Map();
  const headingByAnchor = new Map();

  const pushLink = (source, target, type, meta = {}) => {
    links.push({ source, target, type, ...meta });
  };

  for (const abs of sourceFiles) {
    const rel = toProjectPath(abs);
    const content = fs.readFileSync(abs, "utf8");

    if (rel.endsWith(".py")) {
      const imports = parsePythonImports(content);
      for (const imp of imports) {
        const targetPath = normalizeImportToPath(imp);
        if (!targetPath || !knownPaths.has(targetPath)) {
          continue;
        }
        pushLink(rel, targetPath, "import");
      }
      continue;
    }

    if (!rel.endsWith(".md")) {
      continue;
    }

    const group = getGroup(rel);
    const headingNodes = parseHeadingsWithRange(content, rel, group);
    for (const headingNode of headingNodes) {
      nodes.push(headingNode);
      pushLink(rel, headingNode.id, "contains_heading", { level: headingNode.level });
      headingByAnchor.set(headingNode.id, headingNode);

      if (isSpecClauseNode(rel, headingNode)) {
        const clauseNodeId = `clause:${headingNode.id}`;
        nodes.push({
          id: clauseNodeId,
          label: headingNode.label,
          path: rel,
          group,
          type: "spec_clause",
          anchor: headingNode.anchor,
          parent: headingNode.id,
          lineStart: headingNode.lineStart,
          lineEnd: headingNode.lineEnd
        });
        pushLink(headingNode.id, clauseNodeId, "maps_clause");
      }
    }

    if (isChecklistPath(rel)) {
      const checklistNodes = parseChecklistItems(content, rel, group);
      for (const itemNode of checklistNodes) {
        nodes.push(itemNode);
        pushLink(rel, itemNode.id, "contains_checklist_item");
      }
    }

    let mdLinkMatch;
    while ((mdLinkMatch = MD_LINK_RE.exec(content)) !== null) {
      const parsedLink = normalizeMdLink(mdLinkMatch[1]);
      if (!parsedLink) {
        continue;
      }

      const baseDir = path.dirname(rel);
      const targetRel = parsedLink.filePart
        ? path
            .normalize(path.join(baseDir, parsedLink.filePart))
            .split(path.sep)
            .join("/")
        : rel;

      if (!knownPaths.has(targetRel)) {
        continue;
      }

      if (parsedLink.fragment) {
        const targetHeadingId = `${targetRel}#${parsedLink.fragment}`;
        if (headingByAnchor.has(targetHeadingId)) {
          pushLink(rel, targetHeadingId, "md_link_anchor");
          const maybeClauseId = `clause:${targetHeadingId}`;
          pushLink(rel, maybeClauseId, "references_clause");
        } else {
          pushLink(rel, targetHeadingId, "md_link", { unresolvedAnchor: true });
        }
      } else {
        pushLink(rel, targetRel, "md_link");
      }
    }

    const traceBlocks = parseTraceabilityBlocks(content);
    for (const block of traceBlocks) {
      const traceId = block.data.id.trim();
      const traceNodeId = `trace:${traceId}`;
      if (!traceDeclMap.has(traceId)) {
        traceDeclMap.set(traceId, rel);
        nodes.push({
          id: traceNodeId,
          label: traceId,
          path: rel,
          group: getGroup(rel),
          type: "trace_id",
          traceId,
          parent: rel,
          lineStart: block.lineStart,
          lineEnd: block.lineEnd
        });
      }

      pushLink(rel, traceNodeId, "declares_trace");

      const walkRefs = (sectionName, direction) => {
        const arr = Array.isArray(block.data[sectionName]) ? block.data[sectionName] : [];
        for (const item of arr) {
          const ids = Array.isArray(item?.ids) ? item.ids : [];
          for (const rawId of ids) {
            if (typeof rawId !== "string" || !rawId.trim()) {
              continue;
            }
            const refId = rawId.trim();
            const refNodeId = `trace:${refId}`;
            pushLink(traceNodeId, refNodeId, direction, {
              linkType: item?.link_type || "",
              requirement: item?.requirement || ""
            });
          }
        }
      };

      walkRefs("upstream", "trace_upstream");
      walkRefs("downstream", "trace_downstream");
    }
  }

  const nodeIdSet = new Set(nodes.map((n) => n.id));
  const filteredLinks = links.filter((link) => nodeIdSet.has(link.source));

  const summary = {
    generatedAt: new Date().toISOString(),
    nodeCount: nodes.length,
    linkCount: filteredLinks.length,
    groupCount: [...new Set(nodes.map((n) => n.group))].length,
    documentCount: nodes.filter((n) => n.type === "document").length,
    headingCount: nodes.filter((n) => n.type === "heading").length,
    traceCount: nodes.filter((n) => n.type === "trace_id").length,
    clauseCount: nodes.filter((n) => n.type === "spec_clause").length,
    checklistCount: nodes.filter((n) => n.type === "checklist_item").length
  };

  return { summary, nodes, links: filteredLinks };
}

function save(data) {
  fs.mkdirSync(path.dirname(OUT_JSON), { recursive: true });
  fs.writeFileSync(OUT_JSON, `${JSON.stringify(data, null, 2)}\n`, "utf8");
  fs.writeFileSync(
    OUT_JS,
    `window.RELATION_DATA = ${JSON.stringify(data, null, 2)};\n`,
    "utf8"
  );
}

const payload = collect();
save(payload);

console.log(
  `Generated relation data: ${payload.summary.nodeCount} nodes, ${payload.summary.linkCount} links`
);