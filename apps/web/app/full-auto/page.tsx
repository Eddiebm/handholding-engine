'use client';

import { useEffect, useRef, useState } from 'react';

const API = "https://api.theworldagency.uk/handholding";

type Phase = 'idle' | 'running' | 'done' | 'error';

interface StepData { label: string; detail: string; }

const STEPS: StepData[] = [
  { label: 'Generating niche',        detail: 'Analyzing trending topics & gaps' },
  { label: 'Researching competitors', detail: 'Scanning top-performing channels' },
  { label: 'Generating video ideas',  detail: 'Creating 10 unique concepts' },
  { label: 'Writing script',          detail: 'Full narration with timestamps' },
  { label: 'Building asset pack',     detail: 'Images, overlays & color palette' },
  { label: 'Generating voiceover',    detail: 'ElevenLabs voice synthesis' },
  { label: 'Fetching B-roll',         detail: 'Pexels & Unsplash video library' },
  { label: 'Generating thumbnail',    detail: 'AI-optimised CTR design' },
  { label: 'Assembling video',        detail: 'FFmpeg multi-track composition' },
];

const NAV_ITEMS = [
  { label: 'Dashboard', href: '/' },
  { label: 'Autopilot', href: '/autopilot' },
  { label: 'Intelligence', href: '/intelligence' },
  { label: 'Capital', href: '/capital' },
  { label: 'Full Auto', href: '/full-auto' },
  { label: 'Calendar', href: '/calendar' },
  { label: 'Batch', href: '/batch' },
  { label: 'Admin', href: '/admin' },
  { label: 'Optimize', href: '/optimize' },
];

const RUST  = 'oklch(0.42 0.15 28)';
const GREEN = 'oklch(0.45 0.12 155)';

function stepIndexFromBackend(stepName: string): number {
  const clean = (stepName || '').replace(/\.\.\.$/,'').toLowerCase().trim();
  return STEPS.findIndex(s => s.label.toLowerCase() === clean);
}

