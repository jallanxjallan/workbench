```dataviewjs

// Image Passages Browser — thumbnails + filesize
// Folder + filters
const FOLDER = "passages";           // your flat folder
const ONLY_TOGGLED = false;          // true => require image_show: true
const THUMB_MAX_W = 160;             // px

// helpers
const human = (n) => n == null ? "—"
  : n >= 1<<30 ? (n/(1<<30)).toFixed(2)+" GB"
  : n >= 1<<20 ? (n/(1<<20)).toFixed(1)+" MB"
  : n >= 1<<10 ? (n/(1<<10)).toFixed(0)+" KB"
  : n + " B";

const isImagePassage = (p) =>
  !!p.image && (String(p.status||"") === "🖼️" || (Array.isArray(p.tags) && p.tags.includes("image")));

const pages = dv.pages(`"${FOLDER}"`)
  .where(p => isImagePassage(p) && (!ONLY_TOGGLED || p.image_show === true))
  .sort(p => p.file.mtime, "desc");

if (!pages || pages.length === 0) {
  dv.paragraph("No image-type passages found.");
  return;
}

const rows = [];
for (const p of pages) {
  // thumbnail cell
  const thumb = document.createElement("img");
  thumb.src = p.image;
  thumb.style.maxWidth = THUMB_MAX_W + "px";
  thumb.style.display = "block";
  thumb.style.borderRadius = "8px";

  // try to stat the image file if it’s a vault path
  let sizeText = "—";
  try {
    const isUrl = /^https?:\/\//i.test(p.image);
    if (!isUrl) {
      // Resolve relative to vault root (works if p.image is a normal vault path)
      const stat = await app.vault.adapter.stat(p.image);
      if (stat && typeof stat.size === "number") sizeText = human(stat.size);
    }
  } catch (e) {
    sizeText = "—";
  }

  rows.push([
    thumb,                         // Preview
    p.file.link,                   // Title/link (note name)
    p.image,                       // Image path/URL
    sizeText,                      // Filesize
    dv.date(p.file.mtime)          // Updated
  ]);
}

dv.table(["Preview", "Passage", "Image", "Filesize", "Updated"], rows);
```