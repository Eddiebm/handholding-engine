"use client";

import { useState, useEffect } from "react";

interface Channel {
  channel_id: string;
  display_name: string;
  niche_keywords: string[];
  active: boolean;
  has_token: boolean;
}

const NICHE_COLORS: Record<string, string> = {
  finance: "bg-green-100 text-green-800 border-green-300",
  legal: "bg-blue-100 text-blue-800 border-blue-300",
  tech: "bg-purple-100 text-purple-800 border-purple-300",
  business: "bg-orange-100 text-orange-800 border-orange-300",
  health: "bg-pink-100 text-pink-800 border-pink-300",
};

const NICHE_ICONS: Record<string, string> = {
  finance: "💰",
  legal: "⚖️",
  tech: "🤖",
  business: "📈",
  health: "🏥",
};

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<string | null>(null);
  const [describing, setDescribing] = useState<string | null>(null);
  const [describeResults, setDescribeResults] = useState<Record<string, string>>({});
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/proxy?path=%2Fchannels")
      .then((r) => r.json())
      .then((d) => {
        setChannels(Array.isArray(d) ? d : []);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load channels");
        setLoading(false);
      });
  }, []);

  const toggleActive = async (channelId: string, currentActive: boolean) => {
    setToggling(channelId);
    try {
      const res = await fetch(
        `/api/proxy?path=${encodeURIComponent(`/channels/${channelId}`)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active: !currentActive }),
        }
      );
      const data = await res.json();
      if (data.ok) {
        setChannels((prev) =>
          prev.map((c) =>
            c.channel_id === channelId ? { ...c, active: data.active } : c
          )
        );
      }
    } catch {
      setError("Toggle failed");
    } finally {
      setToggling(null);
    }
  };

  const setDescription = async (channelId: string) => {
    setDescribing(channelId);
    setDescribeResults((p) => ({ ...p, [channelId]: "Setting..." }));
    try {
      const res = await fetch(
        `/api/proxy?path=${encodeURIComponent(`/channels/${channelId}/describe`)}`,
        { method: "POST" }
      );
      const data = await res.json();
      if (data.ok) {
        setDescribeResults((p) => ({ ...p, [channelId]: "✅ Description set!" }));
      } else {
        setDescribeResults((p) => ({
          ...p,
          [channelId]: `❌ ${data.detail || "Failed"}`,
        }));
      }
    } catch {
      setDescribeResults((p) => ({ ...p, [channelId]: "❌ Network error" }));
    } finally {
      setDescribing(null);
    }
  };

  const activeCount = Array.isArray(channels) ? channels.filter((c) => c.active).length : 0;
  const tokenCount = Array.isArray(channels) ? channels.filter((c) => c.has_token).length : 0;

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto text-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600 mx-auto mb-4" />
        <p className="text-gray-500">Loading channels...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">YouTube Channels</h1>
          <p className="text-gray-500 text-sm mt-1">
            {tokenCount}/{channels.length} channels have OAuth tokens ·{" "}
            {activeCount} active
          </p>
        </div>
        <div className="flex gap-3 text-sm">
          <span className="px-3 py-1 rounded-full bg-green-100 text-green-800 font-medium">
            {activeCount} Active
          </span>
          <span className="px-3 py-1 rounded-full bg-gray-100 text-gray-600 font-medium">
            {channels.length - activeCount} Inactive
          </span>
        </div>
      </div>

      {error && (
        <div className="card bg-red-50 border border-red-300 text-red-800">
          {error}
        </div>
      )}

      <div className="grid gap-4">
        {channels.map((ch) => {
          const colorClass =
            NICHE_COLORS[ch.channel_id] ||
            "bg-gray-100 text-gray-800 border-gray-300";
          const icon = NICHE_ICONS[ch.channel_id] || "📺";
          const descResult = describeResults[ch.channel_id];

          return (
            <div
              key={ch.channel_id}
              className={`card border-2 ${
                ch.active ? "border-gray-200" : "border-dashed border-gray-300 opacity-70"
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-3xl">{icon}</span>
                  <div className="min-w-0">
                    <h2 className="text-xl font-bold">{ch.display_name}</h2>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${colorClass}`}
                      >
                        {ch.channel_id}
                      </span>
                      {ch.has_token ? (
                        <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-green-50 text-green-700 border border-green-200">
                          ✅ OAuth ready
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                          ⚠️ Needs OAuth token
                        </span>
                      )}
                      {!ch.active && (
                        <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-500 border border-gray-200">
                          Paused
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-2 shrink-0">
                  <button
                    onClick={() => toggleActive(ch.channel_id, ch.active)}
                    disabled={toggling === ch.channel_id || !ch.has_token}
                    className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      ch.active
                        ? "bg-gray-200 hover:bg-gray-300 text-gray-700"
                        : "bg-purple-600 hover:bg-purple-700 text-white"
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {toggling === ch.channel_id
                      ? "..."
                      : ch.active
                      ? "Pause"
                      : "Activate"}
                  </button>

                  {ch.has_token && (
                    <button
                      onClick={() => setDescription(ch.channel_id)}
                      disabled={describing === ch.channel_id}
                      className="px-4 py-1.5 rounded-lg text-sm font-medium bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 disabled:opacity-50"
                    >
                      {describing === ch.channel_id ? "Setting..." : "Set About"}
                    </button>
                  )}
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-1.5">
                {ch.niche_keywords.slice(0, 8).map((kw) => (
                  <span
                    key={kw}
                    className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                  >
                    {kw}
                  </span>
                ))}
                {ch.niche_keywords.length > 8 && (
                  <span className="px-2 py-0.5 text-gray-400 text-xs">
                    +{ch.niche_keywords.length - 8} more
                  </span>
                )}
              </div>

              {descResult && (
                <p className="mt-2 text-sm text-gray-600">{descResult}</p>
              )}

              {!ch.has_token && (
                <p className="mt-3 text-xs text-amber-600 bg-amber-50 rounded px-3 py-2 border border-amber-100">
                  This channel needs an OAuth refresh token before it can post videos.
                  Create the YouTube channel first, then run the OAuth flow.
                </p>
              )}
            </div>
          );
        })}
      </div>

      <div className="card bg-gray-50 border border-gray-200 text-sm text-gray-600">
        <p className="font-semibold mb-1">How routing works</p>
        <p>
          Each video automation picks a niche, then the system matches the niche
          name against channel keyword lists. The first active channel whose
          keywords match gets the upload. Finance Freedom gets finance/investing
          content, Legal Clarity gets law/legal content, and so on.
        </p>
      </div>
    </div>
  );
}
