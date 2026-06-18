"use client";

import { useState } from "react";
import axios from "axios";

export default function OptimizePage() {
  const [activeTab, setActiveTab] = useState<"seo" | "hashtags" | "schedule">("seo");
  const [loading, setLoading] = useState(false);

  // SEO State
  const [seoInput, setSeoInput] = useState({ title: "", description: "", niche: "" });
  const [seoResult, setSeoResult] = useState<any>(null);

  // Hashtags State
  const [hashtagInput, setHashtagInput] = useState({ title: "", niche: "", platform: "tiktok" });
  const [hashtagResult, setHashtagResult] = useState<any>(null);

  // Schedule State
  const [scheduleInput, setScheduleInput] = useState({
    niche: "",
    platforms: ["tiktok", "reels", "youtube_shorts", "linkedin", "facebook"] as string[]
  });
  const [scheduleResult, setScheduleResult] = useState<any>(null);

  // SEO Optimization
  const optimizeSEO = async () => {
    if (!seoInput.title || !seoInput.niche) {
      alert("Please fill in title and niche");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post("/api/proxy?path=/api/seo/optimize", seoInput, {
        headers: { "Content-Type": "application/json" }
      });
      setSeoResult(response.data);
    } catch (error: any) {
      alert("SEO optimization failed: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // Generate Hashtags
  const generateHashtags = async () => {
    if (!hashtagInput.title || !hashtagInput.niche) {
      alert("Please fill in title and niche");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post("/api/proxy?path=/api/hashtags/generate", hashtagInput, {
        headers: { "Content-Type": "application/json" }
      });
      setHashtagResult(response.data);
    } catch (error: any) {
      alert("Hashtag generation failed: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // Get Posting Schedule
  const getSchedule = async () => {
    if (!scheduleInput.niche) {
      alert("Please fill in niche");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post("/api/proxy?path=/api/schedule/recommend", scheduleInput, {
        headers: { "Content-Type": "application/json" }
      });
      setScheduleResult(response.data);
    } catch (error: any) {
      alert("Schedule recommendation failed: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-2 text-purple-600">✨ Content Optimization</h1>
        <p className="text-gray-600">AI-powered SEO, hashtags, and scheduling</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b-2 border-gray-300">
        <button
          onClick={() => setActiveTab("seo")}
          className={`px-6 py-3 font-bold border-b-4 transition ${
            activeTab === "seo"
              ? "border-purple-600 text-purple-600"
              : "border-transparent text-gray-600 hover:text-gray-900"
          }`}
        >
          🔍 SEO Optimization
        </button>
        <button
          onClick={() => setActiveTab("hashtags")}
          className={`px-6 py-3 font-bold border-b-4 transition ${
            activeTab === "hashtags"
              ? "border-purple-600 text-purple-600"
              : "border-transparent text-gray-600 hover:text-gray-900"
          }`}
        >
          #️⃣ Hashtags
        </button>
        <button
          onClick={() => setActiveTab("schedule")}
          className={`px-6 py-3 font-bold border-b-4 transition ${
            activeTab === "schedule"
              ? "border-purple-600 text-purple-600"
              : "border-transparent text-gray-600 hover:text-gray-900"
          }`}
        >
          📅 Posting Schedule
        </button>
      </div>

      {/* SEO Tab */}
      {activeTab === "seo" && (
        <div className="space-y-6">
          <div className="card bg-gradient-to-r from-blue-50 to-cyan-50 border-2 border-blue-300">
            <h2 className="text-2xl font-bold mb-6">🔍 YouTube SEO Optimization</h2>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Video Title</label>
                <input
                  type="text"
                  value={seoInput.title}
                  onChange={(e) => setSeoInput({ ...seoInput, title: e.target.value })}
                  placeholder="Your current video title"
                  className="w-full bg-white px-4 py-2 rounded-lg border border-gray-300 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Description</label>
                <textarea
                  value={seoInput.description}
                  onChange={(e) => setSeoInput({ ...seoInput, description: e.target.value })}
                  placeholder="Your current video description"
                  rows={4}
                  className="w-full bg-white px-4 py-2 rounded-lg border border-gray-300 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Niche</label>
                <input
                  type="text"
                  value={seoInput.niche}
                  onChange={(e) => setSeoInput({ ...seoInput, niche: e.target.value })}
                  placeholder="e.g., Personal Finance, Fitness, Tech Reviews"
                  className="w-full bg-white px-4 py-2 rounded-lg border border-gray-300 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <button
                onClick={optimizeSEO}
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition"
              >
                {loading ? "Optimizing..." : "🚀 Optimize for SEO"}
              </button>
            </div>

            {seoResult && (
              <div className="bg-white rounded-lg p-6 border-l-4 border-green-500">
                <h3 className="text-lg font-bold text-green-700 mb-4">✅ SEO Optimization Results</h3>

                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">🎯 Optimized Title</p>
                    <p className="font-bold text-gray-900 text-lg">{seoResult.seo_optimization.optimized_title}</p>
                  </div>

                  <div>
                    <p className="text-sm text-gray-600 mb-1">📝 Optimized Description (First 200 chars)</p>
                    <p className="text-gray-800">{seoResult.seo_optimization.optimized_description.substring(0, 200)}...</p>
                  </div>

                  <div>
                    <p className="text-sm text-gray-600 mb-2">🏷️ Key Topics</p>
                    <div className="flex flex-wrap gap-2">
                      {seoResult.seo_optimization.key_topics?.map((topic: string, i: number) => (
                        <span key={i} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-semibold">
                          {topic}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="text-sm text-gray-600 mb-1">📊 SEO Score</p>
                    <div className="flex items-center gap-3">
                      <div className="w-full bg-gray-300 rounded-full h-3">
                        <div
                          className="bg-green-500 h-3 rounded-full"
                          style={{ width: `${seoResult.seo_optimization.seo_score}%` }}
                        />
                      </div>
                      <p className="font-bold text-lg text-green-600">{seoResult.seo_optimization.seo_score}/100</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Hashtags Tab */}
      {activeTab === "hashtags" && (
        <div className="space-y-6">
          <div className="card bg-gradient-to-r from-pink-50 to-rose-50 border-2 border-pink-300">
            <h2 className="text-2xl font-bold mb-6">#️⃣ AI Hashtag Generation</h2>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Video Title</label>
                <input
                  type="text"
                  value={hashtagInput.title}
                  onChange={(e) => setHashtagInput({ ...hashtagInput, title: e.target.value })}
                  placeholder="Your video title"
                  className="w-full bg-white px-4 py-2 rounded-lg border border-gray-300 focus:border-pink-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Niche</label>
                <input
                  type="text"
                  value={hashtagInput.niche}
                  onChange={(e) => setHashtagInput({ ...hashtagInput, niche: e.target.value })}
                  placeholder="e.g., Fitness, Tech, Gaming"
                  className="w-full bg-white px-4 py-2 rounded-lg border border-gray-300 focus:border-pink-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Platform</label>
                <select
                  value={hashtagInput.platform}
                  onChange={(e) => setHashtagInput({ ...hashtagInput, platform: e.target.value })}
                  className="w-full bg-white px-4 py-2 rounded-lg border border-gray-300 focus:border-pink-500 focus:outline-none"
                >
                  <option value="tiktok">🎵 TikTok</option>
                  <option value="reels">📷 Instagram Reels</option>
                  <option value="youtube_shorts">▶️ YouTube Shorts</option>
                  <option value="linkedin">💼 LinkedIn</option>
                  <option value="facebook">👨‍👩‍👧‍👦 Facebook</option>
                </select>
              </div>

              <button
                onClick={generateHashtags}
                disabled={loading}
                className="w-full bg-pink-600 hover:bg-pink-700 text-white font-bold py-3 rounded-lg transition"
              >
                {loading ? "Generating..." : "✨ Generate Hashtags"}
              </button>
            </div>

            {hashtagResult && (
              <div className="bg-white rounded-lg p-6 border-l-4 border-pink-500 space-y-4">
                <div>
                  <p className="text-sm text-gray-600 mb-2">🏷️ Recommended Hashtags</p>
                  <div className="flex flex-wrap gap-2">
                    {hashtagResult.hashtags.hashtags?.map((tag: string, i: number) => (
                      <span key={i} className="bg-pink-100 text-pink-800 px-3 py-1 rounded-full font-semibold text-sm">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                {hashtagResult.hashtags.trending_hashtags && (
                  <div>
                    <p className="text-sm text-gray-600 mb-2">🔥 Trending Hashtags</p>
                    <div className="flex flex-wrap gap-2">
                      {hashtagResult.hashtags.trending_hashtags.map((tag: string, i: number) => (
                        <span key={i} className="bg-red-100 text-red-800 px-3 py-1 rounded-full font-semibold text-sm">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {hashtagResult.hashtags.branded_hashtag && (
                  <div>
                    <p className="text-sm text-gray-600 mb-2">💎 Branded Hashtag</p>
                    <p className="font-bold text-lg text-purple-600">{hashtagResult.hashtags.branded_hashtag}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Schedule Tab */}
      {activeTab === "schedule" && (
        <div className="space-y-6">
          <div className="card bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300">
            <h2 className="text-2xl font-bold mb-6">📅 Posting Schedule Recommendation</h2>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Niche</label>
                <input
                  type="text"
                  value={scheduleInput.niche}
                  onChange={(e) => setScheduleInput({ ...scheduleInput, niche: e.target.value })}
                  placeholder="Your niche"
                  className="w-full bg-white px-4 py-2 rounded-lg border border-gray-300 focus:border-green-500 focus:outline-none"
                />
              </div>

              <button
                onClick={getSchedule}
                disabled={loading}
                className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-lg transition"
              >
                {loading ? "Analyzing..." : "📊 Get Schedule"}
              </button>
            </div>

            {scheduleResult && (
              <div className="space-y-4">
                {Object.entries(scheduleResult.schedule).map(([platform, data]: any) => (
                  <div key={platform} className="bg-white rounded-lg p-4 border-l-4 border-green-500">
                    <h4 className="font-bold text-gray-900 capitalize mb-3">{platform}</h4>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-gray-600">Best Days</p>
                        <p className="font-semibold text-gray-900">{data.best_days.join(", ")}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Best Times</p>
                        <p className="font-semibold text-gray-900">{data.best_times.join(", ")}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Frequency</p>
                        <p className="font-semibold text-gray-900">{data.frequency}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Reason</p>
                        <p className="text-xs text-gray-700">{data.reason}</p>
                      </div>
                    </div>
                  </div>
                ))}

                {scheduleResult.strategy && (
                  <div className="bg-blue-50 rounded-lg p-4 border-l-4 border-blue-500">
                    <p className="font-bold text-blue-900 mb-2">💡 Strategy Tips</p>
                    <ul className="text-sm text-gray-800 space-y-1">
                      <li>• {scheduleResult.strategy.daily_strategy}</li>
                      <li>• {scheduleResult.strategy.weekly_strategy}</li>
                      <li>• {scheduleResult.strategy.growth_tip}</li>
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
