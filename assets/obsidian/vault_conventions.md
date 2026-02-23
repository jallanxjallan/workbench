# 🗂️ Vault Conventions

## Folder Structure
| Path | Purpose |
|------|----------|
| `_common/` | Holds all shared operational assets (symlinked into each vault) |
| `_common/templates/` | Templater templates for new notes (**Ctrl+Alt+M/P/I/T**) |
| `_common/queries/` | DataviewJS query notes (open via QuickAdd picker) |
| `_common/scripts/` | QuickAdd and helper scripts, run manually via **Ctrl+P** |
| *(content folders)* | All other folders contain authored material only |

---

## Hotkey Scheme

### 🔍 Global Navigation
| Hotkey | Action |
|---------|--------|
| **Meta + O** | Quick Open (files, headings) |
| **Meta + F** | Search vault |
| **Meta + /** | Command Palette |
| **Ctrl + Alt + ← / → / ↑** | Back / Forward / Reveal in Explorer |
| **Alt + G** | Open Graph view |
| **Ctrl + E** | Toggle Edit/Preview |

### 🧩 Templates
| Hotkey            | Template                                            |
| ----------------- | --------------------------------------------------- |
| **Mod + Alt + M** | New *message* note (`_common/templates/message.md`) |
| **Mod + Alt + P** | New *passage* note (`_common/templates/passage.md`) |
| **Mod + Alt + I** | New *image* note (`_common/templates/image.md`)     |
| **Mod + Alt + T** | New *topic* note (`_common/templates/topic.md`)     |

### 📊 Queries
| Hotkey | Action |
|---------|--------|
| **Ctrl + Meta + Q** | Open Common Query picker |
| **Ctrl + Meta + S** | Open *Draft Status* query |

### ⚙️ QuickAdd Macros
| Hotkey | Function |
|---------|-----------|
| **Ctrl + Alt + N** | New note / session (QuickAdd macro) |
| **Ctrl + Alt + C** | Compile prompts |
| **Ctrl + Alt + P** | Process or pipeline step |
| **Alt + Shift + C** | Custom command (QuickAdd UUID choice) |

---

## 📘 Philosophy
Maintain a single `_common/` folder for all shared internal logic.  
Keep every other folder focused on content, ensuring clean API input and minimal accidental inclusion of non-text assets.  
Scripts can be invoked via QuickAdd hotkeys or via **Ctrl + P** as needed.
