# 🗂️ Vault Conventions

## Folder Structure
| Path | Purpose |
|------|----------|
| `_system/` | Holds all operational assets (hidden from content workflows) |
| `_system/templates/` | Templater templates for new notes (**Ctrl+Alt+M/P/I/T**) |
| `_system/queries/` | DataviewJS and dashboard queries (**Mod+Shift+D/L**) |
| `_system/scripts/` | QuickAdd and helper scripts, run manually via **Ctrl+P** |
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
| **Mod + Alt + M** | New *message* note (`_system/templates/message.md`) |
| **Mod + Alt + P** | New *passage* note (`_system/templates/passage.md`) |
| **Mod + Alt + I** | New *image* note (`_system/templates/image.md`)     |
| **Mod + Alt + T** | New *topic* note (`_system/templates/topic.md`)     |

### 📊 Queries
| Hotkey | Dashboard |
|---------|------------|
| **Mod + Shift + D** | Open *Draft Status* dashboard |
| **Mod + Shift + L** | Open *Link Health* dashboard |

### ⚙️ QuickAdd Macros
| Hotkey | Function |
|---------|-----------|
| **Ctrl + Alt + N** | New note / session (QuickAdd macro) |
| **Ctrl + Alt + C** | Compile prompts |
| **Ctrl + Alt + P** | Process or pipeline step |
| **Alt + Shift + C** | Custom command (QuickAdd UUID choice) |

---

## 📘 Philosophy
Maintain a single `_system/` folder for all internal logic.  
Keep every other folder focused on content, ensuring clean API input and minimal accidental inclusion of non-text assets.  
Scripts are discoverable but not hotkey-bound—invoke them via **Ctrl + P** as needed.