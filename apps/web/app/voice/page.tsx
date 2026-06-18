"use client";

import { useState, useEffect } from "react";
import axios from "axios";

export default function VoicePage() {
  const [voices, setVoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    loadVoices();
  }, []);

  const loadVoices = async () => {
    try {
      const response = await axios.get("/api/proxy?path=%2Fvoices%2Flist");
      setVoices(response.data.voices || []);
    } catch (error) {
      console.error("Failed to load voices:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      alert("Please select an audio file");
      return;
    }

    setUploading(true);
    try {
      // In a real implementation, this would upload the file to the server
      // For now, we'll show a message about using the cloned voice
      alert(
        `Voice file "${file.name}" selected.\n\nNext steps:\n1. Save this file to your server\n2. Set VOICE_FILE_PATH environment variable\n3. Restart the backend\n\nThen all videos will use your cloned voice!`
      );

      // Show success
      const response = await axios.post("/api/proxy?path=%2Fvoices%2Fupload");
      setFile(null);
      loadVoices();
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Upload failed. Check console for details.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">🎙️ Your Voice Profiles</h1>

      {/* Upload Section */}
      <div className="card bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-300 mb-8">
        <h2 className="text-2xl font-bold mb-4">Upload Your Cloned Voice</h2>
        <p className="text-gray-700 mb-4">
          Use your MacBook voice cloning app to create a voice, then upload the MP3 here. All future videos will use YOUR voice!
        </p>

        <form onSubmit={handleUpload} className="space-y-4">
          <div className="border-2 border-dashed border-purple-300 rounded-lg p-6 text-center">
            <input
              type="file"
              accept="audio/mpeg,audio/wav,audio/mp4"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="hidden"
              id="voice-input"
            />
            <label htmlFor="voice-input" className="cursor-pointer">
              <div className="text-4xl mb-2">🎵</div>
              <p className="font-semibold text-gray-800">
                {file ? file.name : "Click to upload voice file"}
              </p>
              <p className="text-sm text-gray-600">MP3, WAV, or M4A (30 seconds - 5 minutes)</p>
            </label>
          </div>

          <button
            type="submit"
            disabled={!file || uploading}
            className="btn w-full"
          >
            {uploading ? "Uploading..." : "Use This Voice"}
          </button>
        </form>

        <div className="mt-6 p-4 bg-white rounded-lg border-l-4 border-blue-500">
          <h3 className="font-bold mb-2">📋 How to Clone Your Voice:</h3>
          <ol className="text-sm text-gray-700 space-y-2 list-decimal list-inside">
            <li>Open your voice cloning app on your MacBook</li>
            <li>Record 30 seconds - 5 minutes of you speaking naturally</li>
            <li>Export as MP3</li>
            <li>Upload here ↑</li>
            <li>All future videos use YOUR voice!</li>
          </ol>
        </div>
      </div>

      {/* Uploaded Voices */}
      {!loading && (
        <div>
          <h2 className="text-2xl font-bold mb-4">Your Voices</h2>
          {voices.length === 0 ? (
            <div className="card text-center py-8 text-gray-500">
              <p>No voices uploaded yet. Upload your first voice above!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {voices.map((voice) => (
                <div key={voice.id} className="card">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-bold">{voice.name}</h3>
                      {voice.is_default && (
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                          Default
                        </span>
                      )}
                    </div>
                    <span className="text-2xl">🎙️</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Benefits */}
      <div className="card bg-green-50 border-2 border-green-300 mt-8">
        <h3 className="font-bold text-lg mb-3">✅ Benefits of Using Your Voice</h3>
        <ul className="space-y-2 text-sm text-gray-800">
          <li>✓ Unique branding - viewers hear YOU, not a robot</li>
          <li>✓ Save $$ on ElevenLabs API costs</li>
          <li>✓ More authentic connection with your audience</li>
          <li>✓ Faster video production (no API wait time)</li>
          <li>✓ Consistent voice across all videos</li>
        </ul>
      </div>
    </div>
  );
}
