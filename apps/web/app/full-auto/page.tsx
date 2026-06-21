"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";

const API = "https://api.theworldagency.uk/handholding";

const STEPS = [
  "Generating niche...",
  "Researching competitors...",
  "Generating video ideas...",
  "Writing script...",
  "Building asset pack...",
  "Generating voiceover...",
  "Fetching B-roll...",
  "Generating thumbnail...",
  "Assembling video...",
];

export default function FullAutoPage() {
  const router = useRouter();
  const [step, setStep] = useState("Starting...");
  const [live, setLive] = useState<any>({});
  const [error, setError] = useState("");
  const [result, setResult] = useState<any>(null);
  const [started, setStarted] = useState(false);
  const [runKey, setRunKey] = useState(0);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!started) return;
    setStep("Starting...");
    setLive({});
    setError("");
    setResult(null);

    const run = async () => {
      try {
        const { data } = await axios.post(`${API}/demo/full-automation/start`, {});
        const jobId = data.job_id;

        pollRef.current = setInterval(async () => {
          try {
            const { data: status } = await axios.get(`${API}/demo/full-automation/status/${jobId}`);
            setStep(status.step || "Running...");
            if (status.live) setLive(status.live);
            if (status.status === "done") {
              clearInterval(pollRef.current!);
              setResult(status.result);
            } else if (status.status === "error") {
              clearInterval(pollRef.current!);
              setError(status.error || "Automation failed");
            }
          } catch (pollErr: any) {
            if (pollErr?.response?.status === 404) {
              clearInterval(pollRef.current!);
              setError("Server restarted mid-job. Please try again.");
            }
            // transient network blip — keep polling
          }
        }, 3000);
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || "Failed to start");
      }
    };

    run();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [runKey]);

  if (!started) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16 space-y-6">
        <h1 className="text-4xl font-bold">⚡ Full Auto</h1>
        <p className="text-gray-500 text-lg">Pick a niche, write a script, generate voiceover, fetch B-roll, assemble a video — all in one click.</p>
        <ul className="text-left card space-y-2 text-sm text-gray-600">
          {STEPS.map(s => <li key={s} className="flex items-center gap-2"><span className="text-gray-300">○</span>{s.replace("...", "")}</li>)}
        </ul>
        <p className="text-sm text-gray-400">~2–3 minutes · ~$0.07 per video</p>
        <button onClick={() => setStarted(true)} className="btn text-lg px-10 py-4">Generate Video</button>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="card bg-red-50 border-2 border-red-300">
          <h1 className="text-2xl font-bold text-red-900 mb-3">Automation Failed</h1>
          <p className="text-red-800 mb-4">{error}</p>
          <button onClick={() => { setStarted(false); setError(""); }} className="btn">Try Again</button>
        </div>
      </div>
    );
  }

  if (!result) {
    const currentIndex = STEPS.indexOf(step);
    return (
      <div className="max-w-4xl mx-auto space-y-6 py-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <h1 className="text-2xl font-bold">Generating your video...</h1>
          <p className="text-gray-500 text-sm mt-1">Takes 2–3 minutes</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Steps */}
          <div className="card space-y-2">
            {STEPS.map((s, i) => {
              const done = currentIndex > i;
              const active = currentIndex === i;
              return (
                <div key={s} className={`flex items-center gap-3 text-sm ${done ? "text-green-700" : active ? "text-blue-700 font-semibold" : "text-gray-400"}`}>
                  <span className="w-5 text-center flex-shrink-0">{done ? "✓" : active ? "⏳" : "○"}</span>
                  {s}
                </div>
              );
            })}
          </div>

          {/* Live content */}
          <div className="space-y-3">
            {live.niche && (
              <div className="card border-l-4 border-purple-500">
                <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-1">Niche</p>
                <p className="font-bold text-lg">{live.niche}</p>
                {live.audience && <p className="text-sm text-gray-600 mt-1">{live.audience}</p>}
                {live.monetization && <p className="text-xs text-green-700 mt-1">💰 {live.monetization}</p>}
              </div>
            )}
            {live.idea && (
              <div className="card border-l-4 border-blue-500">
                <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-1">Video Idea</p>
                <p className="font-bold">{live.idea}</p>
                {live.idea_reason && <p className="text-sm text-gray-600 mt-1">{live.idea_reason}</p>}
              </div>
            )}
            {live.hook && (
              <div className="card border-l-4 border-orange-500">
                <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-1">Hook</p>
                <p className="text-sm italic">"{live.hook}"</p>
                {live.cta && <p className="text-xs text-gray-500 mt-2">CTA: {live.cta}</p>}
              </div>
            )}
            {!live.niche && (
              <div className="card border-l-4 border-gray-200 opacity-50">
                <p className="text-sm text-gray-400">Content will appear here as it's generated...</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Result page
  const files = result.automation_files || {};
  const hasVideo = files.final_video && files.final_video !== "Not assembled";
  const hasVoice = files.voiceover && files.voiceover !== "Not generated";
  const hasThumb = files.thumbnail && files.thumbnail !== "Not generated";

  return (
    <div className="max-w-4xl mx-auto space-y-6 py-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-purple-600 mb-1">Done — ${result.cost?.total || "0.07"}</h1>
        <p className="text-gray-500">{result.niche} · {result.idea}</p>
      </div>

      {/* Video player — top and centre */}
      {hasVideo ? (
        <div className="card bg-black p-0 overflow-hidden">
          <video controls className="w-full" style={{ maxHeight: "420px" }}>
            <source src={`${API}${files.final_video}`} type="video/mp4" />
          </video>
          <div className="p-4 flex gap-3">
            <a href={`${API}${files.final_video}`} download className="btn flex-1 text-center">⬇️ Download MP4</a>
          </div>
        </div>
      ) : (
        <div className="card bg-gray-50 border-2 border-dashed border-gray-300 text-center py-8">
          <p className="text-gray-500">Video assembly failed — voiceover and thumbnail saved below</p>
        </div>
      )}

      {/* Assets row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Voiceover */}
        {hasVoice ? (
          <div className="card">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">🎙️ Voiceover</p>
            <audio controls className="w-full">
              <source src={`${API}${files.voiceover}`} type="audio/mpeg" />
            </audio>
            <a href={`${API}${files.voiceover}`} download className="text-xs text-blue-600 underline mt-2 inline-block">⬇️ Download MP3</a>
          </div>
        ) : (
          <div className="card opacity-50">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">🎙️ Voiceover</p>
            <p className="text-sm text-gray-400">Not generated</p>
          </div>
        )}

        {/* Thumbnail */}
        {hasThumb ? (
          <div className="card">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">📸 Thumbnail</p>
            <img src={`${API}${files.thumbnail}`} alt="Thumbnail" className="w-full rounded" />
          </div>
        ) : (
          <div className="card opacity-50">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">📸 Thumbnail</p>
            <p className="text-sm text-gray-400">Not generated</p>
          </div>
        )}
      </div>

      {/* Script hook */}
      <div className="card">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">🎬 B-Roll</p>
        <p className="text-sm text-gray-700">{files.broll_videos || 0} stock clips fetched from Pexels</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <button onClick={() => router.push("/")} className="btn btn-secondary">← Home</button>
        <button onClick={() => { setStarted(false); setResult(null); }} className="btn">⚡ Run Again</button>
      </div>
    </div>
  );
}
