"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.theworldagency.uk/handholding";

export default function ScriptsPage() {
  const router = useRouter();
  const [script, setScript] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadLatestScript();
  }, []);

  const loadLatestScript = async () => {
    try {
      const response = await axios.get(`/api/proxy?path=%2Fscripts%2Flatest`);
      setScript(response.data);
    } catch {
      setError("No scripts yet. Run Full Auto first.");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateNew = async () => {
    setGenerating(true);
    setError("");
    try {
      const response = await axios.post(`${API_URL}/demo/full-automation`, {}, { timeout: 180000 });
      await loadLatestScript();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Failed to generate");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <div className="max-w-2xl mx-auto py-20 text-center">Loading latest script...</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Your Script</h1>
        <button onClick={handleGenerateNew} disabled={generating} className="btn">
          {generating ? "Generating..." : "⚡ Generate New"}
        </button>
      </div>

      {error && (
        <div className="card mb-8 p-6 bg-amber-50 border-2 border-amber-300 text-center">
          <p className="text-amber-800 mb-4">{error}</p>
          <button onClick={() => router.push("/full-auto")} className="btn">Run Full Auto</button>
        </div>
      )}

      {script && (
        <>
          <div className="card mb-6 p-4 bg-blue-50 border-l-4 border-blue-600">
            <p className="text-sm text-blue-700 font-semibold">Video Idea</p>
            <p className="text-xl font-bold text-blue-900">{script.idea_title}</p>
          </div>

          <div className="card mb-6 p-4 bg-yellow-50 border-l-4 border-yellow-400">
            <h3 className="font-bold text-lg mb-2">Hook (First 10 Seconds)</h3>
            <p className="text-lg font-semibold text-yellow-900">{script.hook}</p>
          </div>

          <div className="card mb-6">
            <h3 className="font-bold text-lg mb-2">Full Script</h3>
            <div className="bg-gray-50 p-4 rounded-lg whitespace-pre-wrap text-sm max-h-96 overflow-y-auto">
              {script.full_script}
            </div>
          </div>

          {script.fact_check_flags && JSON.parse(script.fact_check_flags).length > 0 && (
            <div className="card mb-6 p-4 bg-red-50 border-l-4 border-red-400">
              <h3 className="font-bold text-red-900 mb-2">⚠️ Fact Check Needed</h3>
              <ul className="text-sm text-red-800">
                {JSON.parse(script.fact_check_flags).map((claim: string, i: number) => (
                  <li key={i}>- {claim}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="card mb-6 p-4 bg-green-50 border-l-4 border-green-400">
            <h3 className="font-bold text-green-900 mb-2">Call to Action</h3>
            <p className="text-green-900">{script.cta}</p>
          </div>

          <button onClick={() => router.push("/asset-pack")} className="btn w-full">
            Next: Create Assets →
          </button>
        </>
      )}
    </div>
  );
}
