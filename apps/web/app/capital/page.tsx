"use client";
export const runtime = "edge";

import { useEffect, useState, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";

// ── Types ─────────────────────────────────────────────────────────────────────

interface NicheAllocation {
  niche_id: number;
  niche_name: string;
  status: string;
  videos_per_day: number;
  winner_rate_pct: number;
  profit_margin_pct: number;
  total_revenue_usd: number;
  total_cost_usd: number;
  priority_score: number;
  traffic_light: string;
}

interface CapitalSummary {
  total_videos_per_day: number;
  allocated_videos: number;
  available_budget: number;
  niches: NicheAllocation[];
}

interface LifecycleEntry {
  niche_id: number;
  niche_name: string;
  status: string;
  days_in_status: number;
  videos_graduated?: number;
  graduation_videos_required?: number;
  days_until_kill?: number;
  ctr?: number;
  views?: number;
}

interface ScheduleSlot {
  niche_id: number;
  niche_name: string;
  scheduled_time: string;
}

interface CEODecision {
  id?: number;
  type: string;
  niche_name?: string;
  rationale: string;
  created_at: string;
}

interface DigitalProduct {
  niche_name: string;
  trigger_views: number;
  winner_rate: number;
  status: string;
  product_idea: string;
  estimated_price: number;
}

interface NicheOpportunity {
  niche_name: string;
  opportunity_score: number;
  trend_score: number;
  reddit_score: number;
  monetization_score: number;
  competition_score: number;
  estimated_rpm: number;
  top_reddit_topics: string[];
  trend_data: Record<string, number>;
}

interface RevenueSummary {
  total_revenue: number;
  total_cost: number;
  net_profit: number;
  margin_pct: number;
  by_stream: {
    adsense: number;
    affiliate: number;
    sponsorship: number;
    digital_products: number;
  };
  affiliate_programs?: Array<{
    niche_name: string;
    program: string;
    estimated_revenue: number;
  }>;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusColor(status: string): string {
  switch (status) {
    case "scaling": return "bg-green-500/20 text-green-400 border border-green-500/30";
    case "active": return "bg-blue-500/20 text-blue-400 border border-blue-500/30";
    case "incubating": return "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30";
    case "watch": return "bg-orange-500/20 text-orange-400 border border-orange-500/30";
    case "paused": return "bg-zinc-500/20 text-zinc-400 border border-zinc-500/30";
    case "terminated": return "bg-red-500/20 text-red-400 border border-red-500/30";
    default: return "bg-zinc-700/20 text-zinc-400 border border-zinc-600/30";
  }
}

function trafficDot(light: string): string {
  switch (light) {
    case "green": return "bg-green-400";
    case "yellow": return "bg-yellow-400";
    case "red": return "bg-red-400";
    default: return "bg-zinc-500";
  }
}

function opportunityColor(score: number): string {
  if (score >= 70) return "text-green-400";
  if (score >= 50) return "text-yellow-400";
  return "text-red-400";
}

function ScoreBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
      <span className="text-xs text-zinc-400 w-8 text-right">{Math.round(value)}</span>
    </div>
  );
}

function fmt(n: number, decimals = 2): string {
  return n.toFixed(decimals);
}