function Sidebar({ activeItem }: { activeItem: string }) {
  return (
    <nav style={{ width: 192, flexShrink: 0, borderRight: '1px solid #E8E3D8', display: 'flex', flexDirection: 'column', background: '#F9F8F5' }}>
      <div style={{ padding: '26px 22px 20px', borderBottom: '1px solid #ECE8DF' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#12100A', letterSpacing: '-0.01em' }}>Handholding</div>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: '#C8C4B8', letterSpacing: '0.14em', marginTop: 4 }}>CONTENT ENGINE</div>
      </div>
      <div style={{ padding: '16px 12px', flex: 1, display: 'flex', flexDirection: 'column', gap: 2, overflowY: 'auto' }}>
        {NAV_ITEMS.map(({ label, href }) => {
          const active = label === activeItem;
          return (
            <a key={label} href={href} style={{
              padding: '7px 10px', fontSize: 13, fontWeight: active ? 500 : 400,
              color: active ? '#12100A' : '#A8A498', cursor: 'pointer',
              letterSpacing: '-0.005em', textDecoration: 'none',
              borderLeft: `1.5px solid ${active ? RUST : 'transparent'}`,
              display: 'block',
            }}>
              {label}
            </a>
          );
        })}
      </div>
    </nav>
  );
}

function StepTrack({ phase, currentStep }: { phase: Phase; currentStep: number }) {
  return (
    <div style={{ padding: '20px 56px 28px', borderTop: '1px solid #ECE8DF', display: 'flex', alignItems: 'center' }}>
      {STEPS.map((step, i) => {
        const done   = phase === 'done' || i < currentStep;
        const active = phase === 'running' && i === currentStep;
        const isLast = i === STEPS.length - 1;
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', flex: isLast ? undefined : 1 }}>
            <div title={step.label} style={{
              width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
              border: `1px solid ${active ? RUST : done ? GREEN : '#DDD8CE'}`,
              background: active ? 'oklch(0.42 0.15 28 / 0.06)' : done ? 'oklch(0.45 0.12 155 / 0.07)' : 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: done ? 11 : 9, fontWeight: done ? 600 : 400,
              color: active ? RUST : done ? GREEN : '#C8C4B8',
              transition: 'border-color 0.35s, background 0.35s, color 0.35s',
            }}>
              {done ? '✓' : String(i + 1).padStart(2, '0')}
            </div>
            {!isLast && (
              <div style={{ flex: 1, height: 1, minWidth: 12, background: done ? 'oklch(0.45 0.12 155 / 0.3)' : '#E8E3D8', transition: 'background 0.45s ease' }} />
            )}
          </div>
        );
      })}
    </div>
  );
}

const HERO_FONT: React.CSSProperties = {
  fontFamily: "'Cormorant Garamond', serif",
  fontStyle: 'italic', fontWeight: 300,
  fontSize: 'clamp(52px, 5.8vw, 90px)',
  lineHeight: 1.04, letterSpacing: '-0.03em',
};

function HeroIdle() {
  return (
    <div style={{ animation: 'fullAutoRise 0.65s ease' }}>
      <div style={{ ...HERO_FONT, color: '#12100A', marginBottom: 26 }}>
        Full automation.<br />One click.
      </div>
      <div style={{ fontSize: 14, color: '#B0AA9E', lineHeight: 1.8, maxWidth: 340, marginBottom: 26 }}>
        Pick a niche, write a script, generate voiceover, fetch B-roll, assemble a video.
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {['~2–3 min', '$0.07 / video', '9 steps'].map((tag, i) => (
          <span key={tag} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {i > 0 && <span style={{ color: '#DDD8CE' }}>·</span>}
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#C8C4B8', letterSpacing: '0.04em' }}>{tag}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function HeroRunning({ currentStep, stepProgress }: { currentStep: number; stepProgress: number }) {
  const step = STEPS[currentStep] ?? STEPS[0];
  const fading = stepProgress < 10;
  return (
    <div style={{ opacity: fading ? 0.03 : 1, transform: fading ? 'translateY(16px)' : 'translateY(0)', transition: fading ? 'none' : 'opacity 0.5s ease, transform 0.5s ease' }}>
      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#C8C4B8', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 22 }}>
        Step {String(currentStep + 1).padStart(2, '0')} / 09
      </div>
      <div style={{ ...HERO_FONT, color: '#12100A', marginBottom: 20 }}>{step.label}.</div>
      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: '#C0BAB0', letterSpacing: '0.02em', marginBottom: 36 }}>{step.detail}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, maxWidth: 380 }}>
        <div style={{ flex: 1, height: 1, background: '#E8E3D8', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, height: '100%', width: `${Math.round(stepProgress)}%`, background: RUST, transition: 'width 55ms linear' }} />
        </div>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#C8C4B8', letterSpacing: '0.04em', width: 30, textAlign: 'right', flexShrink: 0 }}>
          {Math.round(stepProgress)}%
        </div>
      </div>
    </div>
  );
}

function HeroDone({ result, onReset }: { result: any; onReset: () => void }) {
  const files = result?.automation_files ?? {};
  const videoUrl = files.final_video ? `${API}${files.final_video}` : null;
  const thumbUrl = files.thumbnail  ? `${API}${files.thumbnail}`   : null;

  return (
    <div style={{ animation: 'fullAutoRise 0.5s ease', display: 'flex', gap: 48, alignItems: 'flex-start', maxWidth: 900 }}>
      {/* Video player */}
      {videoUrl && (
        <div style={{ flexShrink: 0, width: 'clamp(220px, 38vw, 420px)' }}>
          <video
            controls
            autoPlay
            src={videoUrl}
            poster={thumbUrl ?? undefined}
            style={{ width: '100%', display: 'block', background: '#12100A' }}
          />
        </div>
      )}

      {/* Info + actions */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: GREEN, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 16 }}>
          All 9 steps complete
        </div>
        <div style={{ ...HERO_FONT, color: RUST, marginBottom: 12 }}>Done.</div>
        {result?.niche && (
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: '#C0BAB0', letterSpacing: '0.02em', marginBottom: 8 }}>
            {result.niche}
          </div>
        )}
        {result?.idea && (
          <div style={{ fontSize: 14, color: '#6B6760', lineHeight: 1.5, marginBottom: 28, maxWidth: 320 }}>
            {result.idea}
          </div>
        )}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          {videoUrl && (
            <a href={videoUrl} download style={{
              background: '#12100A', color: '#F9F8F5', border: 'none', padding: '11px 24px',
              fontFamily: "'Epilogue', sans-serif", fontSize: 12, fontWeight: 600, cursor: 'pointer',
              letterSpacing: '0.06em', textTransform: 'uppercase', textDecoration: 'none', display: 'inline-block',
            }}>Download</a>
          )}
          <button onClick={onReset} style={{
            background: 'transparent', color: '#C0BAB0', border: '1px solid #DDD8CE', padding: '11px 24px',
            fontFamily: "'Epilogue', sans-serif", fontSize: 12, cursor: 'pointer',
            letterSpacing: '0.06em', textTransform: 'uppercase',
          }}>Generate Another</button>
        </div>
      </div>
    </div>
  );
}

