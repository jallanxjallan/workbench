```dataviewjs
const scriptPath = "_common/scripts/compile_batch_query.js";

try {
  const source = await app.vault.adapter.read(scriptPath);
  await eval(source);
} catch (error) {
  const message = `Compile Batch failed to load ${scriptPath}: ${error?.message || error}`;
  dv.paragraph(message);
  console.error(message, error);
}
```