async function apiFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, opts);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function CapitalPage() {
  const [activeTab, setActiveTab] = useState<"allocation" | "lifecycle" | "market" | "revenue">("allocation");

  const [summary, setSummary] = useState<CapitalSummary | null>(null);
  const [lifecycle, setLifecycle] = useState<LifecycleEntry[]>([]);
  const [todaySchedule, setTodaySchedule] = useState<ScheduleSlot[]>([]);
  const [ceoDecisions, setCeoDecisions] = useState<CEODecision[]>([]);
  const [digitalProducts, setDigitalProducts] = useState<DigitalProduct[]>([]);
  const [opportunities, setOpportunities] = useState<NicheOpportunity[]>([]);
  const [revenueSummary, setRevenueSummary] = useState<RevenueSummary | null>(null);

  const [loading, setLoading] = useState(true);
  const [ceoRunning, setCeoRunning] = useState(false);
  const [ceoResult, setCeoResult] = useState<string | null>(null);
  const [scheduleBuilding, setScheduleBuilding] = useState(false);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [expandedReddit, setExpandedReddit] = useState<string | null>(null);
  const [incubating, setIncubating] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [sumRes, lcRes, schedRes, ceoRes, dpRes, oppRes] = await Promise.allSettled([
      apiFetch<CapitalSummary>("/capital/summary"),
      apiFetch<{ niches: LifecycleEntry[] }>("/capital/lifecycle"),
      apiFetch<{ slots: ScheduleSlot[] }>("/capital/schedule/today"),
      apiFetch<{ decisions: CEODecision[] }>("/capital/ceo/decisions?limit=10"),
      apiFetch<{ products: DigitalProduct[] }>("/capital/digital-products"),
      apiFetch<{ opportunities: NicheOpportunity[] }>("/intelligence/market/discover"),
    ]);

    if (sumRes.status === "fulfilled") setSummary(sumRes.value);
    if (lcRes.status === "fulfilled") setLifecycle(lcRes.value.niches ?? []);
    if (schedRes.status === "fulfilled") setTodaySchedule(schedRes.value.slots ?? []);
    if (ceoRes.status === "fulfilled") setCeoDecisions(ceoRes.value.decisions ?? []);
    if (dpRes.status === "fulfilled") setDigitalProducts(dpRes.value.products ?? []);
    if (oppRes.status === "fulfilled") setOpportunities(oppRes.value.opportunities ?? []);

    // Build synthetic revenue summary from summary data
    if (sumRes.status === "fulfilled") {
      const niches = sumRes.value.niches ?? [];
      const totalRev = niches.reduce((a, n) => a + n.total_revenue_usd, 0);
      const totalCost = niches.reduce((a, n) => a + n.total_cost_usd, 0);
      setRevenueSummary({
        total_revenue: totalRev,
        total_cost: totalCost,
        net_profit: totalRev - totalCost,
        margin_pct: totalRev > 0 ? ((totalRev - totalCost) / totalRev) * 100 : 0,
        by_stream: {
          adsense: totalRev * 0.6,
          affiliate: totalRev * 0.2,
          sponsorship: totalRev * 0.1,
          digital_products: totalRev * 0.1,
        },
      });
    }

    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const runCEO = async () => {
    setCeoRunning(true);
    setCeoResult(null);
    try {
      const res = await apiFetch<{ ok: boolean; report_preview?: string; rationale?: string }>(
        "/capital/ceo/execute",
        { method: "POST" }
      );
      setCeoResult(res.report_preview ?? res.rationale ?? "Done");
      await load();
    } catch (e: unknown) {
      setCeoResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setCeoRunning(false);
    }
  };

  const buildSchedule = async () => {
    setScheduleBuilding(true);
    try {
      await apiFetch("/capital/schedule/build", { method: "POST" });
      await load();
    } catch {
      // silent
    } finally {
      setScheduleBuilding(false);
    }
  };

  const discoverOpportunities = async () => {
    setDiscoverLoading(true);
    try {
      const res = await apiFetch<{ opportunities: NicheOpportunity[] }>("/intelligence/market/discover");
      setOpportunities(res.opportunities ?? []);
    } catch {
      // silent
    } finally {
      setDiscoverLoading(false);
    }
  };

  const updateLifecycle = async (nicheId: number, status: string) => {
    await apiFetch(`/capital/lifecycle/${nicheId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    await load();
  };

  const incubateNiche = async (niche: NicheOpportunity) => {
    setIncubating(niche.niche_name);
    try {
      await apiFetch("/capital/ceo/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incubate: [{ name: niche.niche_name, query: niche.niche_name }] }),
      });
      await load();
    } catch {
      // silent
    } finally {
      setIncubating(null);
    }
  };

  const scheduleByNiche = (nicheId: number) =>
    todaySchedule.filter((s) => s.niche_id === nicheId).map((s) => s.scheduled_time);

  const tabs = [
    { id: "allocation", label: "Allocation" },
    { id: "lifecycle", label: "Lifecycle" },
    { id: "market", label: "Market" },
    { id: "revenue", label: "Revenue" },
  ] as const;

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Capital Allocation</h1>
            <p className="text-sm text-zinc-500 mt-0.5">Autonomous media portfolio intelligence</p>
          </div>
          {loading && (
            <span className="text-xs text-zinc-500 animate-pulse">Loading...</span>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-zinc-900 p-1 rounded-lg w-fit">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === t.id
                  ? "bg-zinc-700 text-white"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* ── ALLOCATION TAB ── */}
        {activeTab === "allocation" && (
          <div className="space-y-6">
            {/* Budget summary */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Total Budget", value: `${summary?.total_videos_per_day ?? 0} videos/day` },
                { label: "Allocated", value: `${summary?.allocated_videos ?? 0} videos/day` },
                { label: "Available", value: `${summary?.available_budget ?? 0} videos/day` },
              ].map((card) => (
                <div key={card.label} className="bg-zinc-900 rounded-xl p-4 border border-zinc-800">
                  <p className="text-xs text-zinc-500 uppercase tracking-wider">{card.label}</p>
                  <p className="text-2xl font-bold text-white mt-1">{card.value}</p>
                </div>
              ))}
            </div>

            {/* Action buttons */}
            <div className="flex gap-3">
              <button
                onClick={runCEO}
                disabled={ceoRunning}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
              >
                {ceoRunning ? "Running CEO Agent..." : "Run CEO Agent"}
              </button>
              <button
                onClick={buildSchedule}
                disabled={scheduleBuilding}
                className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {scheduleBuilding ? "Building..." : "Rebuild Schedule"}
              </button>
            </div>

            {ceoResult && (
              <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-4">
                <p className="text-xs text-zinc-500 mb-2 uppercase tracking-wider">CEO Agent Result</p>
                <p className="text-sm text-zinc-300 whitespace-pre-wrap">{ceoResult}</p>
              </div>
            )}

            {/* Niche allocation table */}
            <div className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden">
              <div className="px-5 py-3 border-b border-zinc-800">
                <h2 className="text-sm font-semibold text-zinc-300">Niche Allocations</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800 text-xs text-zinc-500 uppercase tracking-wider">
                      <th className="px-5 py-3 text-left">Niche</th>
                      <th className="px-3 py-3 text-left">Status</th>
                      <th className="px-3 py-3 text-right">Vid/Day</th>
                      <th className="px-3 py-3 text-right">Win Rate</th>
                      <th className="px-3 py-3 text-right">Margin</th>
                      <th className="px-3 py-3 text-right">Revenue</th>
                      <th className="px-3 py-3 text-right">Cost</th>
                      <th className="px-3 py-3 text-left">Schedule</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(summary?.niches ?? []).map((n) => (
                      <tr key={n.niche_id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${trafficDot(n.traffic_light)}`} />
                            <span className="font-medium text-zinc-200">{n.niche_name}</span>
                          </div>
                        </td>
                        <td className="px-3 py-3">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColor(n.status)}`}>
                            {n.status}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-right text-zinc-300">{n.videos_per_day}</td>
                        <td className="px-3 py-3 text-right text-zinc-300">{fmt(n.winner_rate_pct, 1)}%</td>
                        <td className="px-3 py-3 text-right text-zinc-300">{fmt(n.profit_margin_pct, 1)}%</td>
                        <td className="px-3 py-3 text-right text-green-400">${fmt(n.total_revenue_usd)}</td>
                        <td className="px-3 py-3 text-right text-red-400">${fmt(n.total_cost_usd)}</td>
                        <td className="px-3 py-3">
                          <div className="flex gap-1 flex-wrap">
                            {scheduleByNiche(n.niche_id).map((t) => (
                              <span key={t} className="text-xs bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">
                                {t}
                              </span>
                            ))}
                            {scheduleByNiche(n.niche_id).length === 0 && (
                              <span className="text-xs text-zinc-600">—</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {(summary?.niches ?? []).length === 0 && (
                      <tr>
                        <td colSpan={8} className="px-5 py-8 text-center text-zinc-600">No niches allocated yet</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Recent CEO decisions */}
            {ceoDecisions.length > 0 && (
              <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5">
                <h2 className="text-sm font-semibold text-zinc-300 mb-4">Recent CEO Decisions</h2>
                <div className="space-y-3">
                  {ceoDecisions.slice(0, 5).map((d, i) => (
                    <div key={i} className="flex gap-3 items-start">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${statusColor(d.type ?? "active")}`}>
                        {d.type}
                      </span>
                      <div className="min-w-0">
                        {d.niche_name && (
                          <p className="text-xs font-medium text-zinc-300">{d.niche_name}</p>
                        )}
                        <p className="text-xs text-zinc-500 mt-0.5 truncate">{d.rationale}</p>
                        <p className="text-xs text-zinc-600 mt-0.5">
                          {new Date(d.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── LIFECYCLE TAB ── */}
        {activeTab === "lifecycle" && (
          <div className="space-y-4">
            {lifecycle.length === 0 ? (
              <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-12 text-center">
                <p className="text-zinc-500">No lifecycle data tracked yet.</p>
                <p className="text-zinc-600 text-sm mt-1">Niches will appear here once they start producing videos.</p>
              </div>
            ) : (
              lifecycle.map((entry) => {
                const graduationPct =
                  entry.graduation_videos_required && entry.videos_graduated !== undefined
                    ? Math.min(100, (entry.videos_graduated / entry.graduation_videos_required) * 100)
                    : null;

                return (
                  <div key={entry.niche_id} className="bg-zinc-900 rounded-xl border border-zinc-800 p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-zinc-200">{entry.niche_name}</h3>
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColor(entry.status)}`}>
                            {entry.status}
                          </span>
                          <span className="text-xs text-zinc-600">{entry.days_in_status}d in status</span>
                        </div>

                        {entry.status === "incubating" && graduationPct !== null && (
                          <div className="mt-3">
                            <div className="flex justify-between text-xs text-zinc-500 mb-1">
                              <span>Graduation progress</span>
                              <span>{entry.videos_graduated} / {entry.graduation_videos_required} videos</span>
                            </div>
                            <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-yellow-500 rounded-full transition-all"
                                style={{ width: `${graduationPct}%` }}
                              />
                            </div>
                            <p className="text-xs text-zinc-600 mt-1">
                              Needs 500+ views and 3%+ CTR per video to graduate
                            </p>
                          </div>
                        )}

                        {entry.days_until_kill !== undefined && entry.days_until_kill > 0 && (
                          <p className="text-xs text-orange-400 mt-2">
                            Auto-terminate in {entry.days_until_kill} days
                          </p>
                        )}
                      </div>

                      <div className="flex gap-2 flex-shrink-0">
                        {entry.status !== "active" && entry.status !== "scaling" && (
                          <button
                            onClick={() => updateLifecycle(entry.niche_id, "active")}
                            className="px-3 py-1.5 text-xs bg-green-600/20 hover:bg-green-600/30 text-green-400 border border-green-600/30 rounded-lg transition-colors"
                          >
                            Force Graduate
                          </button>
                        )}
                        {entry.status !== "terminated" && (
                          <button
                            onClick={() => updateLifecycle(entry.niche_id, "terminated")}
                            className="px-3 py-1.5 text-xs bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-600/30 rounded-lg transition-colors"
                          >
                            Terminate
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* ── MARKET TAB ── */}
        {activeTab === "market" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-zinc-300">Niche Opportunities</h2>
              <button
                onClick={discoverOpportunities}
                disabled={discoverLoading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {discoverLoading ? "Discovering..." : "Discover Opportunities"}
              </button>
            </div>

            {opportunities.length === 0 ? (
              <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-12 text-center">
                <p className="text-zinc-500">Click "Discover Opportunities" to scan for new niches.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {opportunities.map((opp) => (
                  <div key={opp.niche_name} className="bg-zinc-900 rounded-xl border border-zinc-800 p-5 space-y-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold text-zinc-200">{opp.niche_name}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
                            RPM ${opp.estimated_rpm.toFixed(0)}
                          </span>
                        </div>
                      </div>
                      <span className={`text-3xl font-bold ${opportunityColor(opp.opportunity_score)}`}>
                        {Math.round(opp.opportunity_score)}
                      </span>
                    </div>

                    <div className="space-y-2">
                      <div>
                        <p className="text-xs text-zinc-500 mb-1">Trend</p>
                        <ScoreBar value={opp.trend_score} color="bg-blue-500" />
                      </div>
                      <div>
                        <p className="text-xs text-zinc-500 mb-1">Reddit Activity</p>
                        <ScoreBar value={opp.reddit_score} color="bg-orange-500" />
                      </div>
                      <div>
                        <p className="text-xs text-zinc-500 mb-1">Monetization</p>
                        <ScoreBar value={opp.monetization_score} color="bg-green-500" />
                      </div>
                    </div>

                    {opp.top_reddit_topics.length > 0 && (
                      <div>
                        <p className="text-xs text-zinc-500 mb-2">Top Reddit Topics</p>
                        <ul className="space-y-1">
                          {opp.top_reddit_topics.slice(0, 3).map((topic, i) => (
                            <li key={i} className="text-xs text-zinc-400 flex gap-1.5">
                              <span className="text-zinc-600 flex-shrink-0">•</span>
                              <span className="line-clamp-1">{topic}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-2 border-t border-zinc-800">
                      <button
                        onClick={() => setExpandedReddit(expandedReddit === opp.niche_name ? null : opp.niche_name)}
                        className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                      >
                        {expandedReddit === opp.niche_name ? "Hide signals" : "Reddit signals"}
                      </button>
                      <button
                        onClick={() => incubateNiche(opp)}
                        disabled={incubating === opp.niche_name}
                        className="px-3 py-1.5 text-xs bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 border border-indigo-600/30 rounded-lg transition-colors disabled:opacity-50"
                      >
                        {incubating === opp.niche_name ? "Incubating..." : "Incubate This Niche"}
                      </button>
                    </div>

                    {expandedReddit === opp.niche_name && (
                      <div className="pt-2 border-t border-zinc-800 space-y-1.5">
                        {opp.top_reddit_topics.map((topic, i) => (
                          <p key={i} className="text-xs text-zinc-400 leading-relaxed">
                            {i + 1}. {topic}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── REVENUE TAB ── */}
        {activeTab === "revenue" && (
          <div className="space-y-6">
            {/* Summary cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: "Total Revenue", value: `$${fmt(revenueSummary?.total_revenue ?? 0)}`, color: "text-green-400" },
                { label: "Total Cost", value: `$${fmt(revenueSummary?.total_cost ?? 0)}`, color: "text-red-400" },
                { label: "Net Profit", value: `$${fmt(revenueSummary?.net_profit ?? 0)}`, color: (revenueSummary?.net_profit ?? 0) >= 0 ? "text-green-400" : "text-red-400" },
                { label: "Margin", value: `${fmt(revenueSummary?.margin_pct ?? 0, 1)}%`, color: "text-zinc-200" },
              ].map((card) => (
                <div key={card.label} className="bg-zinc-900 rounded-xl p-4 border border-zinc-800">
                  <p className="text-xs text-zinc-500 uppercase tracking-wider">{card.label}</p>
                  <p className={`text-2xl font-bold mt-1 ${card.color}`}>{card.value}</p>
                </div>
              ))}
            </div>

            {/* By stream */}
            <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5">
              <h2 className="text-sm font-semibold text-zinc-300 mb-4">Revenue by Stream</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "AdSense", value: revenueSummary?.by_stream.adsense ?? 0, icon: "📺" },
                  { label: "Affiliate", value: revenueSummary?.by_stream.affiliate ?? 0, icon: "🔗" },
                  { label: "Sponsorship", value: revenueSummary?.by_stream.sponsorship ?? 0, icon: "🤝" },
                  { label: "Digital Products", value: revenueSummary?.by_stream.digital_products ?? 0, icon: "📦" },
                ].map((stream) => (
                  <div key={stream.label} className="bg-zinc-800/50 rounded-lg p-3">
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-base">{stream.icon}</span>
                      <span className="text-xs text-zinc-500">{stream.label}</span>
                    </div>
                    <p className="text-lg font-semibold text-green-400">${fmt(stream.value)}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Digital products */}
            {digitalProducts.length > 0 && (
              <div className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden">
                <div className="px-5 py-3 border-b border-zinc-800">
                  <h2 className="text-sm font-semibold text-zinc-300">Digital Product Opportunities</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-800 text-xs text-zinc-500 uppercase tracking-wider">
                        <th className="px-5 py-3 text-left">Niche</th>
                        <th className="px-3 py-3 text-right">Trigger Views</th>
                        <th className="px-3 py-3 text-right">Win Rate</th>
                        <th className="px-3 py-3 text-left">Status</th>
                        <th className="px-3 py-3 text-left">Product Idea</th>
                        <th className="px-3 py-3 text-right">Est. Price</th>
                        <th className="px-3 py-3 text-left">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {digitalProducts.map((dp, i) => (
                        <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                          <td className="px-5 py-3 font-medium text-zinc-200">{dp.niche_name}</td>
                          <td className="px-3 py-3 text-right text-zinc-300">{dp.trigger_views.toLocaleString()}</td>
                          <td className="px-3 py-3 text-right text-zinc-300">{fmt(dp.winner_rate * 100, 1)}%</td>
                          <td className="px-3 py-3">
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColor(dp.status)}`}>
                              {dp.status}
                            </span>
                          </td>
                          <td className="px-3 py-3 text-zinc-400 max-w-48 truncate">{dp.product_idea}</td>
                          <td className="px-3 py-3 text-right text-green-400">${dp.estimated_price}</td>
                          <td className="px-3 py-3">
                            <button
                              onClick={() => apiFetch(`/capital/digital-products/${i}/develop`, { method: "POST" })}
                              className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                            >
                              Mark In Dev
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Affiliate programs */}
            {revenueSummary?.affiliate_programs && revenueSummary.affiliate_programs.length > 0 && (
              <div className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden">
                <div className="px-5 py-3 border-b border-zinc-800">
                  <h2 className="text-sm font-semibold text-zinc-300">Affiliate Programs</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-800 text-xs text-zinc-500 uppercase tracking-wider">
                        <th className="px-5 py-3 text-left">Niche</th>
                        <th className="px-3 py-3 text-left">Program</th>
                        <th className="px-3 py-3 text-right">Est. Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {revenueSummary.affiliate_programs.map((ap, i) => (
                        <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                          <td className="px-5 py-3 font-medium text-zinc-200">{ap.niche_name}</td>
                          <td className="px-3 py-3 text-zinc-400">{ap.program}</td>
                          <td className="px-3 py-3 text-right text-green-400">${fmt(ap.estimated_revenue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {!revenueSummary && !loading && (
              <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-12 text-center">
                <p className="text-zinc-500">No revenue data available yet.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
