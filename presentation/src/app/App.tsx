import { useState } from 'react';

const slides = [
  {
    id: 's1',
    label: '01 Title',
    component: Slide1
  },
  {
    id: 's2',
    label: '02 The Learning Gap',
    component: Slide2
  },
  {
    id: 's3',
    label: '03 Meet CircuitSensei',
    component: Slide3
  },
  {
    id: 's4',
    label: '04 The Agentic Workflow',
    component: Slide4
  },
  {
    id: 's5',
    label: '05 Visual Guidance',
    component: Slide5
  },
  {
    id: 's6',
    label: '06 Technology Stack',
    component: Slide6
  },
  {
    id: 's7',
    label: '07 Education Impact',
    component: Slide7
  },
  {
    id: 's8',
    label: '08 Open Source',
    component: Slide8
  }
];

const bgGradient = 'linear-gradient(147.542deg, rgb(9, 9, 11) 0%, rgb(24, 24, 27) 50%, rgb(9, 9, 11) 100%)';

function Slide1() {
  return (
    <section className="relative w-full h-full flex flex-col justify-center px-16 py-12 overflow-hidden" style={{ background: bgGradient }}>
      <div className="absolute inset-0 opacity-40 pointer-events-none">
        <div className="absolute bg-[rgba(0,188,125,0.1)] blur-[64px] left-[60%] opacity-50 rounded-full size-96 top-20" />
        <div className="absolute bg-[rgba(43,127,255,0.1)] blur-[64px] left-20 rounded-full size-96 top-1/3" />
      </div>

      <div className="flex flex-col gap-0 relative z-10 max-w-5xl">
        <h1 className="font-['Inter'] text-7xl font-semibold leading-none text-white">
          Circuit<span className="text-[#00BC7D]">Sensei</span>
        </h1>
        <div className="flex items-center gap-2 mt-4 mb-6">
          <div className="bg-[#00d492] opacity-50 rounded-full size-2" />
          <p className="text-[#00d492] text-sm font-normal">AI-Powered Electronics Assistant</p>
        </div>
        <p className="text-xl text-[#d4d4d8] leading-relaxed max-w-3xl">
          An open-source agentic assistant that guides students through breadboard circuits — step by step, visually.
        </p>
        <div className="mt-8 flex gap-4 items-center flex-wrap">
          <div className="bg-[#009966] px-5 py-3 rounded-xl shadow-lg flex items-center gap-2 text-white text-base font-medium">
            <svg width="16" height="16" viewBox="0 0 22 22" fill="none">
              <circle cx="11" cy="11" r="9" stroke="currentColor" strokeWidth="1.8"/>
              <path d="M7 11l3 3 5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Light the Way · Aramco Track
          </div>
          <div className="text-[#71717b] text-sm">LAHacks 2026 · April 25–27</div>
        </div>
      </div>
    </section>
  );
}

