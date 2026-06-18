"use client";

import { useState, useEffect } from "react";
import { assetPacks } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function AssetPackPage() {
  const router = useRouter();
  const [assetPack, setAssetPack] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [scriptId] = useState(1); // Would be passed from previous page in real app

  const handleGenerateAssets = async () => {
    setLoading(true);
    try {
      const response = await assetPacks.generate(scriptId);
      setAssetPack(response.data);
    } catch (error) {
      console.error("Failed to generate asset pack:", error);
      alert("Failed to generate assets. Make sure script exists.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Create Your Asset Pack</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleGenerateAssets();
        }}
        className="card mb-8"
      >
        <p className="text-gray-600 mb-4">
          Generate everything you need: thumbnail design, video titles, B-roll list,
          voiceover instructions, editor brief, YouTube description, and pinned comment.
        </p>
        <button
          type="submit"
          className="btn w-full"
          disabled={loading}
        >
          {loading ? "Generating Assets..." : "Generate Complete Asset Pack"}
        </button>
      </form>

      {assetPack && (
        <>
          <div className="card mb-6">
            <h2 className="text-2xl font-bold mb-4">📸 Thumbnail Design</h2>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm">{assetPack.thumbnail_prompt}</p>
            </div>
            <p className="text-xs text-gray-500 mt-2">Use this prompt on Fiverr to order a thumbnail designer</p>
          </div>

          <div className="card mb-6">
            <h2 className="text-2xl font-bold mb-4">📝 Video Titles (Pick One)</h2>
            <div className="space-y-2">
              {JSON.parse(assetPack.alternate_titles).map((title: string, i: number) => (
                <div key={i} className="p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-blue-50">
                  <p className="font-semibold">{title}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="card mb-6">
            <h2 className="text-2xl font-bold mb-4">🎬 B-Roll List</h2>
            <div className="bg-gray-50 p-4 rounded-lg">
              <ul className="text-sm space-y-1">
                {JSON.parse(assetPack.broll_list).map((scene: string, i: number) => (
                  <li key={i}>• {scene}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="card mb-6">
            <h2 className="text-2xl font-bold mb-4">🎙️ Voiceover Instructions</h2>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm whitespace-pre-wrap">{assetPack.voiceover_instructions}</p>
            </div>
          </div>

          <div className="card mb-6">
            <h2 className="text-2xl font-bold mb-4">👷 Fiverr Editor Brief</h2>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm whitespace-pre-wrap">{assetPack.editor_brief}</p>
            </div>
            <p className="text-xs text-gray-500 mt-2">Copy this and paste into a Fiverr order to a video editor</p>
          </div>

          <div className="card mb-6">
            <h2 className="text-2xl font-bold mb-4">📺 YouTube Description</h2>
            <div className="bg-gray-50 p-4 rounded-lg font-mono text-xs">
              <p className="whitespace-pre-wrap">{assetPack.youtube_description}</p>
            </div>
            <button className="btn-secondary w-full mt-4">Copy to Clipboard</button>
          </div>

          <div className="card mb-6">
            <h2 className="text-2xl font-bold mb-4">📌 Pinned Comment</h2>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm whitespace-pre-wrap">{assetPack.pinned_comment}</p>
            </div>
            <button className="btn-secondary w-full mt-4">Copy to Clipboard</button>
          </div>

          <div className="card border-4 border-green-500 text-center py-8">
            <h3 className="text-2xl font-bold text-green-600 mb-4">✅ You're Ready!</h3>
            <p className="text-gray-700 mb-4">
              Record your voiceover and upload to Fiverr for editing. You're on your way to a successful YouTube channel!
            </p>
            <button
              onClick={() => router.push("/")}
              className="btn"
            >
              Back to Dashboard
            </button>
          </div>
        </>
      )}
    </div>
  );
}
