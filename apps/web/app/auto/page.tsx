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
          {/* Cost Meter */}
          {result.cost && (
            <div className="card bg-gradient-to-r from-blue-50 to-cyan-50 border-2 border-blue-300">
              <div className="flex justify-between items-center mb-3">
                <span className="text-lg font-bold text-gray-800">💰 AI Generation Cost</span>
                <span className="text-3xl font-bold text-blue-600">${result.cost.total}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                <div
                  className="bg-gradient-to-r from-blue-500 to-cyan-500 h-3 rounded-full"
                  style={{ width: `${Math.min((result.cost.total / 0.50) * 100, 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-600">
                {result.cost.api_calls} API calls • Cost scales with content complexity
              </p>
            </div>
          )}

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

          {/* Next Steps */}
          <div className="card bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-300">
            <h2 className="text-2xl font-bold mb-6 text-amber-900">📋 Your Action Plan (Next Steps)</h2>

            <div className="space-y-4">
              <div className="flex gap-4 items-start">
                <div className="text-3xl">🎙️</div>
                <div>
                  <h3 className="font-bold text-lg mb-1">Step 1: Record Voiceover (5-10 min)</h3>
                  <p className="text-gray-700 text-sm">Read the generated script in a quiet room. Use Audacity (free) or your phone voice memo. Follow the voiceover tone instructions from your asset pack.</p>
                </div>
              </div>

              <div className="flex gap-4 items-start">
                <div className="text-3xl">🎬</div>
                <div>
                  <h3 className="font-bold text-lg mb-1">Step 2: Gather B-Roll (Varies)</h3>
                  <p className="text-gray-700 text-sm">Use the B-roll list from your asset pack. Record yourself or use stock footage from Unsplash, Pexels, or YouTube Music Library (free).</p>
                </div>
              </div>

              <div className="flex gap-4 items-start">
                <div className="text-3xl">✂️</div>
                <div>
                  <h3 className="font-bold text-lg mb-1">Step 3: Edit on Fiverr ($50-150)</h3>
                  <p className="text-gray-700 text-sm">Post a gig with your voiceover file, B-roll, and the editor brief from your asset pack. Expert editors will match the thumbnail to YouTube. Typical turnaround: 3-5 days.</p>
                </div>
              </div>

              <div className="flex gap-4 items-start">
                <div className="text-3xl">📸</div>
                <div>
                  <h3 className="font-bold text-lg mb-1">Step 4: Design Thumbnail ($5-20)</h3>
                  <p className="text-gray-700 text-sm">Order on Fiverr with your thumbnail prompt. Or use Canva Pro if you want to do it yourself. The AI prompt in your assets has everything the designer needs.</p>
                </div>
              </div>

              <div className="flex gap-4 items-start">
                <div className="text-3xl">🚀</div>
                <div>
                  <h3 className="font-bold text-lg mb-1">Step 5: Upload to YouTube (20 min)</h3>
                  <p className="text-gray-700 text-sm">Upload edited video, paste the YouTube description and title from your asset pack. Post the pinned comment immediately after going live to boost engagement.</p>
                </div>
              </div>
            </div>

            <div className="mt-6 p-4 bg-white rounded-lg border-l-4 border-green-500">
              <p className="text-sm font-semibold text-gray-900 mb-2">💡 Quick Math:</p>
              <p className="text-sm text-gray-700">
                • AI Cost: ${result.cost?.total || "0.07"} <br/>
                • Fiverr Editing: ~$100 <br/>
                • Fiverr Thumbnail: ~$10 <br/>
                • Your Time: ~8 hours <br/>
                • Revenue Potential: $100-1000+ (depending on niche & growth)
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-2 gap-4">
            <button onClick={() => router.push("/")} className="btn btn-secondary">
              View Full Details
            </button>
            <button onClick={() => router.push("/auto")} className="btn">
              Generate Another Video
            </button>
          </div>
        </>
      )}
    </div>
  );
}
