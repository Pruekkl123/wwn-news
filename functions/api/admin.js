// Cloudflare Pages Function: /api/admin
// ตั้งค่าที่ Pages > Settings > Environment variables (Production และ Preview):
//   ADMIN_PASSWORD             Secret  รหัสผ่านเข้า admin panel (ตั้งเอง ยิ่งยาวยิ่งดี)
//   GITHUB_TOKEN               Secret  fine-grained PAT ของ repo wwn-news
//                                      ต้องมีสิทธิ์: Contents: Read and write, Actions: Read and write
//   GITHUB_REPO                Text    เช่น "Pruekkl123/wwn-news"
//   WORKFLOW_FILE              Text    เช่น "daily_news.yml"
//   LINE_CHANNEL_ACCESS_TOKEN  Secret  (ไม่ใส่ก็ได้ ถ้าไม่ใช้ปุ่มส่งข่าวด่วนเข้า LINE ทันที)

const GH = "https://api.github.com";

function b64encodeUtf8(str) {
  var bytes = new TextEncoder().encode(str), binary = "", chunk = 0x8000;
  for (var i = 0; i < bytes.length; i += chunk) binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  return btoa(binary);
}
function b64decodeUtf8(str) {
  var binary = atob(str.replace(/\n/g, "")), bytes = new Uint8Array(binary.length);
  for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}
function jsonRes(obj, status) {
  return new Response(JSON.stringify(obj), { status: status || 200, headers: { "content-type": "application/json" } });
}
function ghHeaders(env) {
  return { Authorization: "Bearer " + env.GITHUB_TOKEN, Accept: "application/vnd.github+json", "User-Agent": "wwn-admin" };
}
async function ghGetFile(env, path) {
  var r = await fetch(GH + "/repos/" + env.GITHUB_REPO + "/contents/" + path, { headers: ghHeaders(env) });
  if (!r.ok) return { ok: false, status: r.status, body: await r.text() };
  var j = await r.json();
  var content = JSON.parse(b64decodeUtf8(j.content));
  return { ok: true, sha: j.sha, content: content };
}
async function ghPutFile(env, path, content, sha, message) {
  var body = { message: message, content: b64encodeUtf8(JSON.stringify(content, null, 2)) };
  if (sha) body.sha = sha;
  var r = await fetch(GH + "/repos/" + env.GITHUB_REPO + "/contents/" + path, {
    method: "PUT",
    headers: Object.assign({ "Content-Type": "application/json" }, ghHeaders(env)),
    body: JSON.stringify(body),
  });
  return { ok: r.ok, status: r.status, body: await r.text() };
}

export async function onRequestPost(ctx) {
  var env = ctx.env, request = ctx.request;
  var data;
  try { data = await request.json(); } catch (e) { return jsonRes({ error: "bad json" }, 400); }

  if (!env.ADMIN_PASSWORD || data.password !== env.ADMIN_PASSWORD) {
    return jsonRes({ error: "รหัสผ่านไม่ถูกต้อง" }, 401);
  }

  var action = data.action;

  if (action === "status") {
    var news = await ghGetFile(env, "news.json");
    var lastRun = null;
    try {
      var rr = await fetch(GH + "/repos/" + env.GITHUB_REPO + "/actions/workflows/" + env.WORKFLOW_FILE + "/runs?per_page=1", { headers: ghHeaders(env) });
      var rj = await rr.json();
      var run = rj.workflow_runs && rj.workflow_runs[0];
      if (run) lastRun = { status: run.status, conclusion: run.conclusion, created_at: run.created_at, html_url: run.html_url };
    } catch (e) {}
    var sentCount = null;
    var sentFile = await ghGetFile(env, "sent_news.json");
    if (sentFile.ok) sentCount = sentFile.content.length;
    return jsonRes({
      ok: true,
      newsCount: news.ok ? news.content.length : null,
      hiddenCount: news.ok ? news.content.filter(function (n) { return n.hidden; }).length : null,
      latestNews: news.ok ? news.content.slice(0, 5).map(function (n) { return { title: n.titleTh || n.title, cat: n.cat, date: n.date, url: n.url, hidden: !!n.hidden }; }) : [],
      lastRun: lastRun,
      sentCount: sentCount,
    });
  }

  if (action === "run-now") {
    var r1 = await fetch(GH + "/repos/" + env.GITHUB_REPO + "/actions/workflows/" + env.WORKFLOW_FILE + "/dispatches", {
      method: "POST",
      headers: Object.assign({ "Content-Type": "application/json" }, ghHeaders(env)),
      body: JSON.stringify({ ref: "main", inputs: { dry_run: String(!!data.dryRun) } }),
    });
    return jsonRes({ ok: r1.ok, status: r1.status, body: await r1.text() });
  }

  if (action === "hide" || action === "unhide") {
    var f1 = await ghGetFile(env, "news.json");
    if (!f1.ok) return jsonRes({ error: "อ่าน news.json ไม่สำเร็จ", detail: f1 }, 500);
    var list1 = f1.content;
    var item1 = list1.filter(function (n) { return n.url === data.url; })[0];
    if (!item1) return jsonRes({ error: "ไม่พบข่าวนี้" }, 404);
    item1.hidden = action === "hide";
    var put1 = await ghPutFile(env, "news.json", list1, f1.sha, "admin: " + action + " " + data.url);
    return jsonRes({ ok: put1.ok, detail: put1 });
  }

  if (action === "breaking") {
    var f2 = await ghGetFile(env, "news.json");
    if (!f2.ok) return jsonRes({ error: "อ่าน news.json ไม่สำเร็จ", detail: f2 }, 500);
    var list2 = f2.content;
    var now = Date.now();
    var item2 = {
      id: 0,
      title: data.titleEn || data.titleTh || "Breaking news",
      titleTh: data.titleTh || data.titleEn || "ข่าวด่วน",
      cat: data.cat || "ด่วน",
      date: new Date(now).toDateString(),
      ts: now,
      img: data.img || ("https://picsum.photos/seed/" + now + "/800/600"),
      desc: data.descEn || data.descTh || "",
      descTh: data.descTh || data.descEn || "",
      url: data.url || ("https://wwn-news.pages.dev/#breaking-" + now),
      breaking: true,
    };
    list2.unshift(item2);
    list2.forEach(function (n, i) { n.id = i + 1; });
    var put2 = await ghPutFile(env, "news.json", list2, f2.sha, "admin: add breaking news");
    var lineResult = null;
    if (data.sendLine && env.LINE_CHANNEL_ACCESS_TOKEN) {
      var text = "🚨 ข่าวด่วน\n\n" + item2.titleTh + "\n" + item2.descTh + "\n\nอ่านเพิ่มเติม: https://wwn-news.pages.dev";
      var r2 = await fetch("https://api.line.me/v2/bot/message/broadcast", {
        method: "POST",
        headers: { Authorization: "Bearer " + env.LINE_CHANNEL_ACCESS_TOKEN, "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [{ type: "text", text: text }] }),
      });
      lineResult = { ok: r2.ok, status: r2.status };
    }
    return jsonRes({ ok: put2.ok, detail: put2, lineResult: lineResult });
  }

  if (action === "announcement") {
    var cur = await ghGetFile(env, "announcement.json");
    var payload = { text: data.text || "", show: !!data.show, updatedAt: Date.now() };
    var put3 = await ghPutFile(env, "announcement.json", payload, cur.ok ? cur.sha : null, "admin: update announcement");
    return jsonRes({ ok: put3.ok, detail: put3 });
  }

  return jsonRes({ error: "ไม่รู้จัก action นี้" }, 400);
}