export default function FullAutoPage() {
  const [phase, setPhase]               = useState<Phase>('idle');
  const [currentStep, setCurrentStep]   = useState(0);
  const [stepProgress, setStepProgress] = useState(0);
  const [result, setResult]             = useState<any>(null);
  const [errorMsg, setErrorMsg]         = useState('');

  const pollRef      = useRef<ReturnType<typeof setInterval> | null>(null);
  const progressRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastStepRef  = useRef(-1);

  const stopPolling = () => {
    if (pollRef.current)     clearInterval(pollRef.current);
    if (progressRef.current) clearInterval(progressRef.current);
  };

  const startProgressTick = () => {
    if (progressRef.current) clearInterval(progressRef.current);
    setStepProgress(0);
    progressRef.current = setInterval(() => {
      setStepProgress(p => p < 85 ? p + 2 : p);
    }, 300);
  };

  const handleGenerate = async () => {
    setPhase('running');
    setCurrentStep(0);
    setStepProgress(0);
    lastStepRef.current = -1;
    startProgressTick();

    let jobId: string;
    try {
      const r = await fetch(`${API}/demo/full-automation/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      if (!r.ok) { setPhase('error'); setErrorMsg(`Server error ${r.status}`); return; }
      const d = await r.json();
      if (!d.job_id) { setPhase('error'); setErrorMsg('No job_id returned'); return; }
      jobId = d.job_id;
    } catch (e: any) {
      setPhase('error'); setErrorMsg(`Connect failed: ${e?.message ?? e}`); return;
    }

    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/demo/full-automation/status/${jobId}`);
        if (r.status === 404) {
          stopPolling(); setPhase('error'); setErrorMsg('Job lost — server restarted. Try again.'); return;
        }
        const s = await r.json();
        const idx = stepIndexFromBackend(s.step ?? '');
        if (idx >= 0 && idx !== lastStepRef.current) {
          lastStepRef.current = idx;
          setCurrentStep(idx);
          startProgressTick();
        }
        if (s.status === 'done') {
          stopPolling();
          setStepProgress(100);
          setResult(s.result);
          setPhase('done');
        } else if (s.status === 'error') {
          stopPolling();
          setPhase('error');
          setErrorMsg(s.error ?? 'Generation failed');
        }
      } catch { /* transient — keep polling */ }
    }, 3000);
  };

  const handleCancel = () => {
    stopPolling();
    setPhase('idle');
    setCurrentStep(0);
    setStepProgress(0);
    setResult(null);
    setErrorMsg('');
    lastStepRef.current = -1;
  };

  useEffect(() => () => stopPolling(), []);

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@1,300;1,400&family=Epilogue:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
        @keyframes fullAutoRise { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
        @keyframes fullAutoBreathe { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.3; transform:scale(1.6); } }
      `}</style>

      {/* Full-viewport takeover — sits above layout nav */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 100, display: 'flex', fontFamily: "'Epilogue', sans-serif", color: '#12100A', background: '#F9F8F5' }}>
        <Sidebar activeItem="Full Auto" />

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden', background: 'radial-gradient(ellipse 90% 45% at 50% -15%, #F0EBE0 0%, #F9F8F5 55%)' }}>

          {/* Top bar */}
          <div style={{ padding: '20px 56px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 13, opacity: 0.4 }}>⚡</span>
              <span style={{ fontSize: 13, fontWeight: 500, color: '#A8A498', letterSpacing: '-0.01em' }}>Full Auto</span>
              {phase === 'running' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 6 }}>
                  <span style={{ width: 5, height: 5, borderRadius: '50%', background: RUST, display: 'block', flexShrink: 0, animation: 'fullAutoBreathe 1.8s ease-in-out infinite' }} />
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: RUST, letterSpacing: '0.05em' }}>{currentStep + 1} / 9</span>
                </div>
              )}
            </div>
            <div>
              {phase === 'idle' && (
                <button onClick={handleGenerate} style={{ display: 'flex', alignItems: 'center', gap: 9, background: '#12100A', color: '#F9F8F5', border: 'none', padding: '9px 22px', borderRadius: 0, fontFamily: "'Epilogue', sans-serif", fontSize: 12, fontWeight: 600, cursor: 'pointer', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  Generate
                  <svg width="11" height="11" viewBox="0 0 11 11" fill="currentColor"><polygon points="1,1 10,5.5 1,10" /></svg>
                </button>
              )}
              {phase === 'running' && (
                <button onClick={handleCancel} style={{ background: 'transparent', color: '#C0BAB0', border: '1px solid #DDD8CE', padding: '9px 22px', borderRadius: 0, fontFamily: "'Epilogue', sans-serif", fontSize: 12, cursor: 'pointer', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Cancel</button>
              )}
              {(phase === 'done' || phase === 'error') && (
                <button onClick={handleCancel} style={{ background: 'transparent', color: '#12100A', border: '1px solid #C8C4B8', padding: '9px 22px', borderRadius: 0, fontFamily: "'Epilogue', sans-serif", fontSize: 12, cursor: 'pointer', letterSpacing: '0.06em', textTransform: 'uppercase' }}>New Video</button>
              )}
            </div>
          </div>

          {/* Hero */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '0 56px', overflow: 'hidden' }}>
            {phase === 'idle'    && <HeroIdle />}
            {phase === 'running' && <HeroRunning currentStep={currentStep} stepProgress={stepProgress} />}
            {phase === 'done'    && <HeroDone result={result} onReset={handleCancel} />}
            {phase === 'error'   && (
              <div style={{ animation: 'fullAutoRise 0.5s ease' }}>
                <div style={{ ...HERO_FONT, color: '#C0392B', marginBottom: 20 }}>Failed.</div>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: '#C0BAB0', marginBottom: 28 }}>{errorMsg}</div>
                <button onClick={handleCancel} style={{ background: '#12100A', color: '#F9F8F5', border: 'none', padding: '11px 28px', fontFamily: "'Epilogue', sans-serif", fontSize: 12, fontWeight: 600, cursor: 'pointer', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Try Again</button>
              </div>
            )}
          </div>

          <StepTrack phase={phase} currentStep={currentStep} />
        </div>
      </div>
    </>
  );
}
