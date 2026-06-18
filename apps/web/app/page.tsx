"use client";

import { useState, useEffect } from "react";
import { coach, niches } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface NextAction {
  task_text: string;
  related_type: string;
  related_id: number;
}

interface Niche {
  id: number;
  name: string;
  audience: string;
  monetization_angle: string;
  notes: string;
}

export default function Dashboard() {
  const router = useRouter();
  const [nextAction, setNextAction] = useState<NextAction | null>(null);
  const [niche, setNiche] = useState<Niche | null>(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      const action = await coach.getNextAction();
      setNextAction(action.data);

      const nichesList = await niches.list();
      if (nichesList.data.length > 0) {
        setNiche(nichesList.data[0]);
      }

      calculateProgress();
    } catch (error) {
      console.error("Failed to load dashboard:", error);
    } finally {
      setLoading(false);
    }
  };

  const calculateProgress = () => {
    let p = 0;
    if (niche) p += 20;
    // Add more based on completion
    setProgress(p);
  };

  const getActionLink = (action: NextAction) => {
    switch (action.related_type) {
      case "niche":
        return "/niches";
      case "competitor":
        return "/competitors";
      case "idea":
        return "/ideas";
      case "script":
        return "/scripts";
      case "asset_pack":
        return "/asset-pack";
      default:
        return "/";
    }
  };

  if (loading) {
    return <div className="text-center py-12">Loading your dashboard...</div>;
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="card bg-gradient-to-r from-purple-50 to-blue-50 border-2 border-purple-300 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-3xl font-bold">Welcome to Your Content Journey</h2>
          <span className="text-3xl">🚀</span>
        </div>
        <p className="text-gray-700 mb-6">Choose your automation level:</p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <button
            onClick={() => router.push("/auto")}
            className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-bold py-4 px-6 rounded-lg transition-all"
          >
            ▶️ YouTube 10min
          </button>
          <button
            onClick={() => router.push("/full-auto")}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-bold py-4 px-6 rounded-lg transition-all"
          >
            🤖 YouTube + Video
          </button>
          <button
            onClick={() => router.push("/multi-platform")}
            className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold py-4 px-6 rounded-lg transition-all"
          >
            📱 4 Platforms
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-600">
          <p>
            <strong>Basic:</strong> Niche, ideas, script, assets. You record voiceover & handle editing.
          </p>
          <p>
            <strong>Full:</strong> Generates voiceover, B-roll, & thumbnail. You just assemble the video.
          </p>
        </div>
      </div>

      <div className="card mb-8">
        <h3 className="text-xl font-bold mb-4 text-gray-700">Or Build Step-by-Step</h3>

        {niche && (
          <div className="mb-6 p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-gray-600">Current Niche</p>
            <h3 className="text-xl font-semibold text-blue-600">{niche.name}</h3>
            <p className="text-sm text-gray-700 mt-2">Audience: {niche.audience}</p>
          </div>
        )}

        <div className="mb-6">
          <div className="flex justify-between mb-2">
            <span className="text-sm font-semibold">Progress</span>
            <span className="text-sm">{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {nextAction && (
        <div className="card border-4 border-blue-600 text-center py-12">
          <h3 className="text-lg text-gray-600 mb-6">Your Next Action</h3>
          <p className="text-3xl font-bold text-blue-600 mb-8">{nextAction.task_text}</p>

          <Link href={getActionLink(nextAction)}>
            <button className="btn text-lg px-8 py-4">
              Get Started
            </button>
          </Link>
        </div>
      )}

      <div className="mt-8 grid grid-cols-1 gap-4">
        <Link href="/niches">
          <div className="card cursor-pointer hover:shadow-lg transition-shadow">
            <h4 className="font-semibold text-blue-600">➊ Create Niche</h4>
            <p className="text-sm text-gray-600 mt-2">Define your YouTube niche and audience</p>
          </div>
        </Link>

        <Link href="/competitors">
          <div className="card cursor-pointer hover:shadow-lg transition-shadow">
            <h4 className="font-semibold text-blue-600">➋ Add Competitors</h4>
            <p className="text-sm text-gray-600 mt-2">Paste YouTube URLs to analyze patterns</p>
          </div>
        </Link>

        <Link href="/ideas">
          <div className="card cursor-pointer hover:shadow-lg transition-shadow">
            <h4 className="font-semibold text-blue-600">➌ Generate & Score Ideas</h4>
            <p className="text-sm text-gray-600 mt-2">AI generates 10 ideas, you pick the best</p>
          </div>
        </Link>

        <Link href="/scripts">
          <div className="card cursor-pointer hover:shadow-lg transition-shadow">
            <h4 className="font-semibold text-blue-600">➍ Write Script</h4>
            <p className="text-sm text-gray-600 mt-2">Generate a compelling 10-minute script</p>
          </div>
        </Link>

        <Link href="/asset-pack">
          <div className="card cursor-pointer hover:shadow-lg transition-shadow">
            <h4 className="font-semibold text-blue-600">➎ Create Assets</h4>
            <p className="text-sm text-gray-600 mt-2">Thumbnail, titles, B-roll, voiceover brief</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
