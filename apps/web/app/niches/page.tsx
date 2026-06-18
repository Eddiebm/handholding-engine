"use client";

import { useState, useEffect } from "react";
import { niches } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function NichesPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: "",
    audience: "",
    monetization_angle: "",
    notes: "",
  });
  const [nichList, setNicheList] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadNiches();
  }, []);

  const loadNiches = async () => {
    try {
      const response = await niches.list();
      setNicheList(response.data);
    } catch (error) {
      console.error("Failed to load niches:", error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await niches.create(formData);
      setFormData({ name: "", audience: "", monetization_angle: "", notes: "" });
      loadNiches();
      router.push("/competitors");
    } catch (error) {
      console.error("Failed to create niche:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Create Your Niche</h1>

      <form onSubmit={handleSubmit} className="card mb-8">
        <div className="space-y-4">
          <div>
            <label className="block font-semibold mb-2">Niche Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Personal Finance for Beginners"
              className="w-full border rounded-lg p-3"
              required
            />
          </div>

          <div>
            <label className="block font-semibold mb-2">Target Audience</label>
            <input
              type="text"
              value={formData.audience}
              onChange={(e) => setFormData({ ...formData, audience: e.target.value })}
              placeholder="e.g., 18-35 year olds wanting financial independence"
              className="w-full border rounded-lg p-3"
              required
            />
          </div>

          <div>
            <label className="block font-semibold mb-2">Monetization Angle</label>
            <input
              type="text"
              value={formData.monetization_angle}
              onChange={(e) => setFormData({ ...formData, monetization_angle: e.target.value })}
              placeholder="e.g., Ad revenue + affiliate products"
              className="w-full border rounded-lg p-3"
              required
            />
          </div>

          <div>
            <label className="block font-semibold mb-2">Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Any additional thoughts..."
              className="w-full border rounded-lg p-3 h-24"
            />
          </div>

          <button type="submit" className="btn w-full" disabled={loading}>
            {loading ? "Creating..." : "Create Niche"}
          </button>
        </div>
      </form>

      {nichList.length > 0 && (
        <div>
          <h2 className="text-xl font-bold mb-4">Your Niches</h2>
          {nichList.map((niche: any) => (
            <div key={niche.id} className="card mb-4">
              <h3 className="font-bold text-lg">{niche.name}</h3>
              <p className="text-sm text-gray-600">Audience: {niche.audience}</p>
              <p className="text-sm text-gray-600">Monetization: {niche.monetization_angle}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
