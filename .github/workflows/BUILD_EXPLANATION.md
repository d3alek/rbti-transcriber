# Build Process Explanation

## Current Workflow

The workflow builds react-transcript-editor **once** - directly as a browser bundle:

### Browser Bundle Build (`build-browser-bundle.js`)
- **Output**: `gh-pages-output/bundles/react-transcript-editor-bundle.js`
- **Format**: UMD bundle (`libraryTarget: 'umd'`)
- **Purpose**: For direct use in browser via `<script>` tags
- **Source**: Builds directly from source files (`packages/components/transcript-editor/`)

## Why Not Use `dist/` Files?

The `dist/` files (from `npm run build:component`) are **CommonJS modules** designed for npm:
```javascript
// Node.js/npm usage
const TranscriptEditor = require('@bbc/react-transcript-editor');
```

But for **browser HTML files**, we need **UMD format**:
```html
<!-- Browser usage -->
<script src="react-transcript-editor-bundle.js"></script>
<script>
  const { TranscriptEditor } = ReactTranscriptEditor;
</script>
```

Since we only need the browser bundle for GitHub Pages, we skip the component build and build the UMD bundle directly from source.

## Benefits

- ✅ **Faster builds** - Only one build step instead of two
- ✅ **Simpler workflow** - One purpose, one build
- ✅ **Direct from source** - No intermediate CommonJS build needed

