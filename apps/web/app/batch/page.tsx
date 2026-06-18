"use client";

import { useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";

export default function BatchPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "Content Batch",
    count: 10,
    schedule_start: new Date(Date.now() + 86400000).toISOString().split("T")[0],
    schedule_frequency: "daily",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const token = localStorage.getItem("access_token");
      const response = await axios.post(
        "/api/proxy?path=/publishing/batch",
        {
          ...formData,
          schedule_start: new Date(formData.schedule_start).toISOString(),
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      alert(response.data.message);
      router.push(`/batch/${response.data.batch_id}`);
    } catch (error: any) {
      alert("Batch creation failed: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-2 text-purple-600">🚀 Batch Generation</h1>
        <p className="text-gray-600">Create multiple videos at once and schedule them</p>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-6">
        <div>
          <label className="block text-sm font-bold text-gray-900 mb-2">Batch Name</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full bg-white px-4 py-2 rounded-lg border border-gray-300 focus:border-purple-500 focus:outline-none"
            placeholder="e.g., Q4 Content Push"
          />
        </div>

        <div>
          <label className="block text-sm font-bold text-gray-900 mb-2">Number of Videos</label>
          <input
            type="number"
            min="1"
            max="30"
            value={formData.count}
            onChange={(e) => setFormData({ ...formData, count: parseInt(e.target.value) })}
            className="w-full bg-white px-4 py-2 rounded-lg border border-gray-300 focus:border-purple-500 focus:outline-none"
          />
          <p className="text-xs text-gray-600 mt-1">Max 30 videos per batch</p>
        </div>

        <div>
          <label className="block text-sm font-bold text-gray-900 mb-2">Start Posting</label>
          <input
            type="date"
            value={formData.schedule_start}
            onChange={(e) => setFormData({ ...formData, schedule_start: e.target.value })}
            className="w-full bg-white px-4 py-2 rounded-lg border border-gray-300 focus:border-purple-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-bold text-gray-900 mb-2">Posting Frequency</label>
          <select
            value={formData.schedule_frequency}
            onChange={(e) => setFormData({ ...formData, schedule_frequency: e.target.value })}
            className="w-full bg-white px-4 py-2 rounded-lg border border-gray-300 focus:border-purple-500 focus:outline-none"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="custom">Custom Schedule</option>
          </select>
        </div>

        <div className="bg-blue-50 rounded-lg p-4 border-l-4 border-blue-500">
          <p className="text-sm text-gray-800">
            <strong>Example:</strong> Create 20 videos, post daily starting tomorrow = 20 days of content
          </p>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 rounded-lg transition disabled:opacity-50"
        >
          {loading ? "Creating batch..." : "🎬 Create Batch"}
        </button>
      </form>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <p className="text-2xl mb-2">⚡</p>
          <p className="font-bold text-gray-900">Fast Generation</p>
          <p className="text-sm text-gray-600">AI generates all videos in parallel</p>
        </div>

        <div className="card">
          <p className="text-2xl mb-2">📅</p>
          <p className="font-bold text-gray-900">Auto-Schedule</p>
          <p className="text-sm text-gray-600">Posts automatically at optimal times</p>
        </div>

        <div className="card">
          <p className="text-2xl mb-2">📊</p>
          <p className="font-bold text-gray-900">Track Results</p>
          <p className="text-sm text-gray-600">Monitor views, engagement, analytics</p>
        </div>
      </div>
    </div>
  );
}
