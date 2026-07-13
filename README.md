# Company Profile

A plain, dependency-free static website with three pages:

- **Company Profile** — `index.html`
- **Contact Us** — `contact.html`
- **Gallery** — `gallery.html`

Shared styling lives in `assets/css/styles.css`; gallery placeholder images
are in `assets/img/`.

## View the site

Open `index.html` directly in a browser, or serve the folder with any static
web server, for example:

```bash
python3 -m http.server 8080
# then open http://localhost:8080
```

## Test

Structural tests (no external dependencies — Node's built-in test runner)
verify that all three pages exist, shared navigation links resolve, the shared
stylesheet is referenced, and gallery image references are valid:

```bash
npm test
```
