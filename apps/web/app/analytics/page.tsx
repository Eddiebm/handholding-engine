"use client";

import { useEffect, useState } from "react";

interface ChannelStats { subscribers: number; total_views: number }
interface VideoEntry {
  video_id: string; niche: string; title: string;
  uploaded_at: string; url: string; views?: number;
  likes?: number; score?: number; cost_usd?: number;
}
interface Summary {
  total_videos: number; scored_videos: number; pending_score: number;
  top_niches: [string, number][]; channel_stats: ChannelStats;
  ypp_subs_pct: number | null; last_updated: string | null;
  cost: { total_usd: number; last_30d_usd: number; per_video_avg: number };
  recent_videos: VideoEntry[];
}

export default function AnalyticsPage() {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/proxy?path=%2Fanalytics%2Fsummary")
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600 p-8">{error}</p>;
  if (!data) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600" />
    </div>
  );

  const subs = data.channel_stats?.subscribers ?? 0;
  const yppPct = Math.min((subs / 1000) * 100, 100);

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      <div className="text-center pt-6">
        <h1 className="text-3xl font-bold text-purple-700">Channel Analytics</h1>
        {data.last_updated && (
          <p className="text-xs text-gray-400 mt-1">
            Last updated: {new Date(data.last_updated).toLocaleString()}
          </p>
        )}
      </div>

      {/* YPP Progress */}
      <div className="card border-2 border-purple-200 bg-purple-50">
        <h2 className="text-lg font-bold text-purple-800 mb-3">YouTube Partner Program Progress</h2>
        <div className="grid grid-cols-2 gap-6 mb-4">
          <div>
            <p className="text-sm text-gray-500 mb-1">Subscribers</p>
            <p className="text-3xl font-bold text-purple-700">{subs.toLocaleString()}<span className="text-base text-gray-400 ml-1">/ 1,000</span></p>
            <div className="mt-2 h-3 bg-purple-100 rounded-full overflow-hidden">
              <div className="h-full bg-purple-500 rounded-full transition-all" style={{ width: `${yppPct}%` }} />
            </div>
            <p className="text-xs text-gray-500 mt-1">{yppPct.toFixed(1)}% of subscriber goal</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">Total Channel Views</p>
            <p className="text-3xl font-bold text-blue-700">{(data.channel_stats?.total_views ?? 0).toLocaleString()}</p>
            <p className="text-xs text-gray-400 mt-1">Watch hours tracked in YouTube Studio</p>
          </div>
        </div>
        {subs >= 1000 && (
          <div className="bg-green-100 border border-green-400 rounded p-3 text-green-800 text-sm font-semibold">
            ✅ Subscriber threshold met! Check YouTube Studio for watch hours (need 4,000h).
          </div>
        )}
        {subs >= 900 && subs < 1000 && (
          <div className="bg-yellow-100 border border-yellow-400 rounded p-3 text-yellow-800 text-sm font-semibold">
            🔔 Almost there — {1000 - subs} more subscribers to go!
          </div>
        )}
      </div>

      {/* Cost Overview */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card text-center border border-gray-200">
          <p className="text-xs text-gray-500 mb-1">Videos Posted</p>
          <p className="text-3xl font-bold">{data.total_videos}</p>
        </div>
        <div className="card text-center border border-gray-200">
          <p className="text-xs text-gray-500 mb-1">Total Spend</p>
          <p className="text-3xl font-bold text-green-600">${data.cost.total_usd.toFixed(2)}</p>
          <p className="text-xs text-gray-400">~${data.cost.per_video_avg.toFixed(2)}/video</p>
        </div>
        <div className="card text-center border border-gray-200">
          <p className="text-xs text-gray-500 mb-1">Last 30 Days</p>
          <p className="text-3xl font-bold text-blue-600">${data.cost.last_30d_usd.toFixed(2)}</p>
        </div>
      </div>

      {/* Top Niches */}
      {data.top_niches.length > 0 && (
        <div className="card border border-gray-200">
          <h2 className="text-lg font-bold mb-4">Top Performing Niches</h2>
          <div className="space-y-3">
            {data.top_niches.map(([name, score], i) => {
              const maxScore = data.top_niches[0][1] || 1;
              const pct = (score / maxScore) * 100;
              return (
                <div key={name}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">#{i + 1} {name}</span>
                    <span className="text-gray-500">avg score {score.toFixed(0)}</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${pct}%`,
                        background: i === 0 ? "#7c3aed" : i === 1 ? "#2563eb" : "#059669",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          {data.pending_score > 0 && (
            <p className="text-xs text-gray-400 mt-3">
              {data.pending_score} video{data.pending_score !== 1 ? "s" : ""} awaiting analytics (videos need 72h before scoring)
            </p>
          )}
        </div>
      )}

      {/* Recent Videos */}
      {data.recent_videos.length > 0 && (
        <div className="card border border-gray-200">
          <h2 className="text-lg font-bold mb-4">Recent Videos</h2>
          <div className="space-y-3">
            {data.recent_videos.map((v) => (
              <div key={v.video_id} className="flex items-start justify-between gap-4 py-2 border-b last:border-0">
                <div className="flex-1 min-w-0">
                  <a href={v.url} target="_blank" rel="noopener noreferrer"
                     className="font-medium text-sm text-purple-700 hover:underline truncate block">
                    {v.title}
                  </a>
                  <p className="text-xs text-gray-400">{v.niche} · {new Date(v.uploaded_at).toLocaleDateString()}</p>
                </div>
                <div className="text-right shrink-0">
                  {v.score != null ? (
                    <p className="text-sm font-bold text-green-600">{v.views?.toLocaleString() ?? 0} views</p>
                  ) : (
                    <p className="text-xs text-gray-400">pending</p>
                  )}
                  {v.cost_usd != null && (
                    <p className="text-xs text-gray-400">${v.cost_usd.toFixed(3)}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.total_videos === 0 && (
        <div className="card text-center text-gray-500 border border-dashed border-gray-300">
          <p className="text-lg mb-2">No videos yet</p>
          <p className="text-sm">Run the full automation to generate your first video.</p>
          <a href="/full-auto" className="btn mt-4 inline-block">Generate First Video</a>
        </div>
      )}
    </div>
  );
}
