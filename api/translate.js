// Vercel Serverless Function: แปลอังกฤษ -> ไทย (Google Translate ฟรี ไม่ต้องมี key) ฝั่งเซิร์ฟเวอร์ จึงไม่ติด CORS
module.exports = async (req, res) => {
  const q = String((req.query && req.query.q) || "").slice(0, 1500);
  if (!q) return res.status(400).json({ error: "missing q" });
  try {
    const r = await fetch("https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=th&dt=t&q=" + encodeURIComponent(q));
    const j = await r.json();
    const text = j[0].map((s) => s[0]).join("");
    res.setHeader("Cache-Control", "s-maxage=86400, stale-while-revalidate");
    return res.status(200).json({ text });
  } catch (e) {
    return res.status(502).json({ error: "translate failed" });
  }
};
