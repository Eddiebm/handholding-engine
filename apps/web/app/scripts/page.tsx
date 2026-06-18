"use client";

import { useState, useEffect } from "react";
import { ideas, scripts } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function ScriptsPage() {
  const router = useRouter();
  const [selectedIdea, setSelectedIdea] = useState<any>(null);
  const [script, setScript] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(true);

  useEffect(() => {
    findSelectedIdea();
  }, []);

  const findSelectedIdea = async () => {
    try {
      // In a real app, we'd track the selected idea. For MVP, we'll show the first selected one
      setSearchLoading(false);
    } catch (error) {
      console.error("Failed to find selected idea:", error);
      setSearchLoading(false);
    }
  };

  const handleGenerateScript = async () => {
    if (!selectedIdea) return;

    setLoading(true);
    try {
      const response = await scripts.generate(selectedIdea.id);
      setScript(response.data);
    } catch (error) {
      console.error("Failed to generate script:", error);
      alert("Failed to generate script. Make sure API is running.");
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (script) {
      router.push("/asset-pack");
    }
  };

  if (searchLoading) {
    return <div className="max-w-2xl mx-auto">Loading...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Generate Your Script</h1>

      <div className="card mb-8 p-8 text-center border-4 border-blue-600">
        <p className="text-gray-600 mb-4">Select an idea first in the Ideas page</p>
        <button
          onClick={() => router.push("/ideas")}
          className="btn-secondary"
        >
          Go to Ideas
        </button>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleGenerateScript();
        }}
        className="card mb-8"
      >
        <div className="space-y-4">
          <div>
            <label className="block font-semibold mb-2">Idea Title (Example)</label>
            <input
              type="text"
              value="How to Save $10,000 in 30 Days"
              disabled
              className="w-full border rounded-lg p-3 bg-gray-100"
            />
            <p className="text-xs text-gray-500 mt-2">
              In a live app, this would be your selected idea
            </p>
          </div>

          <button
            type="submit"
            className="btn w-full"
            disabled={loading}
            onClick={handleGenerateScript}
          >
            {loading ? "Writing Script..." : "Generate Script"}
          </button>
        </div>
      </form>

      {script && (
        <>
          <div className="card mb-8">
            <h2 className="text-2xl font-bold mb-4">Your Script</h2>

            <div className="mb-6 p-4 bg-yellow-50 border-l-4 border-yellow-400">
              <h3 className="font-bold text-lg mb-2">Hook (First 10 Seconds)</h3>
              <p className="text-lg font-semibold text-yellow-900">{script.hook}</p>
            </div>

            <div className="mb-6">
              <h3 className="font-bold text-lg mb-2">Full Script</h3>
              <div className="bg-gray-50 p-4 rounded-lg whitespace-pre-wrap text-sm">
                {script.full_script}
              </div>
            </div>

            {script.fact_check_flags && JSON.parse(script.fact_check_flags).length > 0 && (
              <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-400">
                <h3 className="font-bold text-red-900 mb-2">⚠️ Fact Check Needed</h3>
                <ul className="text-sm text-red-800">
                  {JSON.parse(script.fact_check_flags).map((claim: string, i: number) => (
                    <li key={i}>- {claim}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mb-6 p-4 bg-blue-50 border-l-4 border-blue-400">
              <h3 className="font-bold text-blue-900 mb-2">Call to Action</h3>
              <p className="text-blue-900">{script.cta}</p>
            </div>

            <button
              onClick={handleNext}
              className="btn w-full"
            >
              Next: Create Assets
            </button>
          </div>
        </>
      )}
    </div>
  );
}
