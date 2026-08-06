export async function onRequest(context) {
const { request, env } = context;
const url = new URL(request.url);
const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, OPTIONS', 'Cache-Control': 'no-store', 'Content-Type': 'application/json; charset=utf-8' };
if (request.method === 'OPTIONS') return new Response(null, { headers: cors });
const KV = env.MOUTIERS;
if (!KV) return new Response(JSON.stringify({}), { headers: cors });
try {
const isNew = url.searchParams.get('new') === '1';
const isNewDay = url.searchParams.get('day') === '1';
const dayKey = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Paris' }).format(new Date());
let total = parseInt((await KV.get('total')) || '0', 10) || 0;
let today = parseInt((await KV.get('day:' + dayKey)) || '0', 10) || 0;
if (isNew) { total += 1; await KV.put('total', String(total)); }
if (isNewDay) { today += 1; await KV.put('day:' + dayKey, String(today), { expirationTtl: 3456000 }); }
return new Response(JSON.stringify({ total, today }), { headers: cors });
} catch (e) {
return new Response(JSON.stringify({}), { headers: cors });
}
}
