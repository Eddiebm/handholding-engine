"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.theworldagency.uk/handholding";

type ClipType = "intro" | "outro";
interface ClipState {
  recording: boolean;
  blob: Blob | null;
  url: string | null;
  uploaded: boolean;
  seconds: number;
}
const defaultClip = (): ClipState => ({ recording: false, blob: null, url: null, uploaded: false, seconds: 0 });

interface ClonedVoice {
  id: number;
  name: string;
  voice_id: string;
  created_at: string;
}

export default function VoicePage() {
  const [clips, setClips] = useState<Record<ClipType, ClipState>>({ intro: defaultClip(), outro: defaultClip() });
  const [hasClips, setHasClips] = useState({ intro: false, outro: false });
  const [uploading, setUploading] = useState<ClipType | null>(null);

  // XTTS voice sample state (primary, free)
  const [xttsHasSample, setXttsHasSample] = useState(false);
  const [xttsFile, setXttsFile] = useState<File | null>(null);
  const [xttsBlob, setXttsBlob] = useState<Blob | null>(null);
  const [xttsUrl, setXttsUrl] = useState<string | null>(null);
  const [xttsRecording, setXttsRecording] = useState(false);
  const [xttsSeconds, setXttsSeconds] = useState(0);
  const [xttsUploading, setXttsUploading] = useState(false);
  const [xttsStatus, setXttsStatus] = useState("");
  const xttsMediaRef = useRef<MediaRecorder | null>(null);
  const xttsChunksRef = useRef<BlobPart[]>([]);
  const xttsTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ElevenLabs cloned voice state (fallback)
  const [clonedVoice, setClonedVoice] = useState<ClonedVoice | null>(null);
  const [cloneFile, setCloneFile] = useState<File | null>(null);
  const [cloneName, setCloneName] = useState("My Voice");
  const [cloning, setCloning] = useState(false);
  const [cloneStatus, setCloneStatus] = useState("");
  const [cloneRecording, setCloneRecording] = useState(false);
  const [cloneSeconds, setCloneSeconds] = useState(0);
  const [cloneBlob, setCloneBlob] = useState<Blob | null>(null);
  const [cloneUrl, setCloneUrl] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeClipRef = useRef<ClipType | null>(null);
  const cloneMediaRef = useRef<MediaRecorder | null>(null);
  const cloneChunksRef = useRef<BlobPart[]>([]);
  const cloneTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    checkHasClips();
    loadClonedVoice();
    loadXttsSampleStatus();
  }, []);

  const loadXttsSampleStatus = async () => {
    try {
      const { data } = await axios.get(`${API}/voices/sample`);
      setXttsHasSample(data.has_sample);
    } catch {}
  };

  const startXttsRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      xttsChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      xttsMediaRef.current = recorder;
      recorder.ondataavailable = e => { if (e.data.size > 0) xttsChunksRef.current.push(e.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(xttsChunksRef.current, { type: "audio/webm" });
        setXttsBlob(blob);
        setXttsUrl(URL.createObjectURL(blob));
        setXttsRecording(false);
        if (xttsTimerRef.current) clearInterval(xttsTimerRef.current);
      };
      recorder.start();
      setXttsRecording(true);
      setXttsSeconds(0);
      setXttsBlob(null);
      setXttsUrl(null);
      xttsTimerRef.current = setInterval(() => setXttsSeconds(s => s + 1), 1000);
    } catch { alert("Microphone access denied."); }
  };

  const stopXttsRecording = () => {
    if (xttsTimerRef.current) clearInterval(xttsTimerRef.current);
    xttsMediaRef.current?.stop();
  };

  const submitXttsSample = async () => {
    const src = xttsFile || (xttsBlob ? new File([xttsBlob], "voice.webm", { type: "audio/webm" }) : null);
    if (!src) return;
    setXttsUploading(true);
    setXttsStatus("Uploading voice sample...");
    try {
      const form = new FormData();
      form.append("file", src);
      await axios.post(`${API}/voices/sample`, form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 60000,
      });
      setXttsHasSample(true);
      setXttsStatus("Voice sample saved! All videos will use your cloned voice.");
      setXttsFile(null);
      setXttsBlob(null);
      setXttsUrl(null);
    } catch (e: any) {
      setXttsStatus("Upload failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setXttsUploading(false);
    }
  };

  const deleteXttsSample = async () => {
    if (!confirm("Remove your voice sample?")) return;
    try {
      await axios.delete(`${API}/voices/sample`);
      setXttsHasSample(false);
      setXttsStatus("Voice sample removed.");
    } catch {}
  };

  const loadClonedVoice = async () => {
    try {
      const { data } = await axios.get(`${API}/voices/cloned`);
      if (data.cloned) setClonedVoice(data.voice);
    } catch {}
  };

  const checkHasClips = async () => {
    try {
      const res = await axios.get(`${API}/voices/has-clips`);
      setHasClips(res.data);
      if (res.data.intro) setClips(c => ({ ...c, intro: { ...c.intro, uploaded: true } }));
      if (res.data.outro) setClips(c => ({ ...c, outro: { ...c.outro, uploaded: true } }));
    } catch {}
  };

  // ── Clone recording ──────────────────────────────────────────────────────────
  const startCloneRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      cloneChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      cloneMediaRef.current = recorder;
      recorder.ondataavailable = e => { if (e.data.size > 0) cloneChunksRef.current.push(e.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(cloneChunksRef.current, { type: "audio/webm" });
        setCloneBlob(blob);
        setCloneUrl(URL.createObjectURL(blob));
        setCloneRecording(false);
        if (cloneTimerRef.current) clearInterval(cloneTimerRef.current);
      };
      recorder.start();
      setCloneRecording(true);
      setCloneSeconds(0);
      setCloneBlob(null);
      setCloneUrl(null);
      cloneTimerRef.current = setInterval(() => setCloneSeconds(s => s + 1), 1000);
    } catch {
      alert("Microphone access denied.");
    }
  };

  const stopCloneRecording = () => {
    if (cloneTimerRef.current) clearInterval(cloneTimerRef.current);
    cloneMediaRef.current?.stop();
  };

  const submitClone = async () => {
    const audioSource = cloneFile || (cloneBlob ? new File([cloneBlob], "voice.webm", { type: "audio/webm" }) : null);
    if (!audioSource) return;
    setCloning(true);
    setCloneStatus("Uploading to ElevenLabs...");
    try {
      const form = new FormData();
      form.append("name", cloneName);
      form.append("file", audioSource);
      const { data } = await axios.post(`${API}/voices/clone`, form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 180000,
      });
      setClonedVoice({ id: data.voice_db_id, name: cloneName, voice_id: data.voice_id, created_at: new Date().toISOString() });
      setCloneStatus("Voice cloned! All videos will now use your voice.");
      setCloneFile(null);
      setCloneBlob(null);
      setCloneUrl(null);
    } catch (e: any) {
      setCloneStatus("Clone failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setCloning(false);
    }
  };

  const deleteClone = async () => {
    if (!confirm("Remove your cloned voice? Future videos will use OpenAI TTS.")) return;
    try {
      await axios.delete(`${API}/voices/cloned`);
      setClonedVoice(null);
      setCloneStatus("Cloned voice removed.");
    } catch {}
  };

  // ── Intro/outro clips ─────────────────────────────────────────────────────
  const startRecording = async (type: ClipType) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      activeClipRef.current = type;
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const clip = activeClipRef.current!;
        setClips(c => ({ ...c, [clip]: { ...c[clip], recording: false, blob, url: URL.createObjectURL(blob), uploaded: false } }));
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
    } catch { alert("Microphone access denied."); }
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
      const form = new FormData();
      form.append("clip_type", type);
      form.append("file", clip.blob, `${type}.webm`);
      await axios.post(`${API}/voices/record-clip`, form, { headers: { "Content-Type": "multipart/form-data" } });
      setClips(c => ({ ...c, [type]: { ...c[type], uploaded: true } }));
      setHasClips(h => ({ ...h, [type]: true }));
    } catch { alert("Upload failed."); }
    finally { setUploading(null); }
  };

  const deleteClip = async (type: ClipType) => {
    try {
      await axios.delete(`${API}/voices/record-clip/${type}`);
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
          {saved && <span className="text-xs bg-green-600 text-white px-2 py-1 rounded">Saved</span>}
        </div>
        <div className="bg-gray-100 rounded p-3 mb-4 text-sm text-gray-700 italic">"{example}"</div>
        {clip.url && <audio controls className="w-full mb-3"><source src={clip.url} /></audio>}
        {clip.recording ? (
          <div className="flex items-center gap-3 mb-3">
            <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
            <span className="text-red-600 font-semibold">Recording... {clip.seconds}s</span>
            <button onClick={stopRecording} className="btn bg-red-600 hover:bg-red-700 ml-auto">Stop</button>
          </div>
        ) : (
          <div className="flex gap-2">
            <button onClick={() => startRecording(type)} className="btn flex-1" disabled={!!uploading}>
              {clip.url ? "Re-record" : "Record"}
            </button>
            {clip.blob && !clip.uploaded && (
              <button onClick={() => uploadClip(type)} disabled={uploading === type} className="btn bg-green-600 hover:bg-green-700 flex-1">
                {uploading === type ? "Saving..." : "Save"}
              </button>
            )}
            {saved && <button onClick={() => deleteClip(type)} className="btn bg-gray-400 hover:bg-gray-500">Delete</button>}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-1">Voice Studio</h1>
        <p className="text-gray-500">Clone your voice for AI narration, or record intro/outro clips.</p>
      </div>

      {/* ── XTTS Voice Cloning (free, on-server) ───────────────────────────── */}
      <section>
        <h2 className="text-xl font-bold mb-1">Clone Your Voice</h2>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs bg-green-600 text-white px-2 py-0.5 rounded font-medium">Free</span>
          <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded font-medium">On-Server</span>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          Record or upload 1–3 minutes of clean speech. Your voice runs on the server (XTTS v2) — completely free, no API key needed.
        </p>

        {xttsHasSample ? (
          <div className="card border-2 border-green-400 bg-green-50">
            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-green-700 font-bold text-lg">Active</span>
                  <span className="text-xs bg-green-700 text-white px-2 py-0.5 rounded">XTTS v2</span>
                </div>
                <p className="text-sm text-green-800">Voice sample uploaded. All video narration will use your cloned voice.</p>
              </div>
              <button onClick={deleteXttsSample} className="btn bg-gray-400 hover:bg-gray-500 text-sm">Remove</button>
            </div>
          </div>
        ) : (
          <div className="card border-2 border-green-200 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Record live (1–3 minutes recommended)</label>
              {xttsUrl && <audio controls className="w-full mb-3"><source src={xttsUrl} /></audio>}
              {xttsRecording ? (
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-red-600 font-semibold">Recording... {xttsSeconds}s</span>
                  <button onClick={stopXttsRecording} className="btn bg-red-600 hover:bg-red-700 ml-auto">Stop</button>
                </div>
              ) : (
                <button onClick={startXttsRecording} className="btn w-full">
                  {xttsUrl ? "Re-record" : "Start Recording"}
                </button>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Or upload an audio file</label>
              <input
                type="file"
                accept="audio/*"
                onChange={e => { setXttsFile(e.target.files?.[0] || null); setXttsUrl(null); setXttsBlob(null); }}
                className="w-full text-sm"
              />
              {xttsFile && <p className="text-xs text-gray-500 mt-1">{xttsFile.name} ({(xttsFile.size / 1024 / 1024).toFixed(1)} MB)</p>}
            </div>
            {(xttsFile || xttsBlob) && (
              <button onClick={submitXttsSample} disabled={xttsUploading} className="btn bg-green-600 hover:bg-green-700 w-full">
                {xttsUploading ? "Uploading..." : "Save Voice Sample"}
              </button>
            )}
            {xttsStatus && (
              <p className={`text-sm font-medium ${xttsStatus.includes("failed") ? "text-red-600" : "text-green-600"}`}>
                {xttsStatus}
              </p>
            )}
          </div>
        )}
      </section>

      {/* ── ElevenLabs Voice Cloning (fallback) ─────────────────────────────── */}
      <section>
        <h2 className="text-xl font-bold mb-1">ElevenLabs Voice Clone</h2>
        <p className="text-sm text-gray-500 mb-4">
          Fallback option — used only if no XTTS sample is uploaded above. Requires an ElevenLabs API key.
        </p>

        {clonedVoice ? (
          <div className="card border-2 border-purple-400 bg-purple-50">
            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-green-600 font-bold text-lg">Active</span>
                  <span className="text-xs bg-purple-600 text-white px-2 py-0.5 rounded">ElevenLabs</span>
                </div>
                <p className="font-semibold">{clonedVoice.name}</p>
                <p className="text-xs text-gray-500 font-mono mt-1">{clonedVoice.voice_id}</p>
              </div>
              <button onClick={deleteClone} className="btn bg-gray-400 hover:bg-gray-500 text-sm">Remove</button>
            </div>
            <p className="text-sm text-purple-800 mt-3">All video narration will use your cloned voice.</p>
          </div>
        ) : (
          <div className="card border-2 border-purple-200 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Voice name</label>
              <input
                type="text"
                value={cloneName}
                onChange={e => setCloneName(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
                placeholder="e.g. Eddie's Voice"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Record live (1–3 minutes recommended)</label>
              {cloneUrl && (
                <audio controls className="w-full mb-3"><source src={cloneUrl} /></audio>
              )}
              {cloneRecording ? (
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-red-600 font-semibold">Recording... {cloneSeconds}s</span>
                  <button onClick={stopCloneRecording} className="btn bg-red-600 hover:bg-red-700 ml-auto">Stop</button>
                </div>
              ) : (
                <button onClick={startCloneRecording} className="btn w-full">
                  {cloneUrl ? "Re-record" : "Start Recording"}
                </button>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Or upload an audio file</label>
              <input
                type="file"
                accept="audio/*"
                onChange={e => { setCloneFile(e.target.files?.[0] || null); setCloneUrl(null); setCloneBlob(null); }}
                className="w-full text-sm"
              />
              {cloneFile && <p className="text-xs text-gray-500 mt-1">{cloneFile.name} ({(cloneFile.size / 1024 / 1024).toFixed(1)} MB)</p>}
            </div>

            {(cloneFile || cloneBlob) && (
              <button
                onClick={submitClone}
                disabled={cloning}
                className="btn bg-purple-600 hover:bg-purple-700 w-full"
              >
                {cloning ? "Cloning..." : "Clone My Voice"}
              </button>
            )}

            {cloneStatus && (
              <p className={`text-sm font-medium ${cloneStatus.includes("failed") ? "text-red-600" : "text-green-600"}`}>
                {cloneStatus}
              </p>
            )}
          </div>
        )}
      </section>

      {/* ── Intro / Outro clips ─────────────────────────────────────────── */}
      <section>
        <h2 className="text-xl font-bold mb-1">Intro & Outro Clips</h2>
        <p className="text-sm text-gray-600 mb-4">Short human clips spliced onto every video to avoid YouTube flags.</p>
        <div className="space-y-4">
          <ClipRecorder type="intro" label="Intro (5–10 sec)" example="Hey, what's up guys, welcome back to the channel—" />
          <ClipRecorder type="outro" label="Outro (5–10 sec)" example="Drop a comment below, subscribe if you're new, see you in the next one." />
        </div>
      </section>
    </div>
  );
}
