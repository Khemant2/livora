const express = require("express");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3000;
app.disable("x-powered-by");
app.use(express.json({ limit: "20kb" }));
app.use(express.static(path.join(__dirname, "public")));

const sampleBanks = [
  { id: "bir", name: "Bir Hospital", location: "Mahaboudha, Kathmandu", sampleInventory: { "O+": 12, "B+": 4, "A-": 2 } },
  { id: "red-cross", name: "Nepal Red Cross Blood Bank", location: "Kalimati, Kathmandu", sampleInventory: { "AB+": 8, "A+": 15 } },
  { id: "grande", name: "Grande International Hospital", location: "Dhapasi, Kathmandu", sampleInventory: { "O-": 3, "B-": 1 } }
];

app.get("/api/health", (_req, res) => res.json({ ok: true, app: "LIVORA", mode: "prototype" }));
app.get("/api/blood-banks", (_req, res) => res.json({ disclaimer: "Illustrative sample data only. Not live inventory.", banks: sampleBanks }));

function fallbackTriage(message) {
  const text = message.toLowerCase();
  const groups = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"];
  const bloodGroup = groups.find(g => text.includes(g.toLowerCase())) || "not specified";
  const match = text.match(/\b(\d{1,2})\s*(?:units?|bags?)\b/i);
  const urgent = /urgent|critical|emergency|asap|immediately|trauma/i.test(text);
  const city = /kathmandu/i.test(text) ? "Kathmandu" : "not specified";
  return {
    mode: "rule-based fallback",
    summary: "Request structured using simple text rules; not a medical assessment.",
    bloodGroup,
    units: match ? Number(match[1]) : "not specified",
    location: city,
    priority: urgent ? "urgent - confirm with medical staff" : "not determined",
    nextSteps: [
      "Contact a licensed hospital or blood bank directly to verify stock.",
      "A qualified clinician must confirm the required blood product and compatibility.",
      "Do not rely on this prototype for clinical decisions or emergency dispatch."
    ]
  };
}

app.post("/api/ai/triage", async (req, res) => {
  const message = typeof req.body?.message === "string" ? req.body.message.trim() : "";
  if (!message) return res.status(400).json({ error: "Please provide a message." });
  if (message.length > 4000) return res.status(413).json({ error: "Message is too long (maximum 4,000 characters)." });

  // Optional Groq API (OpenAI-compatible). The API key stays on the server.
  if (process.env.GROQ_API_KEY) {
    try {
      const upstream = await fetch("https://api.groq.com/openai/v1/chat/completions", {
        method: "POST",
        headers: { "Authorization": `Bearer ${process.env.GROQ_API_KEY}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          model: process.env.GROQ_MODEL || "llama-3.3-70b-versatile",
          temperature: 0.2,
          max_tokens: 500,
          messages: [
            { role: "system", content: "You are Livora, a careful assistant for structuring blood-bank requests. Return valid JSON only with keys: summary, bloodGroup, units, location, priority, nextSteps. Extract only information explicitly present; use 'not specified' when missing. Never diagnose, decide transfusion compatibility, promise availability, or claim alerts were sent. State that hospital staff must verify all details and that this is not medical advice." },
            { role: "user", content: message }
          ]
        })
      });
      const payload = await upstream.json();
      if (!upstream.ok) throw new Error(payload.error?.message || "AI provider error");
      const content = payload.choices?.[0]?.message?.content || "";
      let result;
      try { result = JSON.parse(content.replace(/^```json\s*/i, "").replace(/\s*```$/, "")); }
      catch { result = { summary: content, note: "AI response was not valid JSON; review manually." }; }
      return res.json({ result, mode: "groq-ai", disclaimer: "Prototype only; verify with licensed medical staff." });
    } catch (err) {
      console.error("AI provider error:", err.message);
      // Keep the demo usable if provider quota/network is unavailable.
    }
  }
  return res.json({ result: fallbackTriage(message), mode: "fallback", disclaimer: "Prototype only; verify with licensed medical staff." });
});

app.get("*", (req, res, next) => {
  if (req.path.startsWith("/api/")) return res.status(404).json({ error: "API route not found" });
  res.sendFile(path.join(__dirname, "public", "index.html"), err => err && next(err));
});

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(500).json({ error: "Unexpected server error." });
});

app.listen(PORT, "0.0.0.0", () => console.log(`LIVORA listening on port ${PORT}`));
