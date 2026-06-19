'use client';

import React, { useState, useEffect } from 'react';

export default function VisioCourtApp() {
  const [activeTab, setActiveTab] = useState<'home' | 'demo' | 'analytics' | 'contact'>('home');
  const [isMounted, setIsMounted] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);

  // Live state simulator for your athletic facility monitor preview
  const [courtStates, setCourtStates] = useState([
    { id: 1, name: 'Indoor Court 1', status: 'Occupied', time: '42 Minutes Active', color: 'amber' },
    { id: 2, name: 'Indoor Court 2', status: 'Open', time: '18 Minutes Free', color: 'customCyan' },
    { id: 3, name: 'Outdoor Court 3', status: 'Occupied', time: '15 Minutes Active', color: 'amber' },
    { id: 4, name: 'Outdoor Court 4', status: 'Open', time: 'Available Now', color: 'customCyan' },
  ]);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Organic circular theme transition expanding from the toggle switch location
  const handleThemeToggle = () => {
    if (!document.startViewTransition) {
      setIsDarkMode(!isDarkMode);
      return;
    }

    document.startViewTransition(() => {
      setIsDarkMode(!isDarkMode);
    });
  };

  const toggleCourtStatus = (id: number) => {
    setCourtStates((prev) =>
      prev.map((court) => {
        if (court.id === id) {
          const isCurrentlyOpen = court.status === 'Open';
          return {
            ...court,
            status: isCurrentlyOpen ? 'Occupied' : 'Open',
            time: isCurrentlyOpen ? '1 Minute Active' : 'Available Now',
            color: isCurrentlyOpen ? 'amber' : 'customCyan',
          };
        }
        return court;
      })
    );
  };

  return (
    <div className={isDarkMode ? 'bg-zinc-950 text-zinc-50' : 'bg-white text-zinc-900'}>
      <div className={`min-h-screen relative overflow-x-hidden font-sans transition-colors duration-300 ${
        isDarkMode ? 'bg-zinc-950 text-zinc-50' : 'bg-white text-zinc-900'
      }`}>
        
        {/* COMPREHENSIVE STYLESHEET FOR RADIAL THEME MASK & MOTION */}
        <style jsx global>{`
          @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
          }
          @keyframes backgroundDrift {
            from { background-position: 0 0; }
            to { background-position: 120px 120px; }
          }
          @keyframes scanLine {
            0% { transform: translateY(-100%); }
            100% { transform: translateY(100%); }
          }
          
          .animate-grid-drift {
            background-size: 60px 60px;
            background-image: ${isDarkMode 
              ? 'linear-gradient(to right, rgba(255, 255, 255, 0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.04) 1px, transparent 1px)'
              : 'linear-gradient(to right, rgba(161, 161, 170, 0.15) 1px, transparent 1px), linear-gradient(to bottom, rgba(161, 161, 170, 0.15) 1px, transparent 1px)'};
            animation: backgroundDrift 80s linear infinite;
          }
          
          .animate-cascade {
            opacity: 0;
            animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
          }
          .delay-1 { animation-delay: 100ms; }
          .delay-2 { animation-delay: 200ms; }
          .delay-3 { animation-delay: 350ms; }
          
          @keyframes softPulseCyan {
            0%, 100% { opacity: 1; box-shadow: 0 0 0px rgba(90, 195, 220, 0); }
            50% { opacity: 0.8; box-shadow: 0 0 8px rgba(90, 195, 220, 0.6); }
          }
          .animate-pulse-cyan { animation: softPulseCyan 3s infinite ease-in-out; }
          
          @keyframes softPulseAmber {
            0%, 100% { opacity: 1; box-shadow: 0 0 0px rgba(245, 158, 11, 0); }
            50% { opacity: 0.8; box-shadow: 0 0 8px rgba(245, 158, 11, 0.5); }
          }
          .animate-pulse-amber { animation: softPulseAmber 3s infinite ease-in-out; }
          
          .scan-laser {
            background: linear-gradient(to bottom, transparent, rgba(90, 195, 220, 0.15), transparent);
            animation: scanLine 4s linear infinite;
          }

          /* Round sweeping fluid view transition from upper corner */
          ::view-transition-old(root),
          ::view-transition-new(root) {
            animation: none;
            mix-blend-mode: normal;
          }
          ::view-transition-new(root) {
            clip-path: circle(0% at calc(100% - 64px) 40px);
            animation: revealTheme 0.7s cubic-bezier(0.4, 0, 0.2, 1) forwards;
          }
          @keyframes revealTheme {
            to { clip-path: circle(150% at calc(100% - 64px) 40px); }
          }
        `}</style>

        {/* Background Animated Technical Grid */}
        <div className="absolute inset-0 animate-grid-drift pointer-events-none z-0" />

        {/* FIXED NAVBAR */}
        <header className={`fixed top-0 left-0 right-0 h-20 backdrop-blur-xl border-b z-50 flex items-center justify-between px-8 md:px-16 transition-colors duration-300 ${
          isDarkMode ? 'bg-zinc-950/80 border-zinc-900' : 'bg-white/80 border-zinc-100'
        }`}>
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('home')}>
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center shadow-md ${isDarkMode ? 'bg-zinc-900' : 'bg-zinc-950'}`}>
              <div className="w-3.5 h-3.5 rounded-full border-2 border-[#5ac3dc] animate-pulse-cyan" />
            </div>
            <span className={`font-bold tracking-tight text-xl ${isDarkMode ? 'text-white' : 'text-zinc-950'}`}>
              Visio<span className="text-[#5ac3dc]">Court</span>
            </span>
          </div>

          <div className="flex items-center space-x-6">
            {/* Tab Links */}
            <nav className={`hidden md:flex space-x-1 p-1 rounded-full ${isDarkMode ? 'bg-zinc-900' : 'bg-zinc-100'}`}>
              {(['home', 'demo', 'analytics', 'contact'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-6 py-2 rounded-full text-sm font-medium capitalize transition-all duration-300 ${
                    activeTab === tab
                      ? (isDarkMode ? 'bg-zinc-800 text-white shadow-sm' : 'bg-white text-zinc-950 shadow-sm')
                      : (isDarkMode ? 'text-zinc-400 hover:text-white' : 'text-zinc-500 hover:text-zinc-950')
                  }`}
                >
                  {tab}
                </button>
              ))}
            </nav>

            {/* EXPANDED SUN / MOON CONTROL PILL MODULE */}
            <div className={`flex items-center space-x-2.5 px-3 py-1.5 rounded-full border ${
              isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-100 border-zinc-200'
            }`}>
              <span className={`text-xs transition-opacity duration-200 ${!isDarkMode ? 'opacity-100' : 'opacity-40'}`}>☀️</span>
              <button 
                onClick={handleThemeToggle}
                className={`w-9 h-5 rounded-full p-0.5 transition-colors duration-300 relative focus:outline-none ${
                  isDarkMode ? 'bg-zinc-700' : 'bg-zinc-300'
                }`}
                aria-label="Toggle interface theme"
              >
                <div className={`bg-white w-4 h-4 rounded-full shadow-sm transform transition-transform duration-300 ${
                  isDarkMode ? 'translate-x-4' : 'translate-x-0'
                }`} />
              </button>
              <span className={`text-xs transition-opacity duration-200 ${isDarkMode ? 'opacity-100' : 'opacity-40'}`}>🌙</span>
            </div>
          </div>
        </header>

        {/* MAIN CONTAINER FRAME */}
        <main className="max-w-7xl mx-auto pt-36 pb-32 px-8 md:px-16 min-h-[calc(100vh-80px)] relative z-10">
          
          {/* ==============================================
              1. HOME TAB / ENTRY SLIDE
              ============================================== */}
          {activeTab === 'home' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-center w-full">
              
              <div className="lg:col-span-7 flex flex-col justify-center space-y-8">
                <div className="space-y-4">
                  <span className={`inline-block px-3 py-1 text-xs font-semibold rounded-full animate-cascade border ${
                    isDarkMode ? 'bg-zinc-900 text-zinc-300 border-zinc-800' : 'bg-zinc-100 text-zinc-800 border-zinc-200'
                  }`}>
                    Edge Intelligence Launching 2026
                  </span>
                  <h1 className={`text-6xl md:text-7xl font-extrabold tracking-tight leading-[1.1] animate-cascade delay-1 ${
                    isDarkMode ? 'text-white' : 'text-zinc-950'
                  }`}>
                    Visio<span className="text-[#5ac3dc]">Court</span>
                  </h1>
                  <p className={`text-xl font-medium leading-relaxed max-w-xl animate-cascade delay-2 ${
                    isDarkMode ? 'text-zinc-400' : 'text-zinc-500'
                  }`}>
                    Computer vision analytics monitoring local court infrastructure. Real time capacity tracking with zero biometrics storage and 5 second state latency.
                  </p>
                </div>

                <div className="space-y-3 max-w-md animate-cascade delay-3">
                  {/* FORMSPREE: WIRED WAITLIST EMAIL CAPTURE */}
                  <form action="https://formspree.io/f/xzdqnawr" method="POST" className="flex flex-col sm:flex-row gap-3">
                    <input
                      type="email"
                      name="email"
                      required
                      placeholder="Enter your email address"
                      className={`flex-grow px-5 py-3 rounded-xl border text-sm focus:outline-none focus:border-[#5ac3dc] transition-all duration-200 ${
                        isDarkMode ? 'border-zinc-800 bg-zinc-900 text-white placeholder-zinc-600' : 'border-zinc-200 bg-white text-zinc-900 placeholder-zinc-400'
                      }`}
                    />
                    <button type="submit" className={`px-6 py-3 rounded-xl font-semibold transition-all duration-200 shadow-md whitespace-nowrap ${
                      isDarkMode ? 'bg-white text-zinc-950 hover:bg-zinc-200' : 'bg-zinc-950 text-white hover:bg-zinc-800'
                    }`}>
                      Join Waitlist
                    </button>
                  </form>
                  <p className="text-xs text-zinc-400 font-medium pt-1">
                    Corporate & facility pilot programs also available.
                  </p>
                </div>
              </div>

              <div className="lg:col-span-5 animate-cascade delay-3">
                <div className={`border rounded-2xl shadow-2xl overflow-hidden relative ${
                  isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
                }`}>
                  <div className="absolute inset-0 scan-laser pointer-events-none z-10" />

                  <div className={`border-b px-6 py-4 flex items-center justify-between ${
                    isDarkMode ? 'border-zinc-800 bg-zinc-950/50' : 'border-zinc-100 bg-zinc-50/50'
                  }`}>
                    <div className="flex items-center space-x-2">
                      <div className="w-2.5 h-2.5 rounded-full bg-[#5ac3dc] animate-pulse-cyan" />
                      <span className={`text-sm font-semibold ${isDarkMode ? 'text-zinc-200' : 'text-zinc-800'}`}>Live Facility Monitor</span>
                    </div>
                    <span className={`text-xs px-2.5 py-1 rounded-md font-medium ${isDarkMode ? 'bg-zinc-800 text-zinc-400' : 'bg-zinc-100 text-zinc-600'}`}>
                      Live scan active
                    </span>
                  </div>

                  <div className="p-6 space-y-4">
                    {courtStates.slice(0, 3).map((court) => (
                      <div 
                        key={court.id} 
                        className={`flex items-center justify-between p-3.5 border rounded-xl ${
                          isDarkMode ? 'border-zinc-800/60 bg-zinc-900 text-white' : 'border-zinc-100 bg-white text-zinc-900'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div className="w-2 h-2 rounded-full bg-zinc-400" />
                          <span className="text-sm font-bold">{court.name}</span>
                        </div>
                        <div className="flex items-center space-x-4">
                          <span className="text-xs text-zinc-400 font-medium">{court.time}</span>
                          <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                            court.color === 'customCyan' 
                              ? 'bg-[#5ac3dc]/10 text-[#5ac3dc] border border-[#5ac3dc]/20' 
                              : (isDarkMode ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20' : 'bg-amber-50 text-amber-600 border border-amber-100')
                          }`}>
                            {court.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* ==============================================
              2. DEMO TAB / SIMULATOR SLIDE
              ============================================== */}
          {activeTab === 'demo' && (
            <div className="w-full flex flex-col space-y-12">
              <div className="max-w-2xl space-y-3">
                <h2 className={`text-4xl font-extrabold tracking-tight animate-cascade ${isDarkMode ? 'text-white' : 'text-zinc-950'}`}>
                  Simulated Intelligence Console
                </h2>
                <p className={`text-lg animate-cascade delay-1 ${isDarkMode ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  Interact with our mock cameras below. Tap the selection circles to simulate computer vision events and watch the network recompute latency metrics.
                </p>
              </div>

              {/* INTERACTIVE MOCK CAMERAS WITH SELECTION CIRCLES */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-cascade delay-2">
                {courtStates.map((court) => (
                  <div 
                    key={court.id}
                    onClick={() => toggleCourtStatus(court.id)}
                    className={`p-6 rounded-2xl border transition-all duration-300 cursor-pointer group relative overflow-hidden ${
                      isDarkMode 
                        ? (court.status === 'Open' ? 'bg-zinc-900 border-[#5ac3dc] shadow-[0_0_20px_rgba(90,195,220,0.15)]' : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700')
                        : (court.status === 'Open' ? 'bg-white border-[#5ac3dc] shadow-[0_0_20px_rgba(90,195,220,0.12)]' : 'bg-white border-zinc-200 hover:border-zinc-400')
                    }`}
                  >
                    <div className="space-y-6">
                      <div className="flex items-center justify-between">
                        {/* THEME SENSITIVE SELECTION CIRCLES */}
                        <div className="flex items-center space-x-3">
                          <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                            court.status === 'Open' 
                              ? 'border-[#5ac3dc] bg-[#5ac3dc]/10 ring-4 ring-[#5ac3dc]/20' 
                              : (isDarkMode ? 'border-zinc-700' : 'border-zinc-300')
                          }`}>
                            {court.status === 'Open' && <div className="w-2 h-2 rounded-full bg-[#5ac3dc]" />}
                          </div>
                          <span className="text-xs text-zinc-400 font-mono tracking-wider">CAMERA ID 0{court.id}</span>
                        </div>
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wide uppercase ${
                          court.color === 'customCyan' ? 'bg-[#5ac3dc]/10 text-[#5ac3dc]' : (isDarkMode ? 'bg-amber-500/10 text-amber-500' : 'bg-amber-50 text-amber-600')
                        }`}>
                          {court.status}
                        </span>
                      </div>

                      <div className="space-y-1">
                        <h4 className={`text-lg font-bold ${isDarkMode ? 'text-white' : 'text-zinc-900'}`}>
                          {court.name}
                        </h4>
                        <p className="text-sm text-zinc-500">
                          {court.time}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* EMBEDDED PROTOTYPE VIDEO PLAYER WITHOUT VERIFICATION BADGE */}
              <div className={`border p-6 md:p-8 rounded-3xl transition-colors duration-300 ${
                isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
              }`}>
                <div className="flex items-center justify-between mb-8">
                  <div>
                    <h3 className={`text-2xl font-bold tracking-tight mb-2 ${isDarkMode ? 'text-white' : 'text-zinc-950'}`}>
                      Live Prototype Demo
                    </h3>
                    <p className="text-sm text-zinc-500">
                      Watch our hardware capture mapping algorithms deployed in a live test environment.
                    </p>
                  </div>
                </div>

                <div className={`relative w-full aspect-video rounded-2xl overflow-hidden border ${
                  isDarkMode ? 'bg-zinc-950 border-zinc-800' : 'bg-zinc-100 border-zinc-200'
                }`}>
                  <iframe 
                    width="100%" 
                    height="100%" 
                    src="https://www.youtube.com/embed/ZqQdA2nn5H0?si=_BXzxwUaSV2gRxK_" 
                    title="YouTube video player" 
                    frameBorder="0" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
                    referrerPolicy="strict-origin-when-cross-origin" 
                    allowFullScreen
                    className="absolute inset-0 w-full h-full object-cover"
                  ></iframe>
                </div>
              </div>
            </div>
          )}

          {/* ==============================================
              3. ANALYTICS TAB / DATA SLIDE
              ============================================== */}
          {activeTab === 'analytics' && (
            <div className="w-full flex flex-col space-y-10">
              <div className="max-w-2xl space-y-3">
                <h2 className={`text-4xl font-extrabold tracking-tight ${isDarkMode ? 'text-white' : 'text-zinc-950'}`}>
                  Accuracy & Verification Analytics
                </h2>
                <p className="text-lg text-zinc-500">
                  Data pipelines and academic benchmarks backing our computer vision deployment.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-cascade delay-2">
                
                <div className={`lg:col-span-8 p-8 rounded-3xl flex flex-col justify-between min-h-[260px] border ${
                  isDarkMode ? 'bg-zinc-900 border-zinc-800 text-white' : 'bg-zinc-955 bg-zinc-950 text-white border-transparent'
                }`}>
                  <div className="space-y-2">
                    <span className="text-zinc-400 text-xs font-bold tracking-widest uppercase">Computer Vision Core</span>
                    <h3 className="text-3xl font-bold tracking-tight">
                      Superior processing pipelines mapping court states under high dynamic range lighting conditions.
                    </h3>
                  </div>
                  <div className="flex items-baseline space-x-3">
                    <span className="text-6xl font-extrabold tracking-tighter">94%</span>
                    <span className="text-zinc-400 text-sm font-semibold">Operational Accuracy tracking verified in field trials</span>
                  </div>
                </div>

                <div className={`lg:col-span-4 p-8 rounded-3xl flex flex-col justify-between min-h-[260px] border ${
                  isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
                }`}>
                  <div className="w-10 h-10 rounded-full bg-[#5ac3dc]/10 flex items-center justify-center">
                    <div className="w-4 h-4 rounded-full bg-[#5ac3dc]" />
                  </div>
                  <div className="space-y-2">
                    <h4 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-zinc-900'}`}>Zero Biometrics Stored</h4>
                    <p className="text-sm text-zinc-500 leading-relaxed">
                      Our local edge pipeline drops video feeds immediately after detecting state availability changes. No facial structures recorded.
                    </p>
                  </div>
                </div>

                <div className={`lg:col-span-4 p-8 rounded-3xl flex flex-col justify-between min-h-[260px] border ${
                  isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
                }`}>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${isDarkMode ? 'bg-zinc-800 text-zinc-200' : 'bg-zinc-100 text-zinc-800'}`}>
                    <span className="text-xs font-bold">MIT</span>
                  </div>
                  <div className="space-y-2">
                    <h4 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-zinc-900'}`}>Academic Verification</h4>
                    <p className="text-sm text-zinc-500 leading-relaxed">
                      Undergraduate research technology modeling vetted by academic advisors and presented directly at the MIT Undergraduate Research Technology Conference.
                    </p>
                  </div>
                </div>

                <div className={`lg:col-span-8 p-8 rounded-3xl flex flex-col justify-between min-h-[260px] border ${
                  isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-50 border-zinc-150'
                }`}>
                  <div className={`flex items-center justify-between border-b pb-4 ${isDarkMode ? 'border-zinc-800' : 'border-zinc-200'}`}>
                    <span className={`text-sm font-bold ${isDarkMode ? 'text-zinc-200' : 'text-zinc-800'}`}>Capacity Optimization Engine</span>
                    <span className={`text-xs px-2.5 py-1 rounded-md font-medium ${isDarkMode ? 'bg-zinc-800 text-zinc-300' : 'bg-zinc-200 text-zinc-700'}`}>Active algorithm</span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-6 pt-6">
                    <div>
                      <p className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-zinc-950'}`}>5s</p>
                      <p className="text-xs text-zinc-500 mt-1">State Latency Buffer</p>
                    </div>
                    <div>
                      <p className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-zinc-950'}`}>100%</p>
                      <p className="text-xs text-zinc-500 mt-1">Local Processing Nodes</p>
                    </div>
                    <div>
                      <p className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-zinc-950'}`}>Zero</p>
                      <p className="text-xs text-zinc-500 mt-1">External Storage Reliance</p>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* ==============================================
              4. CONTACT TAB / FORM SLIDE
              ============================================== */}
          {activeTab === 'contact' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-start w-full">
              
              <div className="lg:col-span-5 flex flex-col justify-center space-y-8">
                <div className="space-y-4">
                  <h2 className={`text-4xl font-extrabold tracking-tight ${isDarkMode ? 'text-white' : 'text-zinc-950'}`}>Partner With Us</h2>
                  <p className="text-lg text-zinc-500 leading-relaxed">
                    We are actively looking to deploy pilots at golf clubs, country clubs, university tennis facilities, and public pickleball parks. General users can also join the waitlist below.
                  </p>
                </div>

                <div className="space-y-4 text-sm text-zinc-500">
                  <div>
                    <p className={`font-semibold ${isDarkMode ? 'text-zinc-200' : 'text-zinc-800'}`}>General Information</p>
                    <p>administration@visio<span className="text-[#5ac3dc]">court</span>.com</p>
                  </div>
                  <div>
                    <p className={`font-semibold ${isDarkMode ? 'text-zinc-200' : 'text-zinc-800'}`}>Operational Inquiries</p>
                    <p>deployment@visio<span className="text-[#5ac3dc]">court</span>.com</p>
                  </div>
                </div>
              </div>

              <div className={`lg:col-span-7 p-8 md:p-10 rounded-3xl border ${
                isDarkMode ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
              }`}>
                {/* FORMSPREE: FULL CONTACT DATA CAPTURE */}
                <form action="https://formspree.io/f/xzdqnawr" method="POST" className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Your Name</label>
                      <input
                        type="text"
                        name="name"
                        required
                        className={`w-full px-4 py-3 rounded-xl border text-sm focus:outline-none focus:border-[#5ac3dc] ${
                          isDarkMode ? 'border-zinc-800 bg-zinc-950 text-white' : 'border-zinc-200 bg-white text-zinc-900'
                        }`}
                        placeholder="Jane Doe"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Facility Name (Optional)</label>
                      <input
                        type="text"
                        name="facility"
                        className={`w-full px-4 py-3 rounded-xl border text-sm focus:outline-none focus:border-[#5ac3dc] ${
                          isDarkMode ? 'border-zinc-800 bg-zinc-950 text-white' : 'border-zinc-200 bg-white text-zinc-900'
                        }`}
                        placeholder="Leave blank if player"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Email Address</label>
                    <input
                      type="email"
                      name="email"
                      required
                      className={`w-full px-4 py-3 rounded-xl border text-sm focus:outline-none focus:border-[#5ac3dc] ${
                        isDarkMode ? 'border-zinc-800 bg-zinc-950 text-white' : 'border-zinc-200 bg-white text-zinc-900'
                      }`}
                      placeholder="player@email.com"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Your Message</label>
                    <textarea
                      rows={4}
                      name="message"
                      className={`w-full px-4 py-3 rounded-xl border text-sm focus:outline-none focus:border-[#5ac3dc] ${
                        isDarkMode ? 'border-zinc-800 bg-zinc-950 text-white' : 'border-zinc-200 bg-white text-zinc-900'
                      }`}
                      placeholder="Let us know if you want to deploy a pilot or just stay updated..."
                    />
                  </div>

                  {/* USER WAITLIST CHECKBOX */}
                  <div className="flex items-center space-x-3 py-2">
                    <input
                      type="checkbox"
                      id="waitlist-checkbox"
                      name="join_general_waitlist"
                      value="yes"
                      defaultChecked
                      className="w-4 h-4 rounded border-zinc-300 text-[#5ac3dc] focus:ring-[#5ac3dc]"
                    />
                    <label htmlFor="waitlist-checkbox" className={`text-sm ${isDarkMode ? 'text-zinc-300' : 'text-zinc-700'}`}>
                      Join the general user waitlist for app launch updates
                    </label>
                  </div>

                  <button type="submit" className={`w-full py-4 rounded-xl font-semibold transition-all duration-200 shadow-md ${
                    isDarkMode ? 'bg-white text-zinc-950 hover:bg-zinc-200' : 'bg-zinc-950 text-white hover:bg-zinc-800'
                  }`}>
                    Submit Details
                  </button>
                </form>
              </div>

            </div>
          )}

        </main>

        {/* BOTTOM FIXED FOOTER */}
        <footer className={`absolute bottom-0 left-0 right-0 h-16 border-t flex items-center justify-between px-8 md:px-16 text-xs text-zinc-400 bg-transparent z-30 ${
          isDarkMode ? 'border-zinc-900' : 'border-zinc-100'
        }`}>
          <span>
            Visio<span className="text-[#5ac3dc]">Court</span> Operations 2026
          </span>
          <div className="flex space-x-6 relative z-40">
            <span className="hover:text-zinc-600 dark:hover:text-zinc-300 cursor-pointer">Security Standards</span>
            <span className="hover:text-zinc-600 dark:hover:text-zinc-300 cursor-pointer">Privacy Guidelines</span>
          </div>
        </footer>
      </div>
    </div>
  );
}<footer className="mt-12 text-center text-sm text-gray-400">
<p>
  By joining the waitlist, you agree to our <a href="/privacy" className="underline">Privacy Policy</a>.
</p>
</footer>