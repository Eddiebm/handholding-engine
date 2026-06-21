"use client";
export const runtime = "edge";

import { useState, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";

type TrendingVideo = {
  id: number;
  title: string;
  channel: string;
  views: number;
  trend_score: number;
  hook_style: string | null;
  thumbnail_style: string | null;
  niche_id: number | null;
  niche_name: string | null;
};

type HookPerformance = {
  hook_type: string;
  avg_retention_pct: number;
  avg_ctr: number;
  videos_tested: number;
  status: string;
};

type ThumbnailStyle = {
  style: string;
  avg_ctr: number;
  video_count: number;
  relative_performance: number;
};

type CeoReport = {
  id: number;
  created_at: string;
  content: string;
};

type PortfolioNiche = {
  niche_id: number;
  niche_name: string;
  status: string;
  videos_per_day: number;
  winner_rate_pct: number;
  profit_margin_pct: number;
  total_revenue: number;
  total_cost: number;
  priority_score: number;
};

type Niche = { id: number; name: string };

const THUMBNAIL_STYLES = ["face", "no_face", "arrow", "text_heavy", "minimal", "luxury", "news_style"];

function fmtViews(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

function retentionColor(pct: number): string {
  if (pct >= 50) return "text-green-400";
  if (pct >= 30) return "text-yellow-400";
  return "text-red-400";
}

export default function IntelligencePage() {
  const [tab, setTab] = useState<"trends" | "hooks" | "thumbnails" | "ceo">("trends");
  const [trends, setTrends] = useState<TrendingVideo[]>([]);
  const [hooks, setHooks] = useState<HookPerformance[]>([]);
  const [thumbnails, setThumbnails] = useState<ThumbnailStyle[]>([]);
  const [ceoReport, setCeoReport] = useState<CeoReport | null>(null);
  const [niches, setNiches] = useState<Niche[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const [scrapeNicheId, setScrapeNicheId] = useState<string>("");
  const [scrapeQuery, setScrapeQuery] = useState("");
  const [scraping, setScraping] = useState(false);

  const [ideaInput, setIdeaInput] = useState("");
  const [ideaScore, setIdeaScore] = useState<number | null>(null);
  const [ideaScoring, setIdeaScoring] = useState(false);

  const [ceoRunning, setCeoRunning] = useState(false);

  const msg = (m: string) => { setActionMsg(m); setTimeout(() => setActionMsg(null), 4000); };

  const load = useCallback(async () => {
    const [trendsR, hooksR, thumbsR, ceoR, nichesR] = await Promise.allSettled([
      fetch(`${API}/intelligence/trends/top`).then(r => r.json()),
      fetch(`${API}/intelligence/hooks`).then(r => r.json()),
      fetch(`${API}/intelligence/thumbnails`).then(r => r.json()),
      fetch(`${API}/intelligence/ceo/latest`).then(r => r.json()),
      fetch(`${API}/niches`).then(r => r.json()),
    ]);
    if (trendsR.status === "fulfilled") setTrends(Array.isArray(trendsR.value) ? trendsR.value : []);
    if (hooksR.status === "fulfilled") setHooks(Array.isArray(hooksR.value) ? hooksR.value : []);
    if (thumbsR.status === "fulfilled") {
      const raw = Array.isArray(thumbsR.value) ? thumbsR.value : [];
      const maxCtr = Math.max(...raw.map((t: ThumbnailStyle) => t.avg_ctr), 1);
      setThumbnails(raw.map((t: ThumbnailStyle) => ({ ...t, relative_performance: t.avg_ctr / maxCtr })));
    } else {
      setThumbnails(THUMBNAIL_STYLES.map(s => ({ style: s, avg_ctr: 0, video_count: 0, relative_performance: 0 })));
    }
    if (ceoR.status === "fulfilled" && ceoR.value?.id) setCeoReport(ceoR.value);
    if (nichesR.status === "fulfilled") setNiches(Array.isArray(nichesR.value) ? nichesR.value : []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const scrapeNow = async () => {
    if (!scrapeNicheId) { msg("Select a niche first"); return; }
    setScraping(true);
    try {
      await fetch(`${API}/intelligence/trends/scrape`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ niche_id: Number(scrapeNicheId), query: scrapeQuery }),
      });
      msg("Trend scrape started — results will appear shortly");
      setTimeout(load, 5000);
    } finally {
      setScraping(false);
    }
  };

  const runCeo = async () => {
    setCeoRunning(true);
    try {
      await fetch(`${API}/intelligence/ceo/run`, { method: "POST" });
      msg("CEO agent running — check back in a minute");
      setTimeout(load, 60000);
    } finally {
      setCeoRunning(false);
    }
  };

  const scoreIdea = async () => {
    if (!ideaInput.trim()) return;
    setIdeaScoring(true);
    setIdeaScore(null);
    try {
      const r = await fetch(`${API}/intelligence/score-idea`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idea: ideaInput }),
      }).then(r => r.json());
      setIdeaScore(r.opportunity_score ?? r.score ?? 0);
    } catch {
      msg("Failed to score idea");
    } finally {
      setIdeaScoring(false);
    }
  };

  const bestHook = hooks.length > 0
    ? hooks.reduce((a, b) => b.avg_retention_pct > a.avg_retention_pct ? b : a, hooks[0])
    : null;

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="text-zinc-500 text-sm animate-pulse">Loading intelligence...</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-6xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Intelligence</h1>
            <p className="text-zinc-500 text-sm mt-0.5">Trends, hooks, thumbnails, CEO reports</p>
          </div>
          {actionMsg && (
            <span className="text-green-400 text-xs bg-green-950 border border-green-800 px-3 py-1.5 rounded-full">
              {actionMsg}
            </span>
          )}
        </div>

        {/* Idea Scorer */}
        <div className="mb-6 bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="text-sm font-medium text-zinc-300 mb-3">Idea Scorer</div>
          <div className="flex gap-2">
            <input
              value={ideaInput}
              onChange={e => setIdeaInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && scoreIdea()}
              placeholder="Enter a video idea to score its opportunity..."
              className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
            />
            <button
              onClick={scoreIdea}
              disabled={ideaScoring || !ideaInput.trim()}
              className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition"
            >
              {ideaScoring ? "Scoring..." : "Score"}
            </button>
          </div>
          {ideaScore !== null && (
            <div className="mt-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-zinc-400">Opportunity Score</span>
                <span className={`text-sm font-bold ${ideaScore >= 70 ? "text-green-400" : ideaScore >= 40 ? "text-yellow-400" : "text-red-400"}`}>
                  {ideaScore}/100
                </span>
              </div>
              <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${ideaScore >= 70 ? "bg-green-500" : ideaScore >= 40 ? "bg-yellow-500" : "bg-red-500"}`}
                  style={{ width: `${ideaScore}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-zinc-800">
          {(["trends", "hooks", "thumbnails", "ceo"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm capitalize transition ${
                tab === t ? "text-white border-b-2 border-blue-500 -mb-px" : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {t === "ceo" ? "CEO Report" : t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {/* Trends Tab */}
        {tab === "trends" && (
          <div>
            {/* Scrape Controls */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 mb-4">
              <div className="text-xs font-medium text-zinc-400 mb-3 uppercase tracking-wide">Scrape Now</div>
              <div className="flex gap-2 flex-wrap">
                <select
                  value={scrapeNicheId}
                  onChange={e => setScrapeNicheId(e.target.value)}
                  className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-zinc-500"
                >
                  <option value="">Select niche...</option>
                  {niches.map(n => (
                    <option key={n.id} value={n.id}>{n.name}</option>
                  ))}
                </select>
                <input
                  value={scrapeQuery}
                  onChange={e => setScrapeQuery(e.target.value)}
                  placeholder="Search query (optional)"
                  className="flex-1 min-w-48 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
                />
                <button
                  onClick={scrapeNow}
                  disabled={scraping || !scrapeNicheId}
                  className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition"
                >
                  {scraping ? "Scraping..." : "Scrape Now"}
                </button>
              </div>
            </div>

            {trends.length === 0 ? (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
                <div className="text-zinc-600 text-3xl mb-3">📈</div>
                <div className="text-zinc-400 text-sm">No trending videos yet</div>
                <div className="text-zinc-600 text-xs mt-1">Scrape a niche to populate trend data</div>
              </div>
            ) : (
              <div className="space-y-3">
                {trends.map((v, i) => (
                  <div key={v.id ?? i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                    <div className="flex items-start gap-3">
                      <span className="text-zinc-600 text-xs w-5 shrink-0 mt-0.5">#{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white">{v.title}</div>
                        <div className="text-xs text-zinc-500 mt-0.5">{v.channel}</div>
                        <div className="flex flex-wrap gap-2 mt-2">
                          <span className="text-xs bg-zinc-800 text-zinc-300 border border-zinc-700 px-2 py-0.5 rounded-full">
                            {fmtViews(v.views)} views
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            v.trend_score >= 70 ? "bg-green-900/40 text-green-300 border border-green-800" :
                            v.trend_score >= 40 ? "bg-yellow-900/40 text-yellow-300 border border-yellow-800" :
                            "bg-zinc-800 text-zinc-400 border border-zinc-700"
                          }`}>
                            Score {v.trend_score}
                          </span>
                          {v.hook_style && (
                            <span className="text-xs bg-blue-900/30 text-blue-300 border border-blue-800/50 px-2 py-0.5 rounded-full">
                              {v.hook_style}
                            </span>
                          )}
                          {v.thumbnail_style && (
                            <span className="text-xs bg-purple-900/30 text-purple-300 border border-purple-800/50 px-2 py-0.5 rounded-full">
                              {v.thumbnail_style}
                            </span>
                          )}
                          {v.niche_name && (
                            <span className="text-xs text-zinc-500">{v.niche_name}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Hooks Tab */}
        {tab === "hooks" && (
          <div>
            {hooks.length === 0 ? (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
                <div className="text-zinc-600 text-3xl mb-3">🪝</div>
                <div className="text-zinc-400 text-sm">No hook performance data yet</div>
                <div className="text-zinc-600 text-xs mt-1">Hook data populates after videos are scored</div>
              </div>
            ) : (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      <th className="text-left text-xs font-medium text-zinc-500 uppercase tracking-wide px-4 py-3">Hook Type</th>
                      <th className="text-right text-xs font-medium text-zinc-500 uppercase tracking-wide px-4 py-3">Avg Retention</th>
                      <th className="text-right text-xs font-medium text-zinc-500 uppercase tracking-wide px-4 py-3">Avg CTR</th>
                      <th className="text-right text-xs font-medium text-zinc-500 uppercase tracking-wide px-4 py-3">Videos Tested</th>
                      <th className="text-right text-xs font-medium text-zinc-500 uppercase tracking-wide px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hooks.map((h, i) => {
                      const isBest = bestHook?.hook_type === h.hook_type;
                      return (
                        <tr
                          key={i}
                          className={`border-b border-zinc-800/50 last:border-0 ${isBest ? "bg-green-950/20" : ""}`}
                        >
                          <td className="px-4 py-3 text-white">
                            <div className="flex items-center gap-2">
                              {isBest && <span title="Best performer">👑</span>}
                              <span className="capitalize">{h.hook_type.replace(/_/g, " ")}</span>
                            </div>
                          </td>
                          <td className={`px-4 py-3 text-right font-medium ${retentionColor(h.avg_retention_pct)}`}>
                            {h.avg_retention_pct.toFixed(1)}%
                          </td>
                          <td className="px-4 py-3 text-right text-zinc-300">
                            {h.avg_ctr.toFixed(2)}%
                          </td>
                          <td className="px-4 py-3 text-right text-zinc-400">
                            {h.videos_tested}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              h.status === "active" ? "bg-green-900/40 text-green-300 border border-green-800" :
                              h.status === "testing" ? "bg-yellow-900/40 text-yellow-300 border border-yellow-800" :
                              "bg-zinc-800 text-zinc-400 border border-zinc-700"
                            }`}>
                              {h.status}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Thumbnails Tab */}
        {tab === "thumbnails" && (
          <div>
            {thumbnails.length === 0 ? (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
                <div className="text-zinc-600 text-3xl mb-3">🖼️</div>
                <div className="text-zinc-400 text-sm">No thumbnail data yet</div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {thumbnails.map((t, i) => (
                  <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium text-white capitalize">{t.style.replace(/_/g, " ")}</span>
                      <span className={`text-xs font-bold ${
                        t.avg_ctr >= 5 ? "text-green-400" : t.avg_ctr >= 3 ? "text-yellow-400" : "text-zinc-400"
                      }`}>
                        {t.avg_ctr.toFixed(2)}% CTR
                      </span>
                    </div>
                    <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden mb-2">
                      <div
                        className={`h-full rounded-full ${
                          t.relative_performance >= 0.8 ? "bg-green-500" :
                          t.relative_performance >= 0.5 ? "bg-yellow-500" : "bg-zinc-600"
                        }`}
                        style={{ width: `${(t.relative_performance * 100).toFixed(0)}%` }}
                      />
                    </div>
                    <div className="text-xs text-zinc-500">{t.video_count} videos tested</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* CEO Report Tab */}
        {tab === "ceo" && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm text-zinc-400">
                {ceoReport
                  ? `Last report: ${new Date(ceoReport.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`
                  : "No reports yet"}
              </div>
              <button
                onClick={runCeo}
                disabled={ceoRunning}
                className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition flex items-center gap-2"
              >
                {ceoRunning ? (
                  <>
                    <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Running...
                  </>
                ) : "Run CEO Agent"}
              </button>
            </div>

            {ceoReport ? (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                <div className="space-y-3">
                  {ceoReport.content.split("\n").filter(Boolean).map((para, i) => (
                    <p key={i} className="text-zinc-300 text-sm leading-relaxed">{para}</p>
                  ))}
                </div>
              </div>
            ) : (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
                <div className="text-zinc-600 text-4xl mb-4">🤖</div>
                <div className="text-zinc-400 text-sm font-medium">No reports yet — run the CEO agent</div>
                <div className="text-zinc-600 text-xs mt-2">The CEO agent analyzes your channel and produces a strategic report</div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
