export async function onRequestGet({ request }) {
  const q = (new URL(request.url).searchParams.get("q") || "").slice(0, 1500);
  if (!q) return new Response(JSON.stringify({ error: "missing q" }), { status: 400 });
  try {
    const r = await fetch("https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=th&dt=t&q=" + encodeURIComponent(q));
    const j = await r.json();
    const text = j[0].map((s) => s[0]).join("");
    return new Response(JSON.stringify({ text }), { headers: { "content-type": "application/json", "cache-control": "public, max-age=86400" } });
  } catch (e) {
    return new Response(JSON.stringify({ error: "translate failed" }), { status: 502 });
  }
}

