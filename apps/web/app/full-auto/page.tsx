"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";

export default function FullAutoPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [result, setResult] = useState<any>(null);
  const [progress, setProgress] = useState("");

  useEffect(() => {
    const generate = async () => {
      try {
        setProgress("🤖 Generating workflow...");
        const response = await axios.post("/api/proxy?path=%2Fdemo%2Ffull-automation");
        setResult(response.data);
        setLoading(false);
        setProgress("");
      } catch (err: any) {
        setError(
          err.response?.data?.detail ||
          err.message ||
          "Failed to run full automation"
        );
        setLoading(false);
      }
    };
    generate();
  }, []);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto text-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
        <h1 className="text-2xl font-bold mb-2">Full Automation Running...</h1>
        <p className="text-gray-600 mb-6">This generates voiceover, fetches B-roll, and creates thumbnail</p>
        <div className="card bg-blue-50 border-2 border-blue-300">
          <p className="text-lg font-semibold text-blue-900 mb-4">{progress || "Processing..."}</p>
          <div className="space-y-2 text-left text-sm text-gray-700">
            <p>✓ Analyzing trending niche</p>
            <p>✓ Generating video script</p>
            <p>⏳ Creating AI voiceover (ElevenLabs)</p>
            <p>⏳ Fetching stock B-roll (Pexels)</p>
            <p>⏳ Generating thumbnail (DALL-E)</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="card bg-amber-50 border-2 border-amber-300">
          <h1 className="text-2xl font-bold text-amber-900 mb-4">⚙️ Setup Required</h1>
          <p className="text-amber-800 mb-4">{error}</p>

          <div className="bg-white p-4 rounded-lg mb-4">
            <h2 className="font-bold mb-3">To enable full automation, set these env vars:</h2>
            <div className="font-mono text-sm bg-gray-100 p-3 rounded space-y-2">
              <p>ELEVENLABS_API_KEY=xxx (free tier at elevenlabs.io)</p>
              <p>PEXELS_API_KEY=xxx (free at pexels.com/api)</p>
            </div>
          </div>

          <button onClick={() => router.push("/auto")} className="btn w-full">
            ← Back to Basic Auto
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-2 text-purple-600">✨ Full Automation Complete!</h1>
        <p className="text-gray-600">Video assets generated and ready to assemble</p>
      </div>

      {result && (
        <>
          {/* Summary */}
          <div className="card bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-300">
            <h2 className="text-2xl font-bold mb-4">📊 Automation Summary</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">Niche</p>
                <p className="font-bold text-lg">{result.niche}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Idea</p>
                <p className="font-bold text-lg">{result.idea}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Cost</p>
                <p className="font-bold text-lg text-green-600">${result.cost?.total || "0.07"}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Files Generated</p>
                <p className="font-bold text-lg">3 files</p>
              </div>
            </div>
          </div>

          {/* Generated Assets */}
          <div className="space-y-4">
            <h2 className="text-2xl font-bold">🎬 Generated Assets</h2>

            {result.automation_files?.voiceover && result.automation_files.voiceover !== "Not generated" ? (
              <div className="card border-l-4 border-blue-500">
                <h3 className="font-bold mb-2">🎙️ AI Voiceover</h3>
                <p className="text-sm text-gray-700 mb-3">Generated with ElevenLabs</p>
                <audio controls className="w-full">
                  <source src={result.automation_files.voiceover} type="audio/mpeg" />
                </audio>
              </div>
            ) : (
              <div className="card border-l-4 border-gray-400 opacity-70">
                <h3 className="font-bold mb-2">🎙️ AI Voiceover</h3>
                <p className="text-sm text-gray-600">{result.automation_files?.voiceover || "Not generated (set ELEVENLABS_API_KEY)"}</p>
              </div>
            )}

            <div className="card border-l-4 border-green-500">
              <h3 className="font-bold mb-2">🎬 B-Roll Videos</h3>
              <p className="text-sm text-gray-700">{result.automation_files?.broll_videos || 0} stock videos fetched from Pexels</p>
            </div>

            {result.automation_files?.thumbnail && result.automation_files.thumbnail !== "Not generated" ? (
              <div className="card border-l-4 border-orange-500">
                <h3 className="font-bold mb-2">📸 AI Thumbnail</h3>
                <img src={result.automation_files.thumbnail} alt="Thumbnail" className="w-full rounded-lg" />
              </div>
            ) : (
              <div className="card border-l-4 border-gray-400 opacity-70">
                <h3 className="font-bold mb-2">📸 AI Thumbnail</h3>
                <p className="text-sm text-gray-600">{result.automation_files?.thumbnail || "Requires DALL-E quota"}</p>
              </div>
            )}
          </div>

          {/* Next Step */}
          <div className="card bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300">
            <h2 className="text-2xl font-bold mb-4 text-green-900">⚡ Next: Assemble Video</h2>
            <div className="bg-white p-4 rounded-lg font-mono text-sm overflow-x-auto mb-4">
              <p className="text-gray-800">ffmpeg -i voiceover.mp3 -i broll.mp4 -i thumbnail.png output.mp4</p>
            </div>
            <p className="text-green-900 text-sm">
              All files are ready. Use FFmpeg or DaVinci Resolve to assemble the final video with transitions, music, and effects. Then upload to YouTube!
            </p>
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-2 gap-4">
            <button onClick={() => router.push("/")} className="btn btn-secondary">
              Back to Home
            </button>
            <button onClick={() => router.push("/full-auto")} className="btn">
              Run Again
            </button>
          </div>
        </>
      )}
    </div>
  );
}
