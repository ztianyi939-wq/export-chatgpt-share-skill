---
name: export-chatgpt-share
description: Export ChatGPT shared conversation links to Obsidian-ready Markdown notes. Use when the user provides a chatgpt.com/share URL, asks to save a ChatGPT conversation as Markdown, wants a reproducible ChatGPT-to-Obsidian workflow, or wants a local archive of a shared ChatGPT conversation.
---

# Export ChatGPT Share

## Workflow

1. Accept one ChatGPT share URL from the user.
2. Prefer the bundled script `scripts/export_chatgpt_share.py` for deterministic export.
3. Save output to the current workspace unless the user provides an Obsidian vault path or another target directory.
4. Default to exporting only visible conversation text: user messages and assistant text responses.
5. Do not include internal `system`, `tool`, `thoughts`, `reasoning_recap`, `model_editable_context`, or code/tool nodes unless the user explicitly asks for a full diagnostic export.
6. If the user asks about formulas, MathType, LaTeX, or Obsidian math rendering, run the script with `--math-delimiters dollar` so `\(...\)` becomes `$...$` and `\[...\]` becomes `$$...$$`.
7. After export, verify that the Markdown file exists, has frontmatter, includes the source URL, and contains readable `## User` / `## Assistant` sections.

## Script Usage

Run from any writable workspace:

```bash
python /path/to/export-chatgpt-share/scripts/export_chatgpt_share.py "<share-url>"
```

Useful options:

```bash
python /path/to/export-chatgpt-share/scripts/export_chatgpt_share.py "<share-url>" --out notes
python /path/to/export-chatgpt-share/scripts/export_chatgpt_share.py "<share-url>" --out "/path/to/ObsidianVault/ChatGPT" --filename "Conversation.md"
python /path/to/export-chatgpt-share/scripts/export_chatgpt_share.py "<share-url>" --out notes --math-delimiters dollar
```

The script uses only the Python standard library. It prints the absolute path of the generated Markdown file on success and prints a concise error on failure.

## Output Contract

The Markdown note must include YAML frontmatter:

- `title`
- `source`
- `share_id`
- `created`
- `updated`
- `model`
- `exported_at`

The body must preserve the original Markdown text from visible messages and separate conversation turns with `## User` and `## Assistant` headings.

When `--math-delimiters dollar` is used, the note must use Obsidian-friendly `$...$` inline math and `$$...$$` display math. This is the preferred mode for MathType-style formula review.

## Formula Handling

When the user mentions formulas, MathType, LaTeX, equations, or asks whether math can display correctly in Obsidian:

1. Run the exporter with `--math-delimiters dollar`.
2. Treat `$...$` as the target inline MathType/MathJax style.
3. Treat `$$...$$` as the target block MathType/MathJax style.
4. Preserve formula content rather than rewriting the math semantically.
5. Let the script normalize common unit spacing from `\ \mathrm{...}` to `\,\mathrm{...}`.
6. Do not alter formulas inside fenced code blocks.
7. After export, report the number of inline and block formulas found when practical.

## Validation

After running the exporter:

1. Confirm the file path printed by the script exists.
2. Inspect the first lines for frontmatter and the original `source` URL.
3. Search the note for internal node labels such as `reasoning_recap`, `model_editable_context`, and `execution_output`; these should not appear unless they are ordinary words inside the user's visible conversation.
4. For formula-focused exports, confirm there are no remaining raw `\(...\)` or `\[...\]` delimiters, `$$` block delimiters are paired, inline `$` delimiters are paired after excluding `$$...$$` blocks, and unit spacing does not contain raw `\ \mathrm`.
5. If network access is blocked or the share page returns 403, rerun the same script with the normal Codex escalation flow for network access.

## Obsidian Import

Obsidian imports Markdown by file placement. If the user asks how to import, tell them to copy or export the generated `.md` file into their vault folder. For repeat use, pass the vault subfolder directly with `--out`.
