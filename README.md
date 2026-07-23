# Visionet — Company Profile Website

A lightweight, three-page company profile website for **Visionet**, a technology
and digital services company.

## Pages

| Page | File | Purpose |
|------|------|---------|
| Landing | [`index.html`](index.html) | Hero, services overview, stats, and call to action |
| About | [`about.html`](about.html) | Company story, mission/vision, and values |
| Contact | [`contact.html`](contact.html) | Contact form and company contact details |

All pages share a single stylesheet, [`styles.css`](styles.css).

## Tech

Plain, dependency-free **static HTML + CSS**. No build step, no framework, no
package manager. This keeps the site fast, easy to host anywhere, and free of
vendored dependencies or generated artifacts.

- Responsive layout (mobile nav is CSS-only, no JavaScript)
- System font stack (no web-font downloads)
- Accessible landmarks, labelled form fields, and focus styles

## Running locally

It's a static site — just open `index.html` in a browser, or serve the folder:

```bash
# Python 3
python3 -m http.server 8000
# then open http://localhost:8000
```

## Validation

Because the site is dependency-free with no build step, structural correctness is
guarded by a standard-library Python script instead of a JS test runner. It must
pass before shipping any change:

```bash
python3 validate.py
```

It verifies that all three pages and the shared stylesheet exist, that every page
links `styles.css` and cross-links to all three pages, that each page marks its own
nav link active, that the **Visionet** brand appears in every `<title>` and brand
mark, and that the contact form exposes the required labelled fields (name, email,
subject, message). It exits `0` on success and `1` (listing each failure) otherwise.

## Notes

- The contact form uses a `mailto:` action because there is no backend in this
  repository. When a form-handling endpoint is available, replace the `action`
  on the `<form>` in `contact.html`.
- Contact details (email, phone, address) are placeholders — update them with
  real values before going live.
