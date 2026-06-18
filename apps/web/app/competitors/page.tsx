"use client";

import { useState, useEffect } from "react";
import { niches, competitors } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function CompetitorsPage() {
  const router = useRouter();
  const [nichList, setNicheList] = useState<any[]>([]);
  const [selectedNiche, setSelectedNiche] = useState(0);
  const [formData, setFormData] = useState({
    title_or_url: "",
    notes: "",
  });
  const [competitorList, setCompetitorList] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadNiches();
  }, []);

  const loadNiches = async () => {
    try {
      const response = await niches.list();
      setNicheList(response.data);
      if (response.data.length > 0) {
        setSelectedNiche(response.data[0].id);
        loadCompetitors(response.data[0].id);
      }
    } catch (error) {
      console.error("Failed to load niches:", error);
    }
  };

  const loadCompetitors = async (niche_id: number) => {
    try {
      const response = await competitors.list(niche_id);
      setCompetitorList(response.data);
    } catch (error) {
      console.error("Failed to load competitors:", error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await competitors.create({
        niche_id: selectedNiche,
        title_or_url: formData.title_or_url,
        notes: formData.notes,
      });
      setFormData({ title_or_url: "", notes: "" });
      loadCompetitors(selectedNiche);
    } catch (error) {
      console.error("Failed to add competitor:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleNicheChange = (niche_id: number) => {
    setSelectedNiche(niche_id);
    loadCompetitors(niche_id);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Add Competitor Videos</h1>

      {nichList.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-gray-600 mb-4">Create a niche first</p>
          <button onClick={() => router.push("/niches")} className="btn">
            Go to Niches
          </button>
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

          <form onSubmit={handleSubmit} className="card mb-8">
            <div className="space-y-4">
              <div>
                <label className="block font-semibold mb-2">YouTube URL or Title</label>
                <input
                  type="text"
                  value={formData.title_or_url}
                  onChange={(e) => setFormData({ ...formData, title_or_url: e.target.value })}
                  placeholder="Paste YouTube URL or video title"
                  className="w-full border rounded-lg p-3"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold mb-2">Notes</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="What makes this video work? What hooks does it use?"
                  className="w-full border rounded-lg p-3 h-20"
                />
              </div>

              <button type="submit" className="btn w-full" disabled={loading}>
                {loading ? "Adding..." : "Add Competitor"}
              </button>
            </div>
          </form>

          <div>
            <h2 className="text-xl font-bold mb-4">
              Added Videos ({competitorList.length})
            </h2>
            {competitorList.length === 0 ? (
              <div className="card text-gray-600">
                Add at least 5 competitor videos to analyze patterns
              </div>
            ) : (
              competitorList.map((comp: any) => (
                <div key={comp.id} className="card mb-4">
                  <h3 className="font-bold">{comp.title_or_url}</h3>
                  {comp.notes && <p className="text-sm text-gray-600 mt-2">{comp.notes}</p>}
                </div>
              ))
            )}
          </div>

          {competitorList.length >= 5 && (
            <button
              onClick={() => router.push("/ideas")}
              className="btn w-full mt-8"
            >
              Next: Generate Ideas
            </button>
          )}
        </>
      )}
    </div>
  );
}
