"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";

export default function AutoPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    const generate = async () => {
      try {
        const response = await axios.post("/api/proxy?path=/demo/auto-workflow");
        setResult(response.data);
        setLoading(false);
      } catch (err: any) {
        setError(err.message || "Failed to generate workflow");
        setLoading(false);
      }
    };
    generate();
  }, []);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto text-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <h1 className="text-2xl font-bold mb-2">Generating Your Complete Video Strategy...</h1>
        <p className="text-gray-600">Picking trending niche, generating ideas, writing script, creating assets</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="card bg-red-50 border border-red-200">
          <h1 className="text-2xl font-bold text-red-800 mb-4">Error</h1>
          <p className="text-red-700 mb-4">{error}</p>
          <button onClick={() => router.push("/auto")} className="btn">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold mb-2 text-green-600">✓ Video Strategy Generated!</h1>
        <p className="text-gray-600">Everything is ready to start creating</p>
      </div>

      {result && (
        <>
          {/* Niche */}
          <div className="card border-l-4 border-blue-500">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-2xl font-bold text-blue-600">{result.niche_name}</h2>
                <p className="text-sm text-gray-500">Niche ID: {result.niche_id}</p>
              </div>
              <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-semibold">Niche</span>
            </div>
          </div>

          {/* Best Idea */}
          <div className="card border-l-4 border-green-500">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-2xl font-bold text-green-600">{result.idea_title}</h2>
                <p className="text-sm text-gray-500">Video Idea ID: {result.idea_id}</p>
              </div>
              <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">Top Idea</span>
            </div>
          </div>

          {/* Script */}
          <div className="card border-l-4 border-purple-500">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-xl font-bold text-purple-600">10-Minute Script Written</h2>
                <p className="text-sm text-gray-500">Script ID: {result.script_id}</p>
              </div>
              <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm font-semibold">Script</span>
            </div>
            <p className="text-gray-600">Complete video script with hooks, main content, and CTAs</p>
          </div>

          {/* Asset Pack */}
          <div className="card border-l-4 border-orange-500">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-xl font-bold text-orange-600">Asset Pack Generated</h2>
                <p className="text-sm text-gray-500">Asset Pack ID: {result.asset_pack_id}</p>
              </div>
              <span className="bg-orange-100 text-orange-800 px-3 py-1 rounded-full text-sm font-semibold">Assets</span>
            </div>
            <p className="text-gray-600">Thumbnail prompts, B-roll lists, voiceover instructions, YouTube description</p>
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-2 gap-4 mt-8">
            <button onClick={() => router.push("/")} className="btn btn-secondary">
              View Dashboard
            </button>
            <button onClick={() => router.push("/auto")} className="btn">
              Generate Another
            </button>
          </div>
        </>
      )}
    </div>
  );
}
