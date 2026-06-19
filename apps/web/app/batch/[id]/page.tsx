"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import axios from "axios";

export default function BatchDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [batch, setBatch] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (params.id) {
      axios
        .get(`/api/proxy?path=%2Fpublishing%2Fbatch%2F${params.id}`)
        .then((r) => setBatch(r.data))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [params.id]);

  if (loading) return <div className="max-w-2xl mx-auto py-20 text-center">Loading batch...</div>;
  if (!batch) return <div className="max-w-2xl mx-auto py-20 text-center text-red-600">Batch not found.</div>;

  const freqLabel: Record<string, string> = { daily: "Daily", weekly: "Weekly", biweekly: "Every 2 weeks" };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => router.push("/batch")} className="text-gray-500 hover:text-gray-700">← Back</button>
        <h1 className="text-3xl font-bold">{batch.name}</h1>
      </div>

      <div className="card">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">Videos planned</p>
            <p className="text-2xl font-bold">{batch.count}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Frequency</p>
            <p className="text-2xl font-bold">{freqLabel[batch.schedule_frequency] || batch.schedule_frequency}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Starts</p>
            <p className="font-semibold">{new Date(batch.schedule_start).toLocaleDateString()}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Status</p>
            <span className="inline-block bg-yellow-100 text-yellow-800 text-sm font-semibold px-3 py-1 rounded-full capitalize">
              {batch.status}
            </span>
          </div>
        </div>
      </div>

      <div className="card bg-blue-50 border-2 border-blue-200">
        <h2 className="font-bold text-lg mb-2">Next steps</h2>
        <ol className="text-sm text-gray-700 space-y-2 list-decimal list-inside">
          <li>Run <strong>⚡ Full Auto</strong> to generate the first video</li>
          <li>Review the script and assets</li>
          <li>Download the final video and upload to YouTube</li>
          <li>Repeat {batch.count - 1} more times on your {batch.schedule_frequency} schedule</li>
        </ol>
      </div>

      <button onClick={() => router.push("/full-auto")} className="btn w-full">
        ⚡ Generate First Video
      </button>
    </div>
  );
}
