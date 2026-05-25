# Export ChatGPT Share Skill

Export ChatGPT shared conversation links into Obsidian-ready Markdown notes.

This skill is useful when you want Codex or another compatible agent to archive a `chatgpt.com/share/...` conversation as a local Markdown file that can be placed directly inside an Obsidian vault.

## What it helps with

- Export ChatGPT shared conversations from public share links.
- Preserve readable user/assistant conversation turns as Markdown.
- Add YAML frontmatter with title, source URL, share ID, model, and timestamps.
- Save notes into the current workspace or directly into an Obsidian vault folder.
- Skip internal ChatGPT nodes such as system messages, tool calls, reasoning recaps, and execution output.
- Convert LaTeX delimiters to Obsidian-friendly MathJax/MathType style when requested.

## Formula support

For formula-heavy conversations, use the math delimiter option:

```powershell
python E:\Codex\.codex\skills\export-chatgpt-share\scripts\export_chatgpt_share.py "https://chatgpt.com/share/..." --out notes --math-delimiters dollar
```

This converts:

- `\(...\)` to `$...$`
- `\[...\]` to `$$...$$`
- `\ \mathrm{...}` to `\,\mathrm{...}`

The conversion avoids fenced code blocks so code examples remain unchanged.

## Install

Install with the Codex skill installer:

```powershell
python E:\Codex\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --url https://github.com/ztianyi939-wq/export-chatgpt-share-skill --path . --name export-chatgpt-share --dest E:\Codex\.codex\skills
```

Or manually download this repository and place it at:

```text
E:\Codex\.codex\skills\export-chatgpt-share
```

The final structure should contain:

```text
E:\Codex\.codex\skills\export-chatgpt-share\SKILL.md
E:\Codex\.codex\skills\export-chatgpt-share\scripts\export_chatgpt_share.py
```

Restart Codex after installing.

## Usage

Example prompts:

```text
Use $export-chatgpt-share to export this ChatGPT share link into an Obsidian-ready Markdown note: https://chatgpt.com/share/...
```

```text
使用 $export-chatgpt-share 把这个链接导出为 Obsidian Markdown: https://chatgpt.com/share/...
```

```text
Use $export-chatgpt-share to export this formula-heavy ChatGPT conversation for Obsidian, and make sure equations render correctly.
```

## Direct script usage

Run the bundled script directly:

```powershell
python E:\Codex\.codex\skills\export-chatgpt-share\scripts\export_chatgpt_share.py "https://chatgpt.com/share/..." --out notes
```

Optional arguments:

```powershell
python E:\Codex\.codex\skills\export-chatgpt-share\scripts\export_chatgpt_share.py "https://chatgpt.com/share/..." --out "D:\ObsidianVault\ChatGPT"
python E:\Codex\.codex\skills\export-chatgpt-share\scripts\export_chatgpt_share.py "https://chatgpt.com/share/..." --out notes --filename "Conversation.md"
python E:\Codex\.codex\skills\export-chatgpt-share\scripts\export_chatgpt_share.py "https://chatgpt.com/share/..." --out notes --math-delimiters dollar
```

On success, the script prints the absolute path of the generated Markdown file.

## Output

Generated notes include YAML frontmatter:

- `title`
- `source`
- `share_id`
- `created`
- `updated`
- `model`
- `exported_at`

The body uses `## User` and `## Assistant` headings and preserves the visible Markdown content from the shared conversation.

## Obsidian import

Obsidian reads Markdown files directly from a vault folder. To import an exported conversation, place the generated `.md` file anywhere inside your vault, for example:

```text
D:\ObsidianVault\ChatGPT\Conversation.md
```

For repeated use, pass the vault subfolder directly with `--out`.

## Attribution

README structure inspired by [ztianyi939-wq/obsidian-markdown-skill](https://github.com/ztianyi939-wq/obsidian-markdown-skill).
