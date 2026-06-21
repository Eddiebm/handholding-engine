"use client";
import { useEffect, useState } from "react";

const API = "https://api.theworldagency.uk/handholding";

export default function WatchPage() {
  const [job, setJob] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/demo/full-automation/latest`)
      .then(r => r.json())
      .then(d => { setJob(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-gray-400">Loading...</div>;
  if (!job?.result) return (
    <div className="max-w-xl mx-auto text-center py-20">
      <h1 className="text-2xl font-bold mb-3">No video yet</h1>
      <p className="text-gray-500 mb-6">Generate your first video on the Full Auto page.</p>
      <a href="/full-auto" className="btn">⚡ Go to Full Auto</a>
    </div>
  );

  const files = job.result.automation_files || {};
  const videoUrl = files.final_video ? `${API}${files.final_video}` : null;
  const thumbUrl = files.thumbnail ? `${API}${files.thumbnail}` : null;
  const audioUrl = files.voiceover ? `${API}${files.voiceover}` : null;

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-8">
      <div>
        <h1 className="text-3xl font-bold">{job.result.idea}</h1>
        <p className="text-gray-500 mt-1">{job.result.niche} · ${job.result.cost?.total?.toFixed(2) || "0.07"} · {files.broll_videos || 0} B-roll clips</p>
      </div>

      {videoUrl && (
        <div className="card p-0 overflow-hidden">
          <video controls className="w-full" style={{ maxHeight: "480px" }}>
            <source src={videoUrl} type="video/mp4" />
            Your browser does not support video playback.
          </video>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {thumbUrl && (
          <div className="card">
            <p className="text-xs text-gray-400 mb-2 uppercase tracking-wide">Thumbnail</p>
            <img src={thumbUrl} alt="thumbnail" className="w-full rounded" />
          </div>
        )}
        <div className="card space-y-3">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Downloads</p>
          {videoUrl && (
            <a href={videoUrl} download className="btn w-full text-center block">⬇️ Download MP4</a>
          )}
          {audioUrl && (
            <a href={audioUrl} download className="btn w-full text-center block" style={{background:"#f3f4f6",color:"#111"}}>⬇️ Download Voiceover</a>
          )}
          <a href="/full-auto" className="block text-center text-sm text-purple-600 underline mt-2">Generate another →</a>
        </div>
      </div>

      {job.live?.hook && (
        <div className="card">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Hook</p>
          <p className="text-gray-800 italic">"{job.live.hook}"</p>
        </div>
      )}
    </div>
  );
}
