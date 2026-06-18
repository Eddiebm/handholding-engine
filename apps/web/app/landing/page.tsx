"use client";

import { useRouter } from "next/navigation";

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Navigation */}
      <nav className="bg-slate-900/80 backdrop-blur border-b border-purple-500/20 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-white">Handholding</h1>
          <div className="space-x-4">
            <button onClick={() => router.push("/auth/login")} className="text-gray-300 hover:text-white">
              Sign In
            </button>
            <button onClick={() => router.push("/auth/signup")} className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2 rounded-lg font-semibold">
              Start Free
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-4xl mx-auto space-y-8">
          <div className="space-y-4">
            <h2 className="text-5xl md:text-7xl font-bold text-white">
              Create YouTube Videos<br />
              <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                With AI
              </span>
            </h2>
            <p className="text-xl text-gray-300">
              Trending niche → Script → Voiceover → B-roll → Video in minutes.
              <br />
              No filming. No editing. No guesswork.
            </p>
          </div>

          <div className="flex gap-4 justify-center">
            <button
              onClick={() => router.push("/auto")}
              className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-8 py-4 rounded-lg font-bold text-lg"
            >
              Try Free Demo →
            </button>
            <button
              onClick={() => window.scrollTo(0, window.innerHeight * 2)}
              className="border-2 border-purple-400 text-purple-400 hover:bg-purple-400/10 px-8 py-4 rounded-lg font-bold text-lg"
            >
              See Pricing
            </button>
          </div>

          {/* Social Proof */}
          <div className="pt-8 border-t border-purple-500/20">
            <p className="text-gray-400 mb-4">Trusted by content creators</p>
            <div className="flex justify-center gap-8 text-sm">
              <div>
                <p className="text-2xl font-bold text-white">1000+</p>
                <p className="text-gray-400">Videos Generated</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-white">$50K+</p>
                <p className="text-gray-400">Revenue Created</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-white">6</p>
                <p className="text-gray-400">Script Styles</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-20">
        <h3 className="text-4xl font-bold text-white text-center mb-16">Why Handholding?</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-slate-800/50 border border-purple-500/20 rounded-lg p-8 hover:border-purple-500/50 transition">
            <div className="text-4xl mb-4">🎯</div>
            <h4 className="text-xl font-bold text-white mb-3">Trending Niches</h4>
            <p className="text-gray-400">AI finds high-monetization YouTube niches with proven demand. No guesswork.</p>
          </div>

          <div className="bg-slate-800/50 border border-purple-500/20 rounded-lg p-8 hover:border-purple-500/50 transition">
            <div className="text-4xl mb-4">📝</div>
            <h4 className="text-xl font-bold text-white mb-3">6 Script Styles</h4>
            <p className="text-gray-400">Storytelling, Educational, Trending, Entertaining, Contrarian, Tutorials. Fresh every time.</p>
          </div>

          <div className="bg-slate-800/50 border border-purple-500/20 rounded-lg p-8 hover:border-purple-500/50 transition">
            <div className="text-4xl mb-4">🎙️</div>
            <h4 className="text-xl font-bold text-white mb-3">Your Voice</h4>
            <p className="text-gray-400">Clone your voice once. All videos use your authentic voice automatically.</p>
          </div>

          <div className="bg-slate-800/50 border border-purple-500/20 rounded-lg p-8 hover:border-purple-500/50 transition">
            <div className="text-4xl mb-4">🎬</div>
            <h4 className="text-xl font-bold text-white mb-3">B-Roll Sourcing</h4>
            <p className="text-gray-400">Automatically fetch stock footage from Pexels. Ready to edit or hand off to freelancers.</p>
          </div>

          <div className="bg-slate-800/50 border border-purple-500/20 rounded-lg p-8 hover:border-purple-500/50 transition">
            <div className="text-4xl mb-4">📸</div>
            <h4 className="text-xl font-bold text-white mb-3">AI Thumbnails</h4>
            <p className="text-gray-400">Generate eye-catching thumbnails with DALL-E. Stand out in the feed.</p>
          </div>

          <div className="bg-slate-800/50 border border-purple-500/20 rounded-lg p-8 hover:border-purple-500/50 transition">
            <div className="text-4xl mb-4">💰</div>
            <h4 className="text-xl font-bold text-white mb-3">Cost Tracking</h4>
            <p className="text-gray-400">See exactly how much each video costs. Profitable from video 1.</p>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="container mx-auto px-4 py-20">
        <h3 className="text-4xl font-bold text-white text-center mb-16">Simple Pricing</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {/* Starter */}
          <div className="bg-slate-800/50 border border-gray-500/30 rounded-lg p-8">
            <h4 className="text-2xl font-bold text-white mb-2">Starter</h4>
            <p className="text-gray-400 mb-6">Perfect for testing</p>
            <p className="text-4xl font-bold text-white mb-6">Free<span className="text-sm text-gray-400">/month</span></p>
            <button className="w-full bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg font-semibold mb-8">
              Get Started
            </button>
            <ul className="space-y-3 text-gray-300 text-sm">
              <li>✓ 2 videos/month</li>
              <li>✓ 6 script styles</li>
              <li>✓ Default voice</li>
              <li>✗ Custom voice cloning</li>
              <li>✗ Commercial use</li>
            </ul>
          </div>

          {/* Pro */}
          <div className="bg-gradient-to-br from-purple-600 to-pink-600 rounded-lg p-8 ring-2 ring-purple-400 relative">
            <div className="absolute -top-4 left-8 bg-purple-600 text-white px-4 py-1 rounded-full text-sm font-bold">
              Most Popular
            </div>
            <h4 className="text-2xl font-bold text-white mb-2">Pro</h4>
            <p className="text-purple-100 mb-6">For content creators</p>
            <p className="text-4xl font-bold text-white mb-6">$99<span className="text-sm text-purple-100">/month</span></p>
            <button className="w-full bg-white hover:bg-gray-100 text-purple-600 py-2 rounded-lg font-semibold mb-8">
              Start Free Trial
            </button>
            <ul className="space-y-3 text-white text-sm">
              <li>✓ 30 videos/month</li>
              <li>✓ 6 script styles</li>
              <li>✓ Custom voice cloning</li>
              <li>✓ Commercial use</li>
              <li>✓ Priority support</li>
            </ul>
          </div>

          {/* Agency */}
          <div className="bg-slate-800/50 border border-gray-500/30 rounded-lg p-8">
            <h4 className="text-2xl font-bold text-white mb-2">Agency</h4>
            <p className="text-gray-400 mb-6">For agencies & companies</p>
            <p className="text-4xl font-bold text-white mb-6">$499<span className="text-sm text-gray-400">/month</span></p>
            <button className="w-full border-2 border-purple-600 hover:bg-purple-600/10 text-white py-2 rounded-lg font-semibold mb-8">
              Contact Sales
            </button>
            <ul className="space-y-3 text-gray-300 text-sm">
              <li>✓ Unlimited videos</li>
              <li>✓ 6 script styles</li>
              <li>✓ Custom voice cloning</li>
              <li>✓ API access</li>
              <li>✓ Dedicated support</li>
            </ul>
          </div>
        </div>

        {/* FAQ */}
        <div className="max-w-2xl mx-auto mt-20 space-y-4">
          <h4 className="text-2xl font-bold text-white mb-8">Common Questions</h4>
          <div className="bg-slate-800/50 border border-purple-500/20 rounded-lg p-6">
            <h5 className="font-bold text-white mb-2">Do I need filming equipment?</h5>
            <p className="text-gray-400">No. We handle everything: script, voiceover, B-roll. You just upload and profit.</p>
          </div>
          <div className="bg-slate-800/50 border border-purple-500/20 rounded-lg p-6">
            <h5 className="font-bold text-white mb-2">Can I use my own voice?</h5>
            <p className="text-gray-400">Yes. Clone your voice once, use it on all videos. Sounds professional and authentic.</p>
          </div>
          <div className="bg-slate-800/50 border border-purple-500/20 rounded-lg p-6">
            <h5 className="font-bold text-white mb-2">How much do videos cost to make?</h5>
            <p className="text-gray-400">$0.05 - $0.15 per video in API costs. Profitable at any YouTube monetization level.</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg p-12">
          <h3 className="text-4xl font-bold text-white mb-4">Ready to Build Your Channel?</h3>
          <p className="text-lg text-purple-100 mb-8">Start free. No credit card required. Scale when you're ready.</p>
          <button
            onClick={() => router.push("/auth/signup")}
            className="bg-white hover:bg-gray-100 text-purple-600 px-10 py-4 rounded-lg font-bold text-lg"
          >
            Start Free Trial
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-purple-500/20 bg-slate-900">
        <div className="container mx-auto px-4 py-8 text-center text-gray-400 text-sm">
          <p>© 2026 Handholding. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
