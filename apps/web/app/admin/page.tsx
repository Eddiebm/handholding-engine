"use client";

import { useState, useEffect } from "react";
import axios from "axios";

interface Video {
  id: number;
  title: string;
  platform: string;
  framework: string;
  status: string;
  cost: number;
  views: number;
  engagement: number;
  created_at: string;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<any>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [usage, setUsage] = useState<any>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      const [statsRes, videosRes, usageRes, analyticsRes] = await Promise.all([
        axios.get("/api/proxy?path=/admin/stats"),
        axios.get("/api/proxy?path=/admin/videos"),
        axios.get("/api/proxy?path=/admin/usage"),
        axios.get("/api/proxy?path=/admin/analytics"),
      ]);

      setStats(statsRes.data);
      setVideos(videosRes.data.videos);
      setUsage(usageRes.data);
      setAnalytics(analyticsRes.data);
    } catch (error) {
      console.error("Failed to load dashboard:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto text-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-4xl font-bold text-gray-900">📊 Dashboard</h1>
        <button onClick={loadDashboard} className="btn btn-secondary">
          🔄 Refresh
        </button>
      </div>

      {/* Key Metrics */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-lg p-6 border-2 border-blue-300">
            <p className="text-sm text-gray-600 mb-2">Total Videos</p>
            <p className="text-4xl font-bold text-blue-600">{stats.total_videos}</p>
            <p className="text-xs text-gray-600 mt-2">Generated videos</p>
          </div>

          <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-6 border-2 border-green-300">
            <p className="text-sm text-gray-600 mb-2">Total Cost</p>
            <p className="text-4xl font-bold text-green-600">${stats.total_cost}</p>
            <p className="text-xs text-gray-600 mt-2">${stats.avg_cost_per_video}/video avg</p>
          </div>

          <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-6 border-2 border-purple-300">
            <p className="text-sm text-gray-600 mb-2">Total Views</p>
            <p className="text-4xl font-bold text-purple-600">{stats.total_views.toLocaleString()}</p>
            <p className="text-xs text-gray-600 mt-2">{stats.total_views > 0 ? Math.round(stats.total_views / Math.max(stats.total_videos, 1)) : 0}/video avg</p>
          </div>

          <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-lg p-6 border-2 border-amber-300">
            <p className="text-sm text-gray-600 mb-2">Est. Earnings</p>
            <p className="text-4xl font-bold text-amber-600">${stats.estimated_earnings}</p>
            <p className="text-xs text-gray-600 mt-2">Based on views</p>
          </div>
        </div>
      )}

      {/* Platform Breakdown */}
      {stats && (
        <div className="card">
          <h2 className="text-2xl font-bold mb-6">📱 Performance by Platform</h2>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {Object.entries(stats.platforms).map(([platform, data]: any) => (
              <div key={platform} className="bg-gray-50 rounded-lg p-4 border-l-4 border-blue-500">
                <p className="font-bold text-gray-900 capitalize mb-3">{platform}</p>
                <div className="space-y-2 text-sm">
                  <div>
                    <p className="text-gray-600">Videos</p>
                    <p className="text-2xl font-bold text-blue-600">{data.count}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Views</p>
                    <p className="text-lg font-bold text-purple-600">{data.views.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Engagement</p>
                    <p className="text-lg font-bold text-green-600">{data.engagement.toLocaleString()}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Usage Metrics */}
      {usage && (
        <div className="card">
          <h2 className="text-2xl font-bold mb-6">📈 API Usage (Last 30 Days)</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-2">Total API Calls</p>
              <p className="text-3xl font-bold text-blue-600">{usage.total_api_calls}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-2">Total Cost</p>
              <p className="text-3xl font-bold text-green-600">${usage.total_cost}</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-2">Daily Average</p>
              <p className="text-3xl font-bold text-purple-600">${usage.avg_daily_cost}</p>
            </div>
          </div>
        </div>
      )}

      {/* Best Performing Content */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card">
            <h2 className="text-2xl font-bold mb-6">⭐ Best Framework</h2>
            {analytics.best_framework ? (
              <div className="bg-gradient-to-br from-yellow-50 to-amber-50 rounded-lg p-6 border-2 border-yellow-300">
                <p className="text-sm text-gray-600 mb-2">Most Effective Style</p>
                <p className="text-3xl font-bold text-amber-700 capitalize mb-4">{analytics.best_framework}</p>
                <div className="space-y-2 text-sm">
                  {analytics.framework_performance[analytics.best_framework] && (
                    <>
                      <p className="text-gray-700">
                        <strong>Videos:</strong> {analytics.framework_performance[analytics.best_framework].count}
                      </p>
                      <p className="text-gray-700">
                        <strong>Avg Views:</strong> {Math.round(analytics.framework_performance[analytics.best_framework].avg_views).toLocaleString()}
                      </p>
                    </>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-gray-500">No data yet</p>
            )}
          </div>

          <div className="card">
            <h2 className="text-2xl font-bold mb-6">🎯 Best Niche</h2>
            {analytics.best_niche ? (
              <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-6 border-2 border-green-300">
                <p className="text-sm text-gray-600 mb-2">Highest Performing Niche</p>
                <p className="text-3xl font-bold text-green-700 capitalize mb-4">{analytics.best_niche}</p>
                <div className="space-y-2 text-sm">
                  {analytics.niche_performance[analytics.best_niche] && (
                    <>
                      <p className="text-gray-700">
                        <strong>Videos:</strong> {analytics.niche_performance[analytics.best_niche].count}
                      </p>
                      <p className="text-gray-700">
                        <strong>Total Views:</strong> {analytics.niche_performance[analytics.best_niche].total_views.toLocaleString()}
                      </p>
                    </>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-gray-500">No data yet</p>
            )}
          </div>
        </div>
      )}

      {/* Video History */}
      <div className="card">
        <h2 className="text-2xl font-bold mb-6">📹 Recent Videos</h2>
        {videos.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100 border-b-2">
                <tr>
                  <th className="text-left p-3 font-bold">Title</th>
                  <th className="text-left p-3 font-bold">Platform</th>
                  <th className="text-left p-3 font-bold">Framework</th>
                  <th className="text-left p-3 font-bold">Status</th>
                  <th className="text-left p-3 font-bold">Cost</th>
                  <th className="text-left p-3 font-bold">Views</th>
                  <th className="text-left p-3 font-bold">Created</th>
                </tr>
              </thead>
              <tbody>
                {videos.slice(0, 20).map((video) => (
                  <tr key={video.id} className="border-b hover:bg-gray-50">
                    <td className="p-3">{video.title}</td>
                    <td className="p-3 capitalize font-semibold text-blue-600">{video.platform}</td>
                    <td className="p-3 capitalize text-purple-600">{video.framework}</td>
                    <td className="p-3">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${
                        video.status === 'published' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {video.status}
                      </span>
                    </td>
                    <td className="p-3 font-bold text-green-600">${video.cost}</td>
                    <td className="p-3 font-bold text-blue-600">{video.views.toLocaleString()}</td>
                    <td className="p-3 text-xs text-gray-600">
                      {new Date(video.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No videos yet. Start generating!</p>
        )}
      </div>
    </div>
  );
}
