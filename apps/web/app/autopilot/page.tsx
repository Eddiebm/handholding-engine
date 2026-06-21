"use client";
export const runtime = "edge";

import { useState, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";

type AutopilotStatus = {
  mode: string;
  active: boolean;
  last_run_at: string | null;
  scheduler_running: boolean;
  stats: {
    total_generated: number;
    uploaded: number;
    live: number;
    pending_upload: number;
    winners: number;
  };
};

type QueueItem = {
  id: number;
  title: string;
  niche: string;
  status: string;
  safety_passed: boolean | null;
  safety_flags: { category: string; reason: string; severity: string }[] | null;
  score_label: string | null;
  decision: string | null;
  has_video: boolean;
  created_at: string;
};

type Decision = {
  id: number;
  decision: string;
  reason: string;
  created_at: string;
  video_title: string | null;
  niche: string | null;
  score_label: string | null;
};

type Leaderboard = {
  id: number;
  title: string;
  niche: string | null;
  label: string | null;
  url: string | null;
  views: number | null;
  ctr: number | null;
  retention: number | null;
};

type Dashboard = {
  summary: {
    videos_generated: number;
    videos_uploaded: number;
    winners: number;
    losers: number;
    total_views: number;
    avg_ctr_pct: number;
  };
  top_performers: Leaderboard[];
  worst_performers: Leaderboard[];
  winning_niches: { niche: string; total_videos: number; winners: number }[];
  pending_actions: { action: string; count: number }[];
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

type CostSummary = {
  total_api_cost: number;
  total_revenue: number;
  net_profit: number;
  margin_pct: number;
};

const LABEL_BADGE: Record<string, string> = {
  winner: "bg-green-900/40 text-green-300 border border-green-800",
  packaging_problem: "bg-yellow-900/40 text-yellow-300 border border-yellow-800",
  retention_problem: "bg-orange-900/40 text-orange-300 border border-orange-800",
  loser: "bg-red-900/40 text-red-300 border border-red-800",
  needs_more_data: "bg-zinc-800 text-zinc-400 border border-zinc-700",
};

const DECISION_ICON: Record<string, string> = {
  double_down: "⚡",
  make_more_like_this: "✅",
  change_title_style: "✏️",
  change_thumbnail_style: "🖼️",
  improve_hook: "🪝",
  shorten_video: "✂️",
  adjust_length: "📏",
  pause_niche: "⏸️",
  wait: "⏳",
};

function trafficLight(score: number): { dot: string; label: string } {
  if (score > 60) return { dot: "bg-green-400", label: "Scale" };
  if (score >= 10) return { dot: "bg-yellow-400", label: "Watch" };
  return { dot: "bg-red-400", label: "Pause" };
}

function fmtMoney(n: number): string {
  return "$" + n.toFixed(2);
}

export default function AutopilotPage() {
  const [status, setStatus] = useState<AutopilotStatus | null>(null);
  const [config, setConfig] = useState<{ mode: string; uploads_per_day: number; safety_gate_enabled: boolean } | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [leaderboard, setLeaderboard] = useState<Leaderboard[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioNiche[]>([]);
  const [costs, setCosts] = useState<CostSummary | null>(null);
  const [ytConnected, setYtConnected] = useState<boolean | null>(null);
  const [ytChannel, setYtChannel] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [tab, setTab] = useState<"overview" | "portfolio" | "queue" | "scores" | "decisions">("overview");
  const [portfolioUpdating, setPortfolioUpdating] = useState<Set<number>>(new Set());

  const load = useCallback(async () => {
    try {
      const [statusR, configR, queueR, decisionsR, dashR, lbR, ytR, portfolioR, costsR] = await Promise.allSettled([
        fetch(`${API}/autopilot/status`).then(r => r.json()),
        fetch(`${API}/autopilot/config`).then(r => r.json()),
        fetch(`${API}/youtube/queue`).then(r => r.json()),
        fetch(`${API}/decisions/pending`).then(r => r.json()),
        fetch(`${API}/reporting/dashboard`).then(r => r.json()),
        fetch(`${API}/scoring/leaderboard`).then(r => r.json()),
        fetch(`${API}/youtube/auth/status`).then(r => r.json()),
        fetch(`${API}/intelligence/portfolio`).then(r => r.json()),
        fetch(`${API}/intelligence/costs`).then(r => r.json()),
      ]);
      if (statusR.status === "fulfilled") setStatus(statusR.value);
      if (configR.status === "fulfilled") setConfig(configR.value);
      if (queueR.status === "fulfilled") setQueue(Array.isArray(queueR.value) ? queueR.value : []);
      if (decisionsR.status === "fulfilled") setDecisions(Array.isArray(decisionsR.value) ? decisionsR.value : []);
      if (dashR.status === "fulfilled") setDashboard(dashR.value);
      if (lbR.status === "fulfilled") setLeaderboard(Array.isArray(lbR.value) ? lbR.value : []);
      if (ytR.status === "fulfilled") {
        setYtConnected(ytR.value.connected);
        setYtChannel(ytR.value.channel_id || null);
      }
      if (portfolioR.status === "fulfilled") setPortfolio(Array.isArray(portfolioR.value) ? portfolioR.value : []);
      if (costsR.status === "fulfilled") setCosts(costsR.value ?? null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const msg = (m: string) => { setActionMsg(m); setTimeout(() => setActionMsg(null), 4000); };

  const toggleMode = async () => {
    if (!config) return;
    const newMode = config.mode === "assisted" ? "full" : "assisted";
    const ok = newMode === "full"
      ? window.confirm("Switch to Full Autopilot? Videos will upload automatically without your approval.")
      : true;
    if (!ok) return;
    await fetch(`${API}/autopilot/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: newMode }),
    });
    setConfig(c => c ? { ...c, mode: newMode } : c);
    msg(`Switched to ${newMode} mode`);
  };

  const approve = async (id: number) => {
    await fetch(`${API}/youtube/queue/${id}/approve`, { method: "POST" });
    await fetch(`${API}/youtube/upload`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_memory_id: id }),
    });
    setQueue(q => q.filter(v => v.id !== id));
    msg("Upload queued — uploading to YouTube...");
  };

  const reject = async (id: number) => {
    await fetch(`${API}/youtube/queue/${id}/reject`, { method: "POST" });
    setQueue(q => q.filter(v => v.id !== id));
    msg("Rejected");
  };

  const applyDecision = async (id: number) => {
    await fetch(`${API}/decisions/${id}/apply`, { method: "POST" });
    setDecisions(d => d.filter(v => v.id !== id));
    msg("Decision marked as applied");
  };

  const runCycle = async () => {
    await fetch(`${API}/autopilot/run`, { method: "POST" });
    msg("Autonomy cycle triggered — analytics collection + generation running...");
    setTimeout(load, 3000);
  };

  const connectYouTube = async () => {
    const r = await fetch(`${API}/youtube/auth/url`).then(r => r.json());
    if (r.auth_url) window.open(r.auth_url, "_blank");
    else msg("Set YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET env vars first");
  };

  const updatePortfolio = async (nicheId: number, patch: Record<string, unknown>) => {
    setPortfolioUpdating(s => new Set(s).add(nicheId));
    try {
      const r = await fetch(`${API}/intelligence/portfolio/${nicheId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      }).then(r => r.json());
      setPortfolio(p => p.map(n => n.niche_id === nicheId ? { ...n, ...r } : n));
      msg("Portfolio updated");
    } catch {
      msg("Update failed");
    } finally {
      setPortfolioUpdating(s => { const next = new Set(s); next.delete(nicheId); return next; });
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="text-zinc-500 text-sm animate-pulse">Loading autopilot...</div>
    </div>
  );

  const stats = status?.stats;

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-6xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Autopilot</h1>
            <p className="text-zinc-500 text-sm mt-0.5">Autonomous YouTube operator</p>
          </div>
          <div className="flex gap-3 items-center">
            {actionMsg && (
              <span className="text-green-400 text-xs bg-green-950 border border-green-800 px-3 py-1.5 rounded-full">
                {actionMsg}
              </span>
            )}
            <button
              onClick={runCycle}
              className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 rounded-lg transition"
            >
              Run Cycle Now
            </button>
          </div>
        </div>

        {/* YouTube Connection */}
        {ytConnected === false && (
          <div className="mb-6 bg-yellow-950 border border-yellow-800 rounded-xl p-4 flex items-center justify-between">
            <div>
              <div className="text-yellow-300 font-medium text-sm">YouTube not connected</div>
              <div className="text-yellow-600 text-xs mt-0.5">Connect your YouTube channel to enable uploading</div>
            </div>
            <button
              onClick={connectYouTube}
              className="px-4 py-2 text-sm bg-red-600 hover:bg-red-500 rounded-lg transition"
            >
              Connect YouTube
            </button>
          </div>
        )}
        {ytConnected && (
          <div className="mb-6 bg-green-950 border border-green-800 rounded-xl p-3 flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-green-400" />
            <div className="text-green-300 text-sm">YouTube connected{ytChannel ? ` — channel ${ytChannel}` : ""}</div>
          </div>
        )}

        {/* Financial Summary Bar */}
        {costs && (
          <div className="mb-6 bg-zinc-900 border border-zinc-800 rounded-xl p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-xs text-zinc-500 mb-1">Total API Cost</div>
                <div className="text-white font-semibold">{fmtMoney(costs.total_api_cost)}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500 mb-1">Total Revenue</div>
                <div className="text-green-400 font-semibold">{fmtMoney(costs.total_revenue)}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500 mb-1">Net Profit</div>
                <div className={`font-semibold ${costs.net_profit >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {fmtMoney(costs.net_profit)}
                </div>
              </div>
              <div>
                <div className="text-xs text-zinc-500 mb-1">Margin</div>
                <div className={`font-semibold ${costs.margin_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {costs.margin_pct.toFixed(1)}%
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Mode Toggle */}
        <div className="mb-6 bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-white">
              {config?.mode === "full" ? "Full Autopilot" : "Assisted Mode"}
            </div>
            <div className="text-zinc-500 text-xs mt-0.5">
              {config?.mode === "full"
                ? "Videos upload automatically after passing safety check"
                : "You approve each video before it uploads to YouTube"}
            </div>
          </div>
          <button
            onClick={toggleMode}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              config?.mode === "full" ? "bg-blue-600" : "bg-zinc-700"
            }`}
          >
            <span className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-all ${
              config?.mode === "full" ? "left-7" : "left-1"
            }`} />
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          {[
            { label: "Generated", value: stats?.total_generated ?? 0, color: "text-white" },
            { label: "Uploaded", value: stats?.uploaded ?? 0, color: "text-blue-400" },
            { label: "Live", value: stats?.live ?? 0, color: "text-green-400" },
            { label: "Pending", value: stats?.pending_upload ?? 0, color: "text-yellow-400" },
            { label: "Winners", value: stats?.winners ?? 0, color: "text-green-300" },
          ].map(s => (
            <div key={s.label} className="bg-zinc-900 border border-zinc-800 rounded-xl p-3 text-center">
              <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-zinc-500 text-xs mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Channel Stats */}
        {dashboard && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
            {[
              { label: "Total Views", value: dashboard.summary.total_views.toLocaleString() },
              { label: "Avg CTR", value: `${dashboard.summary.avg_ctr_pct}%` },
              { label: "Winning Niches", value: dashboard.winning_niches.filter(n => n.winners > 0).length },
            ].map(s => (
              <div key={s.label} className="bg-zinc-900 border border-zinc-800 rounded-xl p-3">
                <div className="text-zinc-500 text-xs">{s.label}</div>
                <div className="text-white text-xl font-bold mt-1">{s.value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-zinc-800">
          {(["overview", "portfolio", "queue", "scores", "decisions"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm capitalize transition ${
                tab === t ? "text-white border-b-2 border-blue-500 -mb-px" : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {t}
              {t === "queue" && queue.length > 0 && (
                <span className="ml-2 bg-yellow-600 text-yellow-100 text-xs px-1.5 py-0.5 rounded-full">
                  {queue.length}
                </span>
              )}
              {t === "decisions" && decisions.length > 0 && (
                <span className="ml-2 bg-blue-700 text-blue-100 text-xs px-1.5 py-0.5 rounded-full">
                  {decisions.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {tab === "overview" && dashboard && (
          <div className="space-y-6">
            {/* Traffic Light Legend */}
            {portfolio.length > 0 && (
              <div className="flex items-center gap-4 text-xs text-zinc-400">
                <span className="font-medium text-zinc-500 uppercase tracking-wide">Portfolio:</span>
                {[
                  { dot: "bg-green-400", label: "Scale (score > 60)" },
                  { dot: "bg-yellow-400", label: "Watch (10–60)" },
                  { dot: "bg-red-400", label: "Pause (< 10)" },
                ].map(({ dot, label }) => (
                  <span key={label} className="flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full ${dot}`} />
                    {label}
                  </span>
                ))}
              </div>
            )}

            {/* Pending Actions */}
            {dashboard.pending_actions.length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                <h3 className="text-sm font-medium text-zinc-300 mb-3">Pending Actions</h3>
                <div className="space-y-2">
                  {dashboard.pending_actions.map(a => (
                    <div key={a.action} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span>{DECISION_ICON[a.action] || "📋"}</span>
                        <span className="text-sm text-zinc-300 capitalize">{a.action.replace(/_/g, " ")}</span>
                      </div>
                      <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">{a.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Top Performers */}
            {dashboard.top_performers.length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                <h3 className="text-sm font-medium text-zinc-300 mb-3">Top Performers</h3>
                <div className="space-y-3">
                  {dashboard.top_performers.map((v, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-zinc-600 text-xs w-4">#{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-white truncate">{v.title}</div>
                        <div className="text-xs text-zinc-500">{v.niche} · {v.views?.toLocaleString()} views · {v.ctr?.toFixed(1)}% CTR</div>
                      </div>
                      {v.label && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${LABEL_BADGE[v.label] || ""}`}>
                          {v.label?.replace(/_/g, " ")}
                        </span>
                      )}
                      {v.url && (
                        <a href={v.url} target="_blank" className="text-xs text-blue-400 hover:text-blue-300">↗</a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Winning Niches */}
            {dashboard.winning_niches.filter(n => n.winners > 0).length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                <h3 className="text-sm font-medium text-zinc-300 mb-3">Winning Niches</h3>
                <div className="space-y-2">
                  {dashboard.winning_niches.filter(n => n.winners > 0).map((n, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <span className="text-sm text-white">{n.niche}</span>
                      <div className="flex items-center gap-2 text-xs text-zinc-400">
                        <span className="text-green-400">{n.winners} wins</span>
                        <span>/ {n.total_videos} total</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {dashboard.top_performers.length === 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
                <div className="text-zinc-600 text-3xl mb-3">📊</div>
                <div className="text-zinc-400 text-sm">No analytics data yet</div>
                <div className="text-zinc-600 text-xs mt-1">Generate and upload videos to see performance data</div>
              </div>
            )}
          </div>
        )}

        {/* Portfolio Tab */}
        {tab === "portfolio" && (
          <div>
            {portfolio.length === 0 ? (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
                <div className="text-zinc-600 text-3xl mb-3">📁</div>
                <div className="text-zinc-400 text-sm">No portfolio data yet</div>
                <div className="text-zinc-600 text-xs mt-1">Portfolio data appears after niches are set up and active</div>
              </div>
            ) : (
              <div className="space-y-3">
                {portfolio.map(n => {
                  const tl = trafficLight(n.priority_score);
                  const busy = portfolioUpdating.has(n.niche_id);
                  return (
                    <div key={n.niche_id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                      <div className="flex items-start gap-3">
                        <div className="pt-1 shrink-0">
                          <div className={`w-3 h-3 rounded-full ${tl.dot}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-white">{n.niche_name}</span>
                            <span className={`text-xs px-1.5 py-0.5 rounded ${
                              n.status === "scaling" ? "bg-green-900/40 text-green-300 border border-green-800" :
                              n.status === "paused" || n.status === "terminated" ? "bg-red-900/40 text-red-300 border border-red-800" :
                              "bg-zinc-800 text-zinc-400 border border-zinc-700"
                            }`}>
                              {n.status}
                            </span>
                            <span className="text-xs text-zinc-500 ml-auto">{tl.label}</span>
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-5 gap-x-4 gap-y-1 text-xs text-zinc-400">
                            <div><span className="text-zinc-600">Videos/day </span>{n.videos_per_day}</div>
                            <div>
                              <span className="text-zinc-600">Win rate </span>
                              <span className={n.winner_rate_pct >= 30 ? "text-green-400" : n.winner_rate_pct >= 10 ? "text-yellow-400" : "text-red-400"}>
                                {n.winner_rate_pct.toFixed(1)}%
                              </span>
                            </div>
                            <div>
                              <span className="text-zinc-600">Margin </span>
                              <span className={n.profit_margin_pct >= 0 ? "text-green-400" : "text-red-400"}>
                                {n.profit_margin_pct.toFixed(1)}%
                              </span>
                            </div>
                            <div><span className="text-zinc-600">Revenue </span>${n.total_revenue.toFixed(2)}</div>
                            <div><span className="text-zinc-600">Cost </span>${n.total_cost.toFixed(2)}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            disabled={busy}
                            onClick={() => updatePortfolio(n.niche_id, { videos_per_day: n.videos_per_day + 1, status: "scaling" })}
                            className="px-3 py-1.5 text-xs bg-green-700 hover:bg-green-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition"
                          >
                            Scale Up
                          </button>
                          <button
                            disabled={busy || n.status === "paused"}
                            onClick={() => updatePortfolio(n.niche_id, { status: "paused" })}
                            className="px-3 py-1.5 text-xs bg-zinc-700 hover:bg-zinc-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition"
                          >
                            Pause
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Queue Tab */}
        {tab === "queue" && (
          <div>
            {queue.length === 0 ? (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
                <div className="text-zinc-600 text-3xl mb-3">✅</div>
                <div className="text-zinc-400 text-sm">Upload queue is empty</div>
                <div className="text-zinc-600 text-xs mt-1">Videos pending safety review or approval will appear here</div>
              </div>
            ) : (
              <div className="space-y-3">
                {queue.map(v => (
                  <div key={v.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white truncate">{v.title}</div>
                        <div className="text-xs text-zinc-500 mt-0.5">{v.niche} · {new Date(v.created_at).toLocaleDateString()}</div>
                        {v.safety_flags && v.safety_flags.length > 0 && (
                          <div className="mt-2 space-y-1">
                            {v.safety_flags.map((f, i) => (
                              <div key={i} className={`text-xs px-2 py-1 rounded ${
                                f.severity === "high" ? "bg-red-950 text-red-300" : "bg-yellow-950 text-yellow-300"
                              }`}>
                                ⚠️ {f.reason}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          v.status === "upload_queue" ? "bg-blue-900/40 text-blue-300 border border-blue-800" :
                          v.status === "uploading" ? "bg-purple-900/40 text-purple-300 border border-purple-800" :
                          v.status === "upload_failed" ? "bg-red-900/40 text-red-300 border border-red-800" :
                          "bg-zinc-800 text-zinc-400 border border-zinc-700"
                        }`}>
                          {v.status.replace(/_/g, " ")}
                        </span>
                        {v.safety_passed === true && config?.mode === "assisted" && v.status === "upload_queue" && (
                          <>
                            <button
                              onClick={() => approve(v.id)}
                              className="px-3 py-1.5 text-xs bg-green-700 hover:bg-green-600 rounded-lg transition"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => reject(v.id)}
                              className="px-3 py-1.5 text-xs bg-zinc-700 hover:bg-zinc-600 rounded-lg transition"
                            >
                              Reject
                            </button>
                          </>
                        )}
                        {v.safety_passed === false && (
                          <button
                            onClick={() => reject(v.id)}
                            className="px-3 py-1.5 text-xs bg-zinc-700 hover:bg-zinc-600 rounded-lg transition"
                          >
                            Dismiss
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Scores Tab */}
        {tab === "scores" && (
          <div>
            {leaderboard.length === 0 ? (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
                <div className="text-zinc-600 text-3xl mb-3">🏆</div>
                <div className="text-zinc-400 text-sm">No scored videos yet</div>
                <div className="text-zinc-600 text-xs mt-1">Scores appear after analytics are collected (24h after upload)</div>
              </div>
            ) : (
              <div className="space-y-2">
                {leaderboard.map((v, i) => (
                  <div key={v.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center gap-3">
                    <span className="text-zinc-600 text-xs w-6 shrink-0">#{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-white truncate">{v.title}</div>
                      <div className="text-xs text-zinc-500 mt-0.5">
                        {v.niche} · {v.views?.toLocaleString() ?? 0} views · {v.ctr?.toFixed(1) ?? 0}% CTR · {v.retention?.toFixed(0) ?? 0}% retention
                      </div>
                    </div>
                    {v.label && (
                      <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${LABEL_BADGE[v.label] || ""}`}>
                        {v.label.replace(/_/g, " ")}
                      </span>
                    )}
                    {v.url && (
                      <a href={v.url} target="_blank" className="text-xs text-blue-400 hover:text-blue-300 shrink-0">↗</a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Decisions Tab */}
        {tab === "decisions" && (
          <div>
            {decisions.length === 0 ? (
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
                <div className="text-zinc-600 text-3xl mb-3">🧠</div>
                <div className="text-zinc-400 text-sm">No pending decisions</div>
                <div className="text-zinc-600 text-xs mt-1">Decisions appear after videos are scored</div>
              </div>
            ) : (
              <div className="space-y-3">
                {decisions.map(d => (
                  <div key={d.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-lg">{DECISION_ICON[d.decision] || "📋"}</span>
                          <span className="text-sm font-medium text-white capitalize">
                            {d.decision.replace(/_/g, " ")}
                          </span>
                          {d.score_label && (
                            <span className={`text-xs px-1.5 py-0.5 rounded ${LABEL_BADGE[d.score_label] || ""}`}>
                              {d.score_label.replace(/_/g, " ")}
                            </span>
                          )}
                        </div>
                        {d.video_title && (
                          <div className="text-xs text-zinc-500 mb-1">"{d.video_title}"</div>
                        )}
                        {d.reason && (
                          <div className="text-xs text-zinc-400">{d.reason}</div>
                        )}
                      </div>
                      <button
                        onClick={() => applyDecision(d.id)}
                        className="px-3 py-1.5 text-xs bg-zinc-700 hover:bg-zinc-600 rounded-lg transition shrink-0"
                      >
                        Mark Applied
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
