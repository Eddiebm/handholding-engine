"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";

const API = "https://api.theworldagency.uk/handholding";

const STEPS = [
  "Picking trending niche...",
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
  const [error, setError] = useState("");
  const [result, setResult] = useState<any>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const { data } = await axios.post(`${API}/demo/full-automation/start`, {});
        const jobId = data.job_id;

        pollRef.current = setInterval(async () => {
          try {
            const { data: status } = await axios.get(`${API}/demo/full-automation/status/${jobId}`);
            setStep(status.step || "Running...");
            if (status.status === "done") {
              clearInterval(pollRef.current!);
              setResult(status.result);
            } else if (status.status === "error") {
              clearInterval(pollRef.current!);
              setError(status.error || "Automation failed");
            }
          } catch {
            // polling blip — keep trying
          }
        }, 3000);
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || "Failed to start");
      }
    };

    run();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="card bg-red-50 border-2 border-red-300">
          <h1 className="text-2xl font-bold text-red-900 mb-3">⚠️ Automation Failed</h1>
          <p className="text-red-800 mb-4">{error}</p>
          <button onClick={() => router.push("/full-auto")} className="btn">Try Again</button>
        </div>
      </div>
    );
  }

  if (!result) {
    const currentIndex = STEPS.indexOf(step);
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-6"></div>
        <h1 className="text-2xl font-bold mb-2">Full Automation Running...</h1>
        <p className="text-gray-500 mb-8">Takes 2–3 minutes. You can leave this tab open.</p>
        <div className="card text-left space-y-3">
          {STEPS.map((s, i) => {
            const done = currentIndex > i;
            const active = currentIndex === i;
            return (
              <div key={s} className={`flex items-center gap-3 text-sm ${done ? "text-green-700" : active ? "text-blue-700 font-semibold" : "text-gray-400"}`}>
                <span className="w-5 text-center">
                  {done ? "✓" : active ? "⏳" : "○"}
                </span>
                {s}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-2 text-purple-600">✨ Done!</h1>
        <p className="text-gray-600">Video assets generated and ready to assemble</p>
      </div>

      <div className="card bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-300">
        <h2 className="text-2xl font-bold mb-4">📊 Summary</h2>
        <div className="grid grid-cols-2 gap-4">
          <div><p className="text-sm text-gray-600">Niche</p><p className="font-bold text-lg">{result.niche}</p></div>
          <div><p className="text-sm text-gray-600">Idea</p><p className="font-bold text-lg">{result.idea}</p></div>
          <div><p className="text-sm text-gray-600">Total Cost</p><p className="font-bold text-lg text-green-600">${result.cost?.total || "0.07"}</p></div>
          <div><p className="text-sm text-gray-600">Files</p><p className="font-bold text-lg">3 assets</p></div>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-2xl font-bold">🎬 Generated Assets</h2>

        {result.automation_files?.voiceover && result.automation_files.voiceover !== "Not generated" ? (
          <div className="card border-l-4 border-blue-500">
            <h3 className="font-bold mb-2">🎙️ AI Voiceover</h3>
            <audio controls className="w-full">
              <source src={`${API}${result.automation_files.voiceover}`} type="audio/mpeg" />
            </audio>
            <a href={`${API}${result.automation_files.voiceover}`} download className="text-sm text-blue-600 underline mt-2 inline-block">⬇️ Download MP3</a>
          </div>
        ) : (
          <div className="card border-l-4 border-gray-300 opacity-60">
            <h3 className="font-bold mb-1">🎙️ AI Voiceover</h3>
            <p className="text-sm text-gray-500">Not generated</p>
          </div>
        )}

        <div className="card border-l-4 border-green-500">
          <h3 className="font-bold mb-1">🎬 B-Roll</h3>
          <p className="text-sm text-gray-700">{result.automation_files?.broll_videos || 0} stock videos fetched from Pexels</p>
        </div>

        {result.automation_files?.thumbnail && result.automation_files.thumbnail !== "Not generated" ? (
          <div className="card border-l-4 border-orange-500">
            <h3 className="font-bold mb-2">📸 Thumbnail</h3>
            <img src={`${API}${result.automation_files.thumbnail}`} alt="Thumbnail" className="w-full rounded-lg" />
          </div>
        ) : (
          <div className="card border-l-4 border-gray-300 opacity-60">
            <h3 className="font-bold mb-1">📸 Thumbnail</h3>
            <p className="text-sm text-gray-500">Not generated</p>
          </div>
        )}

        {result.automation_files?.final_video && result.automation_files.final_video !== "Not assembled" ? (
          <div className="card border-l-4 border-green-500 bg-green-50">
            <h2 className="text-xl font-bold mb-3 text-green-700">✅ Final Video Ready</h2>
            <video controls className="w-full rounded-lg mb-4" style={{ maxHeight: "400px" }}>
              <source src={`${API}${result.automation_files.final_video}`} type="video/mp4" />
            </video>
            <a href={`${API}${result.automation_files.final_video}`} download className="btn w-full text-center block">⬇️ Download MP4</a>
          </div>
        ) : (
          <div className="card border-l-4 border-gray-300 opacity-60">
            <h3 className="font-bold mb-1">🎬 Final Video</h3>
            <p className="text-sm text-gray-500">Not assembled — voiceover required</p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <button onClick={() => router.push("/")} className="btn btn-secondary">Back to Home</button>
        <button onClick={() => { setResult(null); setStep("Starting..."); setError(""); }} className="btn">⚡ Run Again</button>
      </div>
    </div>
  );
}
