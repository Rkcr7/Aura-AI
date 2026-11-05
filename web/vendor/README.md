# Bundled third-party assets

The UI loads these from here instead of a CDN, so the window paints without
waiting on the network and keeps working offline or on networks that block
Google Fonts or cdnjs. Files are byte-for-byte the published versions
(`.gitattributes` keeps Git from touching their line endings).

| Folder | What | Version | Source | License |
|---|---|---|---|---|
| `inter/` | Inter variable font, 7 WOFF2 subsets + `inter.css` | Google Fonts v20 | `fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap`, font URLs pointed at the local files | SIL OFL 1.1 (`inter/OFL.txt`) |
| `prism/` | Prism core, autoloader, okaidia theme and all 298 language components | 1.29.0 | npm `prismjs@1.29.0`, matches the cdnjs SHA-512 hashes | MIT (`prism/LICENSE`) |
| `katex/` | KaTeX JS, CSS and WOFF2 fonts | 0.19.0 | npm `katex@0.19.0` (`dist/`), matches the cdnjs SHA-512 hashes | MIT (`katex/LICENSE`) |

## Updating

- **KaTeX**: bump `katex` in `package.json` (the tests use it too), `npm install`,
  then copy `node_modules/katex/dist/katex.min.{js,css}` and `dist/fonts/*.woff2` here.
- **Prism**: `npm pack prismjs@<version>`, then copy `components/*.min.js`,
  `plugins/autoloader/prism-autoloader.min.js` and `themes/prism-okaidia.min.css`.
  The autoloader finds `components/` relative to its own path, so keep the layout.
- **Inter**: fetch the Google Fonts CSS URL above with a current browser user agent
  (that is what gets WOFF2), download the font files it lists, and point `inter.css` at them.
