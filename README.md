# LIVORA — Blood Request Coordination Prototype

This project packages the supplied LIVORA dashboard as a deployable Node/Express app and adds an AI request-structuring endpoint.

## Features
- Responsive dashboard based on the supplied HTML.
- Express server and health endpoint (`/api/health`).
- Sample blood-bank directory (`/api/blood-banks`).
- Embedded AI triage panel (`/api/ai/triage`).
- Works without an AI key using a simple rule-based fallback.
- Optional Groq AI integration configured only on the server.

## Important safety and data notes
This is a **prototype**, not a production blood-dispatch or medical system. The dashboard inventory is illustrative sample data and is not live or verified. Do not use it to make clinical decisions or claim that an emergency alert was sent. Contact a licensed hospital/blood bank directly in an emergency. Before real deployment, implement authentication, database persistence, audit logs, rate limiting, consent/privacy controls, verified facility data, and professional/ regulatory review. Do not enter real patient-identifying information into the demo.

## Run locally
Requires Node.js 18+.

```bash
npm install
npm start
```

Open http://localhost:3000

Optional AI:
1. Create a Groq API key from the Groq console.
2. Set `GROQ_API_KEY` in your local environment (never commit it).
3. Restart `npm start`. Without the key, fallback triage still works.

Windows PowerShell example for the current terminal:
```powershell
$env:GROQ_API_KEY="your_key_here"
npm start
```

## Push to GitHub
1. Create a new **public or private** repository on GitHub named `livora` (do not add a README if you already have this project).
2. Extract the ZIP.
3. Open a terminal in the extracted `livora-app` folder.
4. Run:

```bash
git init
git add .
git commit -m "Initial LIVORA web app"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/livora.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username. Do not commit `.env` or API keys.

## Deploy on Render (free web service)
1. Sign in at https://render.com and choose **New + → Web Service**.
2. Connect GitHub and select the `livora` repository.
3. Configure:
   - **Runtime:** Node
   - **Build Command:** `npm install`
   - **Start Command:** `npm start`
   - **Instance:** Free (if offered for your account/region)
4. Under **Environment**, optionally add `GROQ_API_KEY` and `GROQ_MODEL`. Store the secret only in Render environment settings, not in code or GitHub.
5. Click **Create Web Service** and wait for deployment.
6. Open the Render URL. Check `https://YOUR-RENDER-URL.onrender.com/api/health` for `{ "ok": true, ... }`.

Free-tier availability and sleep/usage limits can change. The service may take a little time to wake after inactivity.

## Troubleshooting
- **Build fails:** confirm `package.json` is at the repository root and Node 18+ is available.
- **Page opens but AI fails:** the rule-based fallback should still return a result. Check Render logs and verify the secret if using Groq.
- **Render says port issue:** keep `process.env.PORT || 3000`; do not hardcode a deployment port.
- **GitHub rejects push:** make sure the remote URL is correct and that you are pushing to a repository you own.
