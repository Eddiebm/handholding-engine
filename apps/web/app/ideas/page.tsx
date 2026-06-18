"use client";

import { useState, useEffect } from "react";
import { niches, ideas } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function IdeasPage() {
  const router = useRouter();
  const [nichList, setNicheList] = useState<any[]>([]);
  const [selectedNiche, setSelectedNiche] = useState(0);
  const [ideaList, setIdeaList] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [scoring, setScoring] = useState<number | null>(null);

  useEffect(() => {
    loadNiches();
  }, []);

  const loadNiches = async () => {
    try {
      const response = await niches.list();
      setNicheList(response.data);
      if (response.data.length > 0) {
        setSelectedNiche(response.data[0].id);
        loadIdeas(response.data[0].id);
      }
    } catch (error) {
      console.error("Failed to load niches:", error);
    }
  };

  const loadIdeas = async (niche_id: number) => {
    try {
      const response = await ideas.list(niche_id);
      setIdeaList(response.data);
    } catch (error) {
      console.error("Failed to load ideas:", error);
    }
  };

  const handleNicheChange = (niche_id: number) => {
    setSelectedNiche(niche_id);
    loadIdeas(niche_id);
  };

  const handleGenerateIdeas = async () => {
    setLoading(true);
    try {
      const response = await ideas.generate(selectedNiche);
      setIdeaList(response.data);
    } catch (error) {
      console.error("Failed to generate ideas:", error);
      alert("Failed to generate ideas. Make sure API is running and you have OpenAI key set.");
    } finally {
      setLoading(false);
    }
  };

  const handleScoreIdea = async (idea_id: number) => {
    setScoring(idea_id);
    try {
      const response = await ideas.score(idea_id);
      setIdeaList(
        ideaList.map((idea: any) => (idea.id === idea_id ? response.data : idea))
      );
    } catch (error) {
      console.error("Failed to score idea:", error);
      alert("Failed to score idea.");
    } finally {
      setScoring(null);
    }
  };

  const handleSelectIdea = async (idea_id: number) => {
    try {
      await ideas.select(idea_id);
      router.push("/scripts");
    } catch (error) {
      console.error("Failed to select idea:", error);
    }
  };

  const topIdea = ideaList.length > 0
    ? [...ideaList].sort((a: any, b: any) => b.total_score - a.total_score)[0]
    : null;

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Generate & Score Ideas</h1>

      {nichList.length === 0 ? (
        <div className="card">
          <p className="text-gray-600 mb-4">Create a niche and add competitors first</p>
        </div>
      ) : (
        <>
          <div className="card mb-8">
            <label className="block font-semibold mb-2">Select Niche</label>
            <select
              value={selectedNiche}
              onChange={(e) => handleNicheChange(parseInt(e.target.value))}
              className="w-full border rounded-lg p-3"
            >
              {nichList.map((niche: any) => (
                <option key={niche.id} value={niche.id}>
                  {niche.name}
                </option>
              ))}
            </select>
          </div>

          {ideaList.length === 0 ? (
            <button
              onClick={handleGenerateIdeas}
              className="btn w-full text-lg py-4 mb-8"
              disabled={loading}
            >
              {loading ? "Generating..." : "Generate 10 Ideas"}
            </button>
          ) : (
            <>
              <div className="mb-8">
                <h2 className="text-xl font-bold mb-4">Your Ideas</h2>
                {topIdea && (
                  <div className="card border-4 border-green-500 mb-4">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-bold text-lg text-green-700">⭐ Top Idea</h3>
                      <span className="text-2xl font-bold text-green-600">
                        {(topIdea.total_score || 0).toFixed(1)}/10
                      </span>
                    </div>
                    <p className="font-semibold text-lg mb-2">{topIdea.title}</p>
                    <p className="text-sm text-gray-700 mb-4">{topIdea.reason}</p>

                    {topIdea.total_score > 0 && (
                      <div className="grid grid-cols-2 gap-2 text-xs mb-4">
                        <div>Demand: {topIdea.demand_score}/10</div>
                        <div>Clickability: {topIdea.clickability_score}/10</div>
                        <div>Monetization: {topIdea.monetization_score}/10</div>
                        <div>Production: {topIdea.production_ease_score}/10</div>
                      </div>
                    )}

                    <button
                      onClick={() => handleSelectIdea(topIdea.id)}
                      className="btn w-full"
                    >
                      Pick This Idea
                    </button>
                  </div>
                )}

                <div className="space-y-3">
                  {ideaList.map((idea: any) => (
                    <div key={idea.id} className="card">
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-bold">{idea.title}</h3>
                        {idea.total_score > 0 && (
                          <span className="font-bold text-blue-600">
                            {idea.total_score.toFixed(1)}/10
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-700 mb-3">{idea.reason}</p>

                      {idea.total_score === 0 && (
                        <button
                          onClick={() => handleScoreIdea(idea.id)}
                          className="btn-secondary w-full"
                          disabled={scoring === idea.id}
                        >
                          {scoring === idea.id ? "Scoring..." : "Score This Idea"}
                        </button>
                      )}

                      {idea.total_score > 0 && (
                        <button
                          onClick={() => handleSelectIdea(idea.id)}
                          className="btn-secondary w-full"
                        >
                          Use This Idea
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={handleGenerateIdeas}
                className="btn-secondary w-full"
                disabled={loading}
              >
                {loading ? "Generating..." : "Generate More Ideas"}
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
}