function Slide2() {
  const painPoints = [
    {
      num: '01',
      title: 'No Spatial Awareness',
      desc: "Beginners stare at a breadboard and don't know where to place components. Diagrams don't map to physical rows and columns."
    },
    {
      num: '02',
      title: 'No Real-Time Feedback',
      desc: 'Traditional tutorials are static. Students make wiring mistakes and have no way to verify correctness before applying power.'
    },
    {
      num: '03',
      title: 'Dangerous Errors',
      desc: 'A single miswired LED or short circuit can destroy components or cause smoke. Fear of breaking things stops learners cold.'
    }
  ];

  return (
    <section className="w-full h-full flex flex-col px-16 py-10" style={{ background: bgGradient }}>
      <div className="text-[#00d492] text-xs uppercase mb-3 tracking-wider">Product Thinking · A Sharp, Differentiated Problem</div>
      <h2 className="text-4xl font-semibold text-white mb-3">The Learning Gap in Electronics</h2>
      <p className="text-base text-[#d4d4d8] max-w-3xl mb-5">Hands-on electronics is gatekept by spatial intuition, fear of damage, and lack of feedback — leaving millions of students without a viable path to physical computing.</p>
      <div className="grid grid-cols-3 gap-6 flex-1">
        {painPoints.map((point) => (
          <div key={point.num} className="flex flex-col gap-3 px-6 py-6 rounded-xl bg-[rgba(24,24,27,0.5)] border border-[#27272a]">
            <div className="text-5xl font-medium text-[#00BC7D] opacity-30">
              {point.num}
            </div>
            <h3 className="text-xl font-semibold text-white">{point.title}</h3>
            <p className="text-sm text-[#9f9fa9] leading-relaxed">
              {point.desc}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Slide3() {
  const features = [
    {
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M16 18L22 12L16 6M8 6L2 12L8 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      title: 'Natural Language',
      desc: 'Describe circuits in plain English powered by Google Gemini',
      color: '#00BC7D'
    },
    {
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M2.062 12.348C1.97866 12.1235 1.97866 11.8765 2.062 11.652C2.8737 9.68385 4.25152 8.00104 6.02077 6.8169C7.79003 5.63276 9.87104 5.00062 12 5.00062C14.129 5.00062 16.21 5.63276 17.9792 6.8169C19.7485 8.00104 21.1263 9.68385 21.938 11.652C22.0213 11.8765 22.0213 12.1235 21.938 12.348C21.1263 14.3161 19.7485 15.999 17.9792 17.1831C16.21 18.3672 14.129 18.9994 12 18.9994C9.87104 18.9994 7.79003 18.3672 6.02077 17.1831C4.25152 15.999 2.8737 14.3161 2.062 12.348Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      title: 'Vision Verification',
      desc: 'AI verifies each component placement with your webcam',
      color: '#51A2FF'
    },
    {
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M4 14C3.81077 14.0006 3.62523 13.9476 3.46495 13.847C3.30468 13.7464 3.17623 13.6024 3.09455 13.4317C3.01287 13.261 2.98129 13.0706 3.0035 12.8827C3.02571 12.6947 3.10078 12.517 3.22 12.37L13.12 2.17C13.1943 2.08428 13.2955 2.02636 13.407 2.00573C13.5185 1.98511 13.6337 2.00301 13.7337 2.0565C13.8337 2.11 13.9126 2.1959 13.9573 2.30011C14.0021 2.40432 14.0101 2.52065 13.98 2.63L12.06 8.65C12.0034 8.80152 11.9844 8.96452 12.0046 9.12501C12.0248 9.28549 12.0837 9.43868 12.1761 9.57143C12.2685 9.70417 12.3918 9.81251 12.5353 9.88716C12.6788 9.96181 12.8382 10.0005 13 10H20C20.1892 9.99935 20.3748 10.0524 20.535 10.153C20.6953 10.2536 20.8238 10.3976 20.9055 10.5683C20.9871 10.739 21.0187 10.9294 20.9965 11.1173C20.9743 11.3053 20.8992 11.483 20.78 11.63L10.88 21.83C10.8057 21.9157 10.7045 21.9736 10.593 21.9943C10.4815 22.0149 10.3663 21.997 10.2663 21.9435C10.1663 21.89 10.0874 21.8041 10.0427 21.6999C9.99791 21.5957 9.98992 21.4794 10.02 21.37L11.94 15.35C11.9966 15.1985 12.0156 15.0355 11.9954 14.875C11.9752 14.7145 11.9163 14.5613 11.8239 14.4286C11.7315 14.2958 11.6082 14.1875 11.4647 14.1128C11.3212 14.0382 11.1618 13.9995 11 14H4Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      title: 'Arduino Testing',
      desc: 'Automated electrical tests via Arduino hardware bridge',
      color: '#FDC700'
    }
  ];

  return (
    <section className="w-full h-full flex flex-col px-16 py-10" style={{ background: bgGradient }}>
      <div className="text-[#00d492] text-xs uppercase mb-3 tracking-wider">Originality &amp; Insight · A Novel Framing</div>
      <h2 className="text-4xl font-semibold text-white mb-2">
        Meet <span className="text-[#00BC7D]">CircuitSensei</span>
      </h2>
      <p className="text-base text-[#d4d4d8] max-w-3xl mb-5">The first agent that <strong>sees your physical breadboard</strong> — closing the loop between LLM reasoning, computer vision, and real hardware. Not a simulator. Not a tutorial. A live tutor.</p>
      <div className="grid grid-cols-3 gap-6 flex-1">
        {features.map((feat, i) => (
          <div key={i} className="flex flex-col items-center text-center gap-3 px-6 py-6 rounded-xl bg-[rgba(24,24,27,0.5)] border border-[#27272a]">
            <div className="size-12 rounded-lg flex items-center justify-center" style={{ background: `rgba(${feat.color === '#00BC7D' ? '0,188,125' : feat.color === '#51A2FF' ? '43,127,255' : '240,177,0'},0.2)`, color: feat.color }}>
              {feat.icon}
            </div>
            <h3 className="text-lg font-medium text-white">{feat.title}</h3>
            <p className="text-sm text-[#9f9fa9] leading-relaxed">
              {feat.desc}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Slide4() {
  const steps = [
    { label: 'STATE 1', name: 'Intake', desc: 'User states circuit goal in plain English', highlight: false },
    { label: 'STATE 2', name: 'Plan', desc: 'Agent derives placement plan with hole coordinates', highlight: false },
    { label: 'STATE 3', name: 'Instruct', desc: 'Annotated overlay highlights exact holes to use', highlight: true },
    { label: 'STATE 4', name: 'Verify', desc: 'Gemini Vision confirms correct placement', highlight: true },
    { label: 'STATE 5', name: 'Test', desc: 'Arduino runs voltage and LED tests', highlight: false }
  ];

  return (
    <section className="w-full h-full flex flex-col px-16 py-10" style={{ background: bgGradient }}>
      <div className="text-[#00d492] text-xs uppercase mb-3 tracking-wider">Technical Depth · Custom Agentic State Machine</div>
      <h2 className="text-4xl font-semibold text-white mb-2">The Agentic Workflow</h2>
      <p className="text-base text-[#d4d4d8] max-w-3xl mb-5">A purpose-built 5-state controller orchestrates Gemini reasoning, Vision verification, and Arduino I/O — with safety interlocks at every transition.</p>
      <div className="flex items-stretch gap-0 flex-1">
        {steps.map((step, i) => (
          <div key={i} className="flex-1 flex flex-col gap-2 px-4 py-5 border relative" style={{
            background: step.highlight ? 'rgba(0,188,125,0.1)' : 'rgba(24,24,27,0.5)',
            borderColor: step.highlight ? '#00BC7D' : '#27272a',
            borderRadius: i === 0 ? '12px 0 0 12px' : i === steps.length - 1 ? '0 12px 12px 0' : '0'
          }}>
            <div className="text-[#00d492] text-xs tracking-wider">
              {step.label}
            </div>
            <div className="text-lg font-semibold text-white">{step.name}</div>
            <div className="text-xs text-[#9f9fa9] leading-relaxed">
              {step.desc}
            </div>
            {i < steps.length - 1 && (
              <div className="absolute -right-3 top-1/2 -translate-y-1/2 z-10 size-6 rounded-full flex items-center justify-center border border-[#00BC7D] bg-[#18181b] text-[#00BC7D] text-sm">
                ›
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function Slide5() {
  return (
    <section className="w-full h-full flex flex-row gap-12 items-center px-16 py-10" style={{ background: bgGradient }}>
      <div className="flex-1 flex flex-col gap-6">
        <div>
          <div className="text-[#00d492] text-xs uppercase mb-3 tracking-wider">Execution &amp; Polish · Working Demo</div>
          <h2 className="text-4xl font-semibold text-white mb-4">
            Visual Guidance<br/>in Action
          </h2>
        </div>
        <div className="flex flex-col gap-3">
          {[
            'Agent maps breadboard coordinates to <strong>pixel positions</strong> in the webcam frame',
            '<strong>Arrows and labels</strong> drawn directly on the captured image',
            '<strong>Auto-brightness enhancement</strong> if the image is too dark',
            'Emergency keyword detection for <strong>smoke or heat</strong>'
          ].map((text, i) => (
            <div key={i} className="flex gap-3 items-start">
              <div className="w-2 h-2 rounded-full mt-2 flex-shrink-0 bg-[#00BC7D]" />
              <p className="text-base text-[#d4d4d8]" dangerouslySetInnerHTML={{ __html: text }} />
            </div>
          ))}
        </div>
      </div>
      <div className="flex-1 flex flex-col gap-3">
        <div className="w-full rounded-xl border border-[#27272a] overflow-hidden bg-[#18181b]" style={{ aspectRatio: '16/10' }}>
          <svg width="100%" height="100%" viewBox="0 0 760 475" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
            <rect width="760" height="475" fill="#090909"/>
            <rect x="60" y="60" width="640" height="355" rx="8" fill="#1a1a1a" stroke="#333" strokeWidth="1.5"/>
            <rect x="60" y="225" width="640" height="25" fill="#0f0f0f"/>
            <rect x="324" y="86" width="20" height="20" rx="4" fill="none" stroke="#00BC7D" strokeWidth="2.5"/>
            <circle cx="334" cy="96" r="5" fill="#00BC7D" opacity="0.7"/>
            <rect x="604" y="86" width="20" height="20" rx="4" fill="none" stroke="#00BC7D" strokeWidth="2.5"/>
            <circle cx="614" cy="96" r="5" fill="#00BC7D" opacity="0.7"/>
            <line x1="354" y1="96" x2="600" y2="96" stroke="#00BC7D" strokeWidth="2" strokeDasharray="6,4"/>
            <polygon points="600,90 614,96 600,102" fill="#00BC7D"/>
            <rect x="318" y="66" width="32" height="18" rx="3" fill="#00BC7D" opacity="0.9"/>
            <text x="334" y="79" fontFamily="Inter,sans-serif" fontSize="10" fill="#090909" textAnchor="middle" fontWeight="500">A10</text>
            <rect x="598" y="66" width="32" height="18" rx="3" fill="#00BC7D" opacity="0.9"/>
            <text x="614" y="79" fontFamily="Inter,sans-serif" fontSize="10" fill="#090909" textAnchor="middle" fontWeight="500">A20</text>
            <rect x="400" y="89" width="60" height="14" rx="7" fill="#FDC700" opacity="0.85"/>
            <text x="430" y="100" fontFamily="Inter,sans-serif" fontSize="9" fill="#090909" textAnchor="middle">330Ω</text>
            <rect x="60" y="390" width="640" height="40" fill="#090909" opacity="0.92"/>
            <text x="80" y="415" fontFamily="Inter,sans-serif" fontSize="13" fill="#00BC7D">Step 1 · Place the current-limit resistor from A10 to A20</text>
          </svg>
        </div>
        <div className="text-[#71717b] text-xs">Annotated guidance overlay with live webcam feed</div>
      </div>
    </section>
  );
}

function Slide6() {
  const techStack = [
    { icon: 'AI', name: 'Gemini 2.0', role: 'Agent brain + Vision verification', accent: true },
    { icon: 'PY', name: 'Python', role: 'Core agent loop and state machine', accent: false },
    { icon: 'CV', name: 'OpenCV', role: 'Webcam capture and annotation', accent: false },
    { icon: '⚡', name: 'Arduino', role: 'USB serial testing', accent: false },
    { icon: '⚛', name: 'React', role: 'Live camera feed UI', accent: false },
    { icon: '∞', name: 'State Machine', role: '7-state workflow with safety', accent: false },
    { icon: '🔓', name: 'Open Source', role: 'MIT licensed with mock mode', accent: false },
    { icon: '✓', name: 'pytest', role: 'Full test coverage', accent: false }
  ];

  return (
    <section className="w-full h-full flex flex-col px-16 py-10" style={{ background: bgGradient }}>
      <div className="text-[#00d492] text-xs uppercase mb-3 tracking-wider">Technical Depth · Systems Thinking</div>
      <h2 className="text-4xl font-semibold text-white mb-2">Technology Stack</h2>
      <p className="text-base text-[#d4d4d8] max-w-3xl mb-5">Eight integrated layers — from LLM agent to USB serial — engineered, tested, and shipped in a hackathon weekend.</p>
      <div className="grid grid-cols-4 gap-4 flex-1 content-start">
        {techStack.map((tech, i) => (
          <div key={i} className="flex flex-col gap-2 px-5 py-4 rounded-xl border" style={{
            background: tech.accent ? 'rgba(0,188,125,0.1)' : 'rgba(24,24,27,0.5)',
            borderColor: tech.accent ? '#00BC7D' : '#27272a'
          }}>
            <div className="text-xl font-medium text-[#00BC7D]">
              {tech.icon}
            </div>
            <div className="text-lg font-semibold text-white">{tech.name}</div>
            <div className="text-xs text-[#9f9fa9] leading-relaxed">
              {tech.role}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Slide7() {
  const audiences = [
    { title: 'K–12 Students', desc: 'First breadboard experience without a teacher', color: '#00BC7D' },
    { title: 'University Beginners', desc: 'Practice circuits outside lab hours', color: '#51A2FF' },
    { title: 'Self-Taught Makers', desc: 'Build real circuits with confidence', color: '#FDC700' },
    { title: 'Low-Resource Classrooms', desc: 'Only webcam + breadboard kit needed', color: '#00BC7D' }
  ];

  return (
    <section className="w-full h-full flex flex-row gap-12 items-center px-16 py-10" style={{ background: bgGradient }}>
      <div className="flex-1 flex flex-col gap-8">
        <div>
          <div className="text-[#00d492] text-xs uppercase mb-3 tracking-wider">Product Impact · Light the Way</div>
          <h2 className="text-4xl font-semibold text-white mb-4">
            Real-World<br/>Education Impact
          </h2>
          <p className="text-base text-[#d4d4d8] max-w-md">Viable today: any classroom with a webcam and a $10 breadboard kit can deploy CircuitSensei. No lab, no instructor, no licensing fees.</p>
        </div>
        <div className="flex gap-12">
          <div className="flex flex-col gap-1">
            <div className="text-6xl font-bold text-[#00BC7D]">0</div>
            <div className="text-base text-[#d4d4d8]">Prior knowledge required</div>
          </div>
          <div className="flex flex-col gap-1">
            <div className="text-6xl font-bold text-[#FDC700]">5</div>
            <div className="text-base text-[#d4d4d8]">Steps to first LED</div>
          </div>
        </div>
        <div className="text-base text-[#d4d4d8] leading-relaxed max-w-lg">
          CircuitSensei lowers the barrier to hands-on electronics education — making physical computing as accessible as a YouTube tutorial.
        </div>
      </div>
      <div className="flex-1 flex flex-col gap-4">
        {audiences.map((aud, i) => (
          <div key={i} className="flex gap-4 items-start px-5 py-4 rounded-xl bg-[rgba(24,24,27,0.5)] border border-[#27272a]">
            <div className="w-2 h-2 rounded-full mt-2 flex-shrink-0" style={{ background: aud.color }} />
            <div>
              <div className="text-lg font-semibold text-white mb-1">{aud.title}</div>
              <div className="text-sm text-[#9f9fa9] leading-relaxed">
                {aud.desc}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Slide8() {
  const pillars = [
    { num: '01', title: 'MIT Licensed, Forkable', desc: 'Like Arduino IDE — every line of agent code, every prompt, every test is open. Schools own their tools.' },
    { num: '02', title: 'Hardware-Agnostic Core', desc: 'Arduino today, Raspberry Pi & ESP32 next. The agent abstracts the board — same way Arduino unified microcontrollers.' },
    { num: '03', title: 'Curriculum-Ready', desc: 'Mock mode runs without hardware so teachers can pilot in any classroom. Curated circuit library ships with the repo.' },
    { num: '04', title: 'Community-First Roadmap', desc: 'Public RFCs, contributor docs, and a circuit-sharing format — modeled after the Arduino ecosystem that taught a generation.' }
  ];

  return (
    <section className="w-full h-full flex flex-col px-16 py-8" style={{ background: bgGradient }}>
      <div className="text-[#00d492] text-xs uppercase mb-3 tracking-wider">Originality &amp; Impact · The Arduino of AI Tutoring</div>
      <h2 className="text-4xl font-semibold text-white mb-2">Open Source for Education</h2>
      <p className="text-base text-[#d4d4d8] max-w-3xl mb-5">Arduino democratized hardware by being open. CircuitSensei does the same for AI-guided learning — free, transparent, and built to be remixed by every classroom on Earth.</p>
      <div className="grid grid-cols-2 gap-4 flex-1">
        {pillars.map((step) => (
          <div key={step.num} className="flex gap-4 items-start px-5 py-4 rounded-xl bg-[rgba(24,24,27,0.5)] border border-[#27272a]">
            <div className="text-2xl font-medium text-[#00BC7D] opacity-40 flex-shrink-0">
              {step.num}
            </div>
            <div>
              <h3 className="text-base font-semibold text-white mb-1">{step.title}</h3>
              <p className="text-xs text-[#9f9fa9] leading-relaxed">
                {step.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-5 flex items-center gap-6 flex-wrap">
        <div className="text-[#00BC7D] text-base font-medium">
          github.com/CircuitSensei
        </div>
        <div className="text-[#71717b] text-xs">
          MIT License · Python 3.11 · Mock mode · Inspired by the Arduino ethos
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const [currentSlide, setCurrentSlide] = useState(0);

  const nextSlide = () => {
    setCurrentSlide((prev) => (prev + 1) % slides.length);
  };

  const prevSlide = () => {
    setCurrentSlide((prev) => (prev - 1 + slides.length) % slides.length);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowRight' || e.key === ' ') {
      e.preventDefault();
      nextSlide();
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      prevSlide();
    }
  };

  useState(() => {
    window.addEventListener('keydown', handleKeyDown as any);
    return () => window.removeEventListener('keydown', handleKeyDown as any);
  });

  const CurrentSlideComponent = slides[currentSlide].component;

  return (
    <div className="relative w-full h-full overflow-hidden font-['Inter']">
      <CurrentSlideComponent />

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-3 px-4 py-2 rounded-lg border backdrop-blur-sm bg-[rgba(9,9,11,0.8)] border-[#27272a]">
        <button
          onClick={prevSlide}
          className="w-8 h-8 flex items-center justify-center rounded-md transition-colors hover:bg-white/10 text-[#00BC7D]"
        >
          <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
            <path d="M12 4l-6 6 6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>

        <div className="text-xs text-[#d4d4d8]">
          {currentSlide + 1} / {slides.length}
        </div>

        <button
          onClick={nextSlide}
          className="w-8 h-8 flex items-center justify-center rounded-md transition-colors hover:bg-white/10 text-[#00BC7D]"
        >
          <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
            <path d="M8 4l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>

      <div className="absolute top-6 right-6 text-xs opacity-60 text-[#71717b]">
        {slides[currentSlide].label}
      </div>
    </div>
  );
}
