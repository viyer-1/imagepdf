# Landing Page — Image ↔ PDF Converter

Marketing landing page for the Image ↔ PDF Converter Open Source Project.

## Structure

```
landing-page/
├── index.html          # Main landing page
├── privacy.html        # Privacy policy
└── css/
    └── styles.css      # Shared stylesheet
```

## Serving Locally

```bash
cd landing-page
python3 -m http.server 8099
# Open http://localhost:8099
```

## Design

- **Theme**: Dark "Digital Vault" — deep navy (`#070a14`), emerald accent (`#0fd97e`)
- **Fonts**: Playfair Display (headings) · DM Sans (body) · DM Mono (code/mono) via Google Fonts
- **CSS tokens**: All design values in `:root` custom properties in `styles.css`
- **Scroll reveal**: `IntersectionObserver` + `.reveal` / `.visible` classes
- **Navbar**: Transparent → frosted-glass on scroll (`.scrolled` class)

## Pages

| File | Purpose |
|------|---------|
| `index.html` | Hero, features, privacy, and download links |
| `privacy.html` | Full privacy policy (GDPR/HIPAA/CCPA) |

## Hosting on GitHub Pages

This landing page can be easily hosted on GitHub Pages:

1. Go to your repository settings on GitHub.
2. Select **Pages** from the sidebar.
3. Choose **GitHub Actions** or **Deploy from a branch**.
4. If deploying from a branch, select the `main` branch and the `/landing-page` folder (or keep it as `/` if you move it to a `gh-pages` branch).
