"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";

export default function CalendarPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [calendar, setCalendar] = useState<any>(null);
  const [showScheduleModal, setShowScheduleModal] = useState(false);

  useEffect(() => {
    loadCalendar();
  }, []);

  const loadCalendar = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await axios.get("/api/proxy?path=/publishing/calendar", {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCalendar(response.data);
    } catch (error) {
      console.error("Failed to load calendar:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto text-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading content calendar...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-4xl font-bold text-gray-900">📅 Content Calendar</h1>
        <button onClick={() => router.push("/batch")} className="btn">
          + New Batch
        </button>
      </div>

      {/* Platform Overview */}
      {calendar && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {["youtube", "tiktok", "instagram", "linkedin", "facebook"].map((platform) => (
            <div key={platform} className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-lg p-4 border-2 border-blue-300">
              <p className="font-bold text-gray-900 capitalize mb-2">{platform}</p>
              <p className="text-3xl font-bold text-blue-600">
                {calendar.calendar?.[platform]?.length || 0}
              </p>
              <p className="text-xs text-gray-600">videos scheduled</p>
            </div>
          ))}
        </div>
      )}

      {/* Calendar Grid */}
      <div className="card">
        <h2 className="text-2xl font-bold mb-6">📆 Next 30 Days</h2>

        {calendar?.calendar && Object.keys(calendar.calendar).length > 0 ? (
          <div className="space-y-6">
            {Object.entries(calendar.calendar).map(([platform, posts]: any) => (
              <div key={platform}>
                <h3 className="font-bold text-lg text-gray-900 capitalize mb-3">{platform}</h3>
                <div className="space-y-2">
                  {posts.map((post: any) => (
                    <div
                      key={post.id}
                      className="bg-gray-50 rounded-lg p-4 border-l-4 border-purple-500 hover:shadow-md transition"
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <p className="font-bold text-gray-900">{post.title}</p>
                          <p className="text-sm text-gray-600">
                            {new Date(post.scheduled_time).toLocaleString()}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <span
                            className={`px-3 py-1 rounded text-xs font-bold ${
                              post.status === "published"
                                ? "bg-green-100 text-green-800"
                                : "bg-yellow-100 text-yellow-800"
                            }`}
                          >
                            {post.status}
                          </span>
                          {post.platform_url && (
                            <a
                              href={post.platform_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-3 py-1 bg-blue-100 text-blue-800 rounded text-xs font-bold hover:bg-blue-200"
                            >
                              View
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <p className="mb-4">No scheduled videos yet</p>
            <button onClick={() => router.push("/batch")} className="btn">
              Create Batch to Get Started
            </button>
          </div>
        )}
      </div>

      {/* Strategy */}
      <div className="card bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-300">
        <h3 className="text-xl font-bold mb-4">💡 Recommended Strategy</h3>
        <ul className="space-y-2 text-sm text-gray-800">
          <li>✓ Post TikTok/Reels daily for maximum virality (algorithm favors frequency)</li>
          <li>✓ Post YouTube Shorts 3-5x/week (quality over quantity)</li>
          <li>✓ Post LinkedIn 2-3x/week on weekdays (B2B engagement)</li>
          <li>✓ Use Batch Generation to create 10-30 videos at once, schedule across the month</li>
          <li>✓ Monitor analytics weekly and adjust based on performance</li>
        </ul>
      </div>
    </div>
  );
}
