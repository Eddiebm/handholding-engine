"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.theworldagency.uk/handholding";

type ClipType = "intro" | "outro";

interface ClipState {
  recording: boolean;
  blob: Blob | null;
  url: string | null;
  uploaded: boolean;
  seconds: number;
}

const defaultClip = (): ClipState => ({
  recording: false,
  blob: null,
  url: null,
  uploaded: false,
  seconds: 0,
});

export default function VoicePage() {
  const [voices, setVoices] = useState<any[]>([]);
  const [loadingVoices, setLoadingVoices] = useState(true);
  const [clips, setClips] = useState<Record<ClipType, ClipState>>({
    intro: defaultClip(),
    outro: defaultClip(),
  });
  const [hasClips, setHasClips] = useState({ intro: false, outro: false });
  const [uploading, setUploading] = useState<ClipType | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const activeClipRef = useRef<ClipType | null>(null);

  useEffect(() => {
    loadVoices();
    checkHasClips();
  }, []);

  const loadVoices = async () => {
    try {
      const res = await axios.get("/api/proxy?path=%2Fvoices%2Flist");
      setVoices(res.data.voices || []);
    } catch {}
    finally { setLoadingVoices(false); }
  };

  const checkHasClips = async () => {
    try {
      const res = await axios.get(`${API_URL}/voices/has-clips`);
      setHasClips(res.data);
      if (res.data.intro) setClips(c => ({ ...c, intro: { ...c.intro, uploaded: true } }));
      if (res.data.outro) setClips(c => ({ ...c, outro: { ...c.outro, uploaded: true } }));
    } catch {}
  };

  const startRecording = async (type: ClipType) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      activeClipRef.current = type;

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        const clip = activeClipRef.current!;
        setClips(c => ({ ...c, [clip]: { ...c[clip], recording: false, blob, url, uploaded: false } }));
        if (timerRef.current) clearInterval(timerRef.current);
      };

      recorder.start();
      setClips(c => ({ ...c, [type]: { ...c[type], recording: true, seconds: 0, blob: null, url: null } }));

      timerRef.current = setInterval(() => {
        setClips(c => {
          const sec = c[type].seconds + 1;
          if (sec >= 15) stopRecording();
          return { ...c, [type]: { ...c[type], seconds: sec } };
        });
      }, 1000);
    } catch (err) {
      alert("Microphone access denied. Please allow mic access in your browser.");
    }
  };

  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    mediaRecorderRef.current?.stop();
  };

  const uploadClip = async (type: ClipType) => {
    const clip = clips[type];
    if (!clip.blob) return;
    setUploading(type);
    try {
      const formData = new FormData();
      formData.append("clip_type", type);
      formData.append("file", clip.blob, `${type}.webm`);
      await axios.post(`${API_URL}/voices/record-clip`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setClips(c => ({ ...c, [type]: { ...c[type], uploaded: true } }));
      setHasClips(h => ({ ...h, [type]: true }));
    } catch {
      alert("Upload failed. Try again.");
    } finally {
      setUploading(null);
    }
  };

  const deleteClip = async (type: ClipType) => {
    try {
      await axios.delete(`${API_URL}/voices/record-clip/${type}`);
      setClips(c => ({ ...c, [type]: defaultClip() }));
      setHasClips(h => ({ ...h, [type]: false }));
    } catch {}
  };

  const ClipRecorder = ({ type, label, example }: { type: ClipType; label: string; example: string }) => {
    const clip = clips[type];
    const saved = hasClips[type] && clip.uploaded;

    return (
      <div className={`card border-2 ${saved ? "border-green-400 bg-green-50" : "border-gray-200"}`}>
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="font-bold text-lg">{label}</h3>
            <p className="text-sm text-gray-500">5–15 seconds</p>
          </div>
          {saved && (
            <span className="text-xs bg-green-600 text-white px-2 py-1 rounded">✓ Saved</span>
          )}
        </div>

        <div className="bg-gray-100 rounded p-3 mb-4 text-sm text-gray-700 italic">
          "{example}"
        </div>

        {clip.url && (
          <audio controls className="w-full mb-3">
            <source src={clip.url} />
          </audio>
        )}

        {clip.recording ? (
          <div className="flex items-center gap-3 mb-3">
            <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
            <span className="text-red-600 font-semibold">Recording... {clip.seconds}s</span>
            <button onClick={stopRecording} className="btn bg-red-600 hover:bg-red-700 ml-auto">
              Stop
            </button>
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => startRecording(type)}
              className="btn flex-1"
              disabled={!!uploading}
            >
              {clip.url ? "Re-record" : "🎤 Record"}
            </button>
            {clip.blob && !clip.uploaded && (
              <button
                onClick={() => uploadClip(type)}
                disabled={uploading === type}
                className="btn bg-green-600 hover:bg-green-700 flex-1"
              >
                {uploading === type ? "Saving..." : "✓ Save"}
              </button>
            )}
            {saved && (
              <button
                onClick={() => deleteClip(type)}
                className="btn bg-gray-400 hover:bg-gray-500"
              >
                Delete
              </button>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">🎙️ Voice Setup</h1>
      <p className="text-gray-600 mb-8">Record a short intro and outro in your real voice — spliced onto every AI-generated video to avoid YouTube flags.</p>

      {/* Human clips status */}
      <div className={`card mb-6 border-2 ${hasClips.intro && hasClips.outro ? "border-green-400 bg-green-50" : "border-amber-300 bg-amber-50"}`}>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xl">{hasClips.intro && hasClips.outro ? "✅" : "⚠️"}</span>
          <h2 className="font-bold">
            {hasClips.intro && hasClips.outro
              ? "Human clips active — all videos will use your voice"
              : "Record intro + outro to protect your channel"}
          </h2>
        </div>
        <div className="flex gap-4 text-sm mt-2">
          <span className={hasClips.intro ? "text-green-700" : "text-gray-500"}>
            {hasClips.intro ? "✓ Intro recorded" : "○ No intro"}
          </span>
          <span className={hasClips.outro ? "text-green-700" : "text-gray-500"}>
            {hasClips.outro ? "✓ Outro recorded" : "○ No outro"}
          </span>
        </div>
      </div>

      <div className="space-y-6 mb-10">
        <ClipRecorder
          type="intro"
          label="Intro (5–10 sec)"
          example="Hey, what's up guys, welcome back to the channel—"
        />
        <ClipRecorder
          type="outro"
          label="Outro (5–10 sec)"
          example="Drop a comment below, subscribe if you're new, see you in the next one."
        />
      </div>

      {/* ElevenLabs Voice */}
      <div className="card bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-300 mb-6">
        <h2 className="text-xl font-bold mb-2">🤖 AI Voice (ElevenLabs)</h2>
        <p className="text-sm text-gray-700 mb-4">
          Your cloned voice handles the full script. The recordings above are spliced at the start and end.
        </p>
        {!loadingVoices && (
          voices.length === 0 ? (
            <p className="text-sm text-gray-500">No ElevenLabs voice configured yet. Run Full Auto once to clone.</p>
          ) : (
            <div className="space-y-2">
              {voices.map((v) => (
                <div key={v.id} className="flex justify-between items-center bg-white rounded p-3">
                  <span className="font-medium">{v.name}</span>
                  {v.is_default && <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">Active</span>}
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}
