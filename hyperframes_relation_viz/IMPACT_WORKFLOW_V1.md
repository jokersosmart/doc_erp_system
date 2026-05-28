# Cross-Document Audit Impact Workflow v1

## Goal

When a paragraph or file is changed, automatically identify related evidence paragraphs/files and mark them as `SUSPECT` candidates for reviewer confirmation.

## Human-Machine Collaboration Model

1. Human edits source paragraph/document.
2. Tool detects changed files from git diff.
3. Tool resolves relation graph and outputs impacted nodes.
4. AI proposes text updates for suspect nodes.
5. Human reviews and accepts/rejects each suggestion.
6. Final audit evidence is recorded with clause/checklist references.

## Data Contracts

### Node types

- `document`: file-level node (`*.md`, `*.py`, `*.yaml`, `*.csv`)
- `heading`: markdown heading-level paragraph anchor node
- `trace_id`: traceability ID node from markdown JSON blocks

### Link types

- `import`: Python import dependency
- `md_link`: markdown hyperlink dependency
- `contains_heading`: document contains heading
- `declares_trace`: document declares traceability id
- `trace_upstream`: traceability upstream relation
- `trace_downstream`: traceability downstream relation

## Status Rules

- `changed`: directly changed node from current diff
- `suspect_paragraph`: impacted heading paragraph node
- `suspect_trace`: impacted traceability node
- `suspect_clause`: impacted spec clause node
- `suspect_checklist`: impacted checklist item node
- `suspect_document`: impacted document node

## Implemented in this repository

1. Git-hunk-aware markdown seed detection (`seedMode = git-hunk-paragraph-aware`)
2. Spec clause nodes (from `specs/**` headings)
3. Checklist item nodes (from markdown checkbox lines)
4. Navigation payload on each impacted item:
	- `navigation.from`
	- `navigation.to`
	- `navigation.returnTo`
	- `navigation.pathIds`

## Execution Commands

From `hyperframes_relation_viz`:

```powershell
npm run build:data
npm run analyze:impact
```

Optional manual changed-file input:

```powershell
node .\scripts\analyze-impact.mjs --changed specs/002-doce-erp-dms/spec.md,backend/app/services/dependency_engine.py --depth 2
```

## Output Files

- `data/relations.json`: full relation graph
- `data/impact-report.json`: impacted and suspect candidate list

## Next Increment (v1.1)

1. Add AI suggestion batch export for reviewer queue.
2. Add confidence/risk scoring for each suspect item.
3. Add clause/checklist reference links from non-spec docs via explicit tags.
4. Add reviewer decision merge utility (`approve`, `reject`, `waive`).