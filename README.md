# LIVORA — Find Blood Faster

LIVORA is a responsive front-end prototype for a blood-request and donor-connection platform. It is based on the supplied dashboard HTML.

## Run locally

1. Extract this project.
2. Open `index.html` in a modern browser.

No build tools or dependencies are required for the static demo. Google Fonts require an internet connection; system fonts are used as fallbacks.

## Current status — read before deployment

This repository currently contains a **front-end prototype**, not a production healthcare system.

- Blood-bank/hospital cards and statistics are demo content.
- Search results and emergency broadcast interactions are simulated in the browser.
- Sign-in, account creation, donor registration, and contact forms currently show demo success states; they do not create accounts or send data to a server.
- There is no backend, database, real-time donor notification, authentication, AI service, or verified inventory integration.

Do not use demo inventory or demo contacts to make medical decisions. Before real-world use, connect a secure backend, validate donor and facility data, implement authentication/authorization, protect personal and health information, add audit logs and abuse controls, and have the workflow reviewed by qualified healthcare and security professionals. Never represent sample data as live blood availability.

## Publish with GitHub Pages

1. Create a new repository on GitHub, for example `livora`.
2. Upload `index.html`, `README.md`, `.gitignore`, and optionally the `prototypes` folder, or push them with Git.
3. In the repository, open **Settings → Pages**.
4. Under **Build and deployment**, choose **Deploy from a branch**.
5. Select your main branch and the root (`/`) folder, then save.
6. Wait for the deployment URL to appear in the Pages section.

## Push with Git

Run these commands in a terminal opened inside the extracted project folder (replace the URL with your repository URL):

```bash
git init
git add .
git commit -m "Add LIVORA frontend prototype"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/livora.git
git push -u origin main
```

If Git says `remote origin already exists`, update it with:

```bash
git remote set-url origin https://github.com/YOUR-USERNAME/livora.git
```

## Project structure

```text
livora-github-project/
├── index.html
├── README.md
├── .gitignore
└── prototypes/
    └── DASHBOARD-PLATE.html
```
