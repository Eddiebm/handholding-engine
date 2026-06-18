"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";

export default function MultiPlatformPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    const generate = async () => {
      try {
        setError("");
        const response = await axios.post("/api/proxy?path=/demo/multi-platform");
        setResult(response.data);
        setLoading(false);
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || "Failed to generate");
        setLoading(false);
      }
    };
    generate();
  }, []);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto text-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
        <h1 className="text-2xl font-bold mb-2">Generating Multi-Platform Content...</h1>
        <p className="text-gray-600">Creating scripts for TikTok, Reels, YouTube Shorts & LinkedIn</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="card bg-red-50 border border-red-200">
          <h1 className="text-2xl font-bold text-red-800 mb-4">Error</h1>
          <p className="text-red-700 mb-4">{error}</p>
          <button onClick={() => router.push("/multi-platform")} className="btn">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const platforms = [
    { key: "tiktok", name: "TikTok", icon: "🎵", color: "from-black to-gray-900" },
    { key: "reels", name: "Instagram Reels", icon: "📷", color: "from-pink-600 to-rose-600" },
    { key: "youtube_shorts", name: "YouTube Shorts", icon: "▶️", color: "from-red-600 to-red-700" },
    { key: "linkedin", name: "LinkedIn", icon: "💼", color: "from-blue-600 to-blue-700" }
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-2 text-purple-600">📱 Multi-Platform Content</h1>
        <p className="text-gray-600 mb-6">One idea, optimized for 4 platforms</p>

        <div className="card bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-300 mb-8">
          <h2 className="text-2xl font-bold text-purple-700 mb-2">{result?.niche}</h2>
          <p className="text-gray-700 mb-2">{result?.idea}</p>
          <p className="text-sm text-gray-600 italic">"{result?.trend_reason}"</p>
          <p className="text-sm text-purple-600 font-semibold mt-3">💡 {result?.viral_angle}</p>
        </div>
      </div>

      {/* Platform Scripts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {platforms.map((platform) => {
          const data = result?.platforms?.[platform.key];
          if (!data) return null;

          return (
            <div key={platform.key} className={`bg-gradient-to-br ${platform.color} rounded-lg p-6 text-white shadow-lg`}>
              <div className="flex items-center gap-3 mb-4">
                <span className="text-3xl">{platform.icon}</span>
                <div>
                  <h3 className="text-xl font-bold">{platform.name}</h3>
                  <p className="text-sm opacity-90">{data.duration} • {data.aspect_ratio}</p>
                </div>
              </div>

              <div className="bg-black/30 rounded-lg p-4 space-y-3 mb-4">
                <div>
                  <p className="text-xs font-semibold opacity-75 mb-1">HOOK</p>
                  <p className="text-sm leading-tight">{data.hook}</p>
                </div>

                <div>
                  <p className="text-xs font-semibold opacity-75 mb-1">SCRIPT</p>
                  <p className="text-sm leading-tight line-clamp-4">{data.script}</p>
                </div>

                <div>
                  <p className="text-xs font-semibold opacity-75 mb-1">CTA</p>
                  <p className="text-sm font-bold">{data.cta}</p>
                </div>

                {data.captions && data.captions.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold opacity-75 mb-1">CAPTIONS</p>
                    <div className="space-y-1">
                      {data.captions.map((caption: string, i: number) => (
                        <p key={i} className="text-xs opacity-90">• {caption}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <button className="flex-1 bg-white/20 hover:bg-white/30 px-3 py-2 rounded font-semibold text-sm">
                  Copy Script
                </button>
                <button className="flex-1 bg-white/20 hover:bg-white/30 px-3 py-2 rounded font-semibold text-sm">
                  Generate Video
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Platform Comparison Table */}
      <div className="card">
        <h3 className="text-2xl font-bold mb-6">📊 Platform Comparison</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-100 border-b-2 border-gray-300">
              <tr>
                <th className="text-left p-3 font-bold">Platform</th>
                <th className="text-left p-3 font-bold">Duration</th>
                <th className="text-left p-3 font-bold">Aspect Ratio</th>
                <th className="text-left p-3 font-bold">Best For</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b hover:bg-gray-50">
                <td className="p-3 font-bold">🎵 TikTok</td>
                <td className="p-3">15-60 sec</td>
                <td className="p-3">9:16</td>
                <td className="p-3">Viral growth, entertainment</td>
              </tr>
              <tr className="border-b hover:bg-gray-50">
                <td className="p-3 font-bold">📷 Instagram Reels</td>
                <td className="p-3">15-90 sec</td>
                <td className="p-3">9:16</td>
                <td className="p-3">Engagement, followers</td>
              </tr>
              <tr className="border-b hover:bg-gray-50">
                <td className="p-3 font-bold">▶️ YouTube Shorts</td>
                <td className="p-3">15-60 sec</td>
                <td className="p-3">9:16</td>
                <td className="p-3">YouTube ecosystem, subscribers</td>
              </tr>
              <tr className="hover:bg-gray-50">
                <td className="p-3 font-bold">💼 LinkedIn</td>
                <td className="p-3">30-90 sec</td>
                <td className="p-3">1:1 or 4:5</td>
                <td className="p-3">B2B, thought leadership</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Strategy */}
      <div className="card bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-300">
        <h3 className="text-2xl font-bold mb-4">🚀 Multi-Platform Strategy</h3>
        <div className="space-y-3 text-sm text-gray-800">
          <p>
            <strong>Day 1:</strong> Upload to TikTok + Reels (highest viral potential)
          </p>
          <p>
            <strong>Day 2:</strong> Post YouTube Shorts (captures YouTube subscribers)
          </p>
          <p>
            <strong>Day 3:</strong> Share on LinkedIn (B2B audience, thought leadership)
          </p>
          <p className="text-xs text-gray-600 mt-4 italic">
            One script, four platforms, maximum reach. Content gets refined based on platform algorithm & audience.
          </p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-4">
        <button onClick={() => router.push("/")} className="btn btn-secondary">
          Back to Dashboard
        </button>
        <button onClick={() => router.push("/multi-platform")} className="btn">
          Generate Another Idea
        </button>
      </div>
    </div>
  );
}
