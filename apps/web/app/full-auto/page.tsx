"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

// Direct backend URL for media files (video/audio) to avoid streaming through Next.js
const BACKEND = process.env.NEXT_PUBLIC_API_URL || "";

function mediaUrl(path: string | undefined): string | null {
  if (!path || path === "Not generated" || path === "Not assembled") return null;
  if (path.startsWith("http")) return path;
  return `${BACKEND}${path}`;
}

export default function FullAutoPage() {
  const router = useRouter();
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState("starting");
  const [step, setStep] = useState("Starting...");
  const [live, setLive] = useState<any>({});
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Start the job on mount
  useEffect(() => {
    fetch("/api/proxy?path=%2Fdemo%2Ffull-automation%2Fstart", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.job_id) setJobId(d.job_id);
        else setError(d.detail || d.error || "Failed to start job");
      })
      .catch((e) => setError(e.message));
  }, []);

  // Poll status once we have a job ID
  useEffect(() => {
    if (!jobId) return;

    const poll = () => {
      fetch(`/api/proxy?path=%2Fdemo%2Ffull-automation%2Fstatus%2F${jobId}`)
        .then((r) => {
          if (r.status === 404) { setError("Job expired (server restarted) — click Try Again"); return null; }
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((d) => {
          if (!d) return;
          setStep(d.step || "");
          setLive(d.live || {});
          setStatus(d.status);
          if (d.status === "done") setResult(d.result);
          else if (d.status === "error") setError(d.error || "Unknown error");
        })
        .catch(() => {}); // ignore transient network errors
    };

    poll();
    pollRef.current = setInterval(poll, 4000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId]);

  // Stop polling when terminal state reached
  useEffect(() => {
    if (status === "done" || status === "error") {
      if (pollRef.current) clearInterval(pollRef.current);
    }
  }, [status]);

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="card bg-red-50 border-2 border-red-300">
          <h1 className="text-2xl font-bold text-red-900 mb-4">Generation Failed</h1>
          <p className="text-red-800 mb-6">{error}</p>
          <button onClick={() => router.push("/full-auto")} className="btn">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (status !== "done") {
    return (
      <div className="max-w-4xl mx-auto text-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
        <h1 className="text-2xl font-bold mb-2">Generating Your Video...</h1>
        <p className="text-gray-500 mb-6 text-sm">
          Takes 3–5 minutes. Don&apos;t close this tab.
        </p>

        <div className="card bg-blue-50 border-2 border-blue-300 text-left">
          <p className="text-lg font-semibold text-blue-900 mb-4">
            {step || "Initialising..."}
          </p>
          {live.niche && (
            <p className="text-sm mb-1">
              📊 Niche: <strong>{live.niche}</strong>
            </p>
          )}
          {live.idea && (
            <p className="text-sm mb-1">
              💡 Idea: <strong>{live.idea}</strong>
            </p>
          )}
          {live.hook && (
            <p className="text-sm text-gray-600 italic mt-3 border-l-2 border-blue-300 pl-3">
              &ldquo;{live.hook.slice(0, 150)}&hellip;&rdquo;
            </p>
          )}
        </div>
      </div>
    );
  }

  // Done
  const files = result?.automation_files || {};
  const videoUrl = mediaUrl(files.final_video);
  const shortUrl = mediaUrl(files.short_video);
  const audioUrl = mediaUrl(files.voiceover);
  const thumbUrl = mediaUrl(files.thumbnail);

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-2 text-purple-600">
          ✨ Video Ready!
        </h1>
        <p className="text-gray-600">
          {result?.niche} — {result?.idea}
        </p>
      </div>

      {/* Summary bar */}
      <div className="card bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-300">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-sm text-gray-600">Niche</p>
            <p className="font-bold">{result?.niche}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">B-roll clips</p>
            <p className="font-bold">{files.broll_videos ?? "—"}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Cost</p>
            <p className="font-bold text-green-600">
              ${result?.cost?.total?.toFixed(2) ?? "—"}
            </p>
          </div>
        </div>
      </div>

      {/* Final video */}
      {videoUrl ? (
        <div className="card border-l-4 border-green-500 bg-green-50">
          <h2 className="text-xl font-bold mb-3 text-green-700">🎬 Final Video</h2>
          <video
            controls
            className="w-full rounded-lg mb-4"
            style={{ maxHeight: "400px" }}
          >
            <source src={videoUrl} type="video/mp4" />
          </video>
          <div className="flex gap-3">
            <a href={videoUrl} download className="btn flex-1 text-center">
              ⬇️ Download MP4
            </a>
            {shortUrl && (
              <a href={shortUrl} download className="btn btn-secondary flex-1 text-center">
                ⬇️ Download Short
              </a>
            )}
          </div>
        </div>
      ) : (
        <div className="card border-l-4 border-amber-400 bg-amber-50">
          <h2 className="text-xl font-bold text-amber-900">⚠️ Video not assembled</h2>
          <p className="text-sm text-amber-700 mt-1">{files.final_video}</p>
        </div>
      )}

      {/* Thumbnail */}
      {thumbUrl && (
        <div className="card border-l-4 border-orange-500">
          <h3 className="font-bold mb-2">📸 Thumbnail</h3>
          <img src={thumbUrl} alt="Thumbnail" className="w-full rounded-lg" />
        </div>
      )}

      {/* Voiceover */}
      {audioUrl && (
        <div className="card border-l-4 border-blue-500">
          <h3 className="font-bold mb-2">🎙️ Voiceover</h3>
          <audio controls className="w-full">
            <source src={audioUrl} type="audio/mpeg" />
          </audio>
        </div>
      )}

      {/* Actions */}
      <div className="grid grid-cols-2 gap-4">
        <button onClick={() => router.push("/")} className="btn btn-secondary">
          Back to Home
        </button>
        <button onClick={() => router.push("/full-auto")} className="btn">
          Generate Another
        </button>
      </div>
    </div>
  );
}
