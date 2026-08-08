# 👻 Aura — The AI They Can't See, Can't Detect, Can't Stop

<div align="center">
  <img src="logo.png" alt="Aura Logo" width="300" />
</div>

**An invisible AI overlay that lives on your screen — answers questions, solves problems, analyzes screenshots, and feeds you real-time intelligence. Works during interviews, exams, meetings, or anything on your screen. Invisible to screen recordings. Undetectable by proctoring software. You see everything. They see nothing.**

[![AI Powered](https://img.shields.io/badge/AI-Vision%20%7C%20Voice%20%7C%20Multi--Provider-purple.svg)](https://github.com)
[![Stealth Mode](https://img.shields.io/badge/Stealth-Screen%20Capture%20Protected-green.svg)](https://github.com)
[![Cost](https://img.shields.io/badge/Cost-Free%20%7C%20Open%20Source-brightgreen.svg)](https://github.com)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=flat&logo=windows&logoColor=white)](#-system-requirements)
[![macOS](https://img.shields.io/badge/macOS-In%20Progress-orange?style=flat&logo=apple&logoColor=white)](https://github.com/Rkcr7/Aura-AI/tree/macos)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)

> **👻 Invisible by Design** — Screen capture protected. Hidden from taskbar. Undetectable by Zoom, Teams, Google Meet, and every proctoring tool on the market.

> **💸 $0. Forever.** — No subscriptions. No credits. No paywalls. Bring your own free API keys and **own** it.

> **⚡ Stupidly Fast** — Powered by **Cerebras** (~2,000-3,000 tokens/sec) and **Groq** (~400-700 tokens/sec) — the two fastest AI inference engines on Earth. Answers hit your screen before the interviewer finishes talking. Nothing else comes close.

> **🖥️ Platform Support** — **Windows 10/11** is the primary, fully-supported platform (this `master` branch). A **macOS** port is in active development on the [`macos`](https://github.com/Rkcr7/Aura-AI/tree/macos) branch — feature parity is **work-in-progress** and some stealth behaviors are limited compared to Windows. macOS contributors welcome via PRs targeting the `macos` branch.

---

## 🆕 What's New in v1.1.0

| | |
|--------|--------|
| ⚡ **Cerebras Vision** | Cerebras now does image input via **Gemma 4 31B** at ~1850 tok/s — the fastest screenshot-to-answer path Aura has ever had, and the new vision default |
| 🚀 **Latest models** | Refreshed across every provider: GPT-OSS 120B, Gemma 4 31B, Gemini 3.6 / 3.5 Flash |
| 🎯 **Tuned for speed** | Cerebras drives both text and vision by default. Need maximum accuracy on a dense screenshot? `Alt+T` swaps to Gemini 3.6 Flash |
| 🏷️ **Labelled model picker** | Every model now shows its speed/accuracy tradeoff right in the dropdown, so you pick the right one under pressure |
| 🎤 **Leaner audio pipeline** | ~70% less bandwidth and 8× fewer messages, with sample rate locked to Deepgram for cleaner transcription |
| 👁️ **Sharper at low opacity** | Headings, bold text and code blocks are noticeably easier to read at 40% transparency |
| ♿ **Respects reduced motion** | Animations settle when your OS asks for it — and a stiller overlay is a less noticeable one |

> **Upgrading?** Re-copy `ai_providers.example.json` to pick up the new model
> lineup — provider catalogues moved on since v1.0.0.

---

## ✨ What is Aura?

Aura isn't just another interview prep tool. It's your secret weapon for **any challenge**—from aptitude tests to quantitative brain-twisters, behavioral showdowns to certification exams. Aura is a **revolutionary AI assistant** that operates in real-time, providing candidates with the critical insights they need to excel in high-stakes situations—all without ever tripping tab-switching warnings, thanks to its stealthy, seamless design.

Imagine having a world-class expert whispering in your ear, helping you deconstruct complex problems, articulate your thoughts, and navigate the toughest questions with confidence. **That's Aura.**

### How It Works

Aura sits on top of your screen as an **invisible overlay** during live interviews and exams. It **listens** to conversations in real-time via Deepgram speech-to-text, **generates** intelligent coaching responses using blazing-fast LLMs (Groq, Cerebras, Gemini), and lets you **screenshot** any problem for instant Vision AI solutions—all while staying **completely hidden** from screen recordings, proctoring software, and human observers.

---

## 🎥 See Aura in Action

Real screenshots and recordings from a live Aura session — no mockups, no staging.

---

### 🛠️ Setup Walkthrough

<details>
<summary><b>Step 1 · Your Profile — Enter your details and pick an interview focus</b></summary>

<div align="center">
  <img src="Media/Onboarding-1.png" alt="Aura Onboarding — Profile Setup" width="750" />
</div>

Fill in your **name**, **target company**, and **role**, then select your **interview focus** (Behavioral, Coding, System Design, Data Structures, Cultural Fit, or HR/Screening). Paste your full resume and job description for hyper-personalized coaching. Hit the **⚡ Demo** button to auto-fill with sample data for quick testing.

</details>

<details>
<summary><b>Step 2 · AI Setup — Configure primary, secondary, and vision models</b></summary>

<div align="center">
  <img src="Media/AI Setup-2.png" alt="Aura AI Setup — Model Configuration" width="750" />
</div>

Choose your **Primary AI Model** (default for all responses — Cerebras shown here for maximum speed) and an optional **Secondary Model** (switch anytime with `Alt+W`). Below, configure your **Vision AI Model** for screenshot analysis — Gemini delivers the best accuracy, Groq Llama 4 is the fastest. The **Quick Switch Hotkeys** panel shows `Alt+Q`, `Alt+W`, `Alt+E` for instant model switching mid-interview.

</details>

<details>
<summary><b>Step 3 · Advanced Config — Manage API keys and provider connections</b></summary>

<div align="center">
  <img src="Media/Config-3.png" alt="Aura Advanced Config — API Key Management" width="750" />
</div>

The **Advanced Config** tab is the raw control panel. Enter your **Deepgram API key** (speech-to-text), then manage **multiple API keys per provider** — notice Groq showing 5 keys for maximum rate-limit resilience. Each provider shows its base URL, keys, and a **Test Connection** button to verify everything works before going live. Changes are saved directly to `ai_providers.json` and `.env`.

</details>

<details>
<summary><b>Step 4 · Commands & Tips — Complete hotkey reference with pro tips</b></summary>

<div align="center">
  <img src="Media/Commands-4.png" alt="Aura Commands & Tips — Hotkey Reference" width="750" />
</div>

The final onboarding tab is your **cheat sheet**. Three highlighted pro-tip cards cover: 🔒 **Stealth Professional Tip** (always use global hotkeys — never click Aura during proctored exams), 📸 **Multi-Screenshot Analysis** (queue up to 4 screenshots with `Alt+S`, process all at once with `Alt+P`), and ⚡ **Speed Strategy** (use `Alt+E` to auto-select the fastest healthy provider). Below, every hotkey is organized by category with color-coded badges.

</details>

---

### ✅ Pre-Flight Check & Permissions

<table>
<tr>
<td width="50%">

<div align="center">
  <img src="Media/Permissions-5.png" alt="Aura Pre-Flight — Requesting Microphone Permission" width="370" />
</div>

**Microphone Permission Request** — Aura's Pre-Flight Check runs before every session. It validates your microphone access, backend connection, Deepgram API, and all configured AI providers. Grant the mic permission prompt to proceed.

</td>
<td width="50%">

<div align="center">
  <img src="Media/permissions-6.png" alt="Aura Pre-Flight — All Systems Green" width="370" />
</div>

**All Systems Go ✅** — Every check is green: Microphone Permission OK, Microphone Selected (NVIDIA Broadcast detected), Backend Connected, Deepgram API OK, Primary Cerebras OK, Secondary Groq OK, Primary Vision Gemini OK, Secondary Vision Groq OK. Hit **Start Interview** and you're live.

</td>
</tr>
</table>

---

### 👻 Stealth Mode in Action

See how Aura overlays **directly on top of LeetCode** during a live coding session — invisible to screen recordings, fully transparent, and controlled entirely via hotkeys.

<table>
<tr>
<td width="50%">

<div align="center">
  <img src="Media/transparency-8.png" alt="Aura Stealth — Screen Share Protection" width="370" />
</div>

**Screen Share Protection** — Aura runs during a live LeetCode session with "Share Entire Screen" active. The Aura window overlays the coding environment but is **excluded from the screen capture** via `WDA_EXCLUDEFROMCAPTURE`. Notice the "Microphone Muted" status bar and model switcher visible only to the user.

</td>
<td width="50%">

<div align="center">
  <img src="Media/transparency-9 - max trasnparency.png" alt="Aura Stealth — Maximum Transparency Overlay" width="370" />
</div>

**Maximum Transparency Mode** — With `Alt+1` (40% opacity), Aura becomes a near-invisible ghost overlay. The Live Interview Session indicator, MUTED/RESET controls, and AI model badges (`Primary: Cerebras`) are barely visible — just enough for you, completely invisible to anyone observing your screen. The LeetCode problem beneath is fully readable.

</td>
</tr>
</table>

<div align="center">
  <img src="Media/Permissions-7.png" alt="Aura Stealth — Vision AI Permissions with Screen Share" width="750" />
</div>

<p align="center"><b>Vision AI + Screen Share</b> — When using Vision AI during a proctored session, Aura shares your entire screen for screenshot capture. The "Also share system audio" toggle (circled) enables audio capture alongside visual analysis. The Aura window itself remains hidden from the capture feed — only you see it.</p>

---

### 🎬 Video Demos

> **Note:** Click any link below to watch the `.mp4` demo directly. These recordings show actual Aura features running in real-time.

| Demo | What You'll See | File |
|:-----|:----------------|:-----|
| 👻 **Ghost Mode Toggle** | Toggling click-through mode with `Alt+X` — interact with apps underneath Aura while its overlay stays visible. Aura becomes a transparent layer you can see but not accidentally click | [▶ easy-toggle-alt+z-12.mp4](Media/easy-toggle-alt+z-%2012.mp4) |
| 🖱️ **Click Passthrough** | Demonstrating Ghost Mode in practice — clicks pass directly through Aura's overlay to the application beneath (browser, IDE, exam platform). Zero interference with your workflow | [▶ passthrough-10.mp4](Media/paasthrough-10.mp4) |
| 🎤 **Real-Time AI Coaching** | Full end-to-end demo: live microphone transcription → AI processing → real-time coaching responses appearing on the overlay. Watch Aura listen, think, and respond in under 2 seconds | [▶ realtime-working-11.mp4](Media/realtime-working-11.mp4) |
| 📸 **Vision AI Screenshot** | Capturing a problem with `Alt+S`, processing with `Alt+P`, and receiving AI-generated solutions overlaid on screen. Multi-screenshot queue in action with instant analysis | [▶ screenshot-13.mp4](Media/screenshot-13.mp4) |

---

## 🔥 Aura in the Hot Seat: Crush Every Round

### The Scene: Your Make-or-Break Moment

Clock's ticking. Stakes are high. Aura's got you covered—whether it's an interview or an exam. Its **Stealth Mode** ensures you can access its powerful features without raising any red flags, keeping your focus entirely on the task at hand.

---

### **Round 1: Behavioral Mastery** 🧠

**The Curveball**: *"Tell me about a time you turned failure into success."*

- **Without Aura**: Stammering, scrambling, stuck.
- **With Aura (Stealth Mode active)**:
  - Real-time transcription catches every word, discreetly.
  - **STAR-method gold** pops up on your screen, invisible to others—customized to your resume and role.
  - You drop a story so smooth, they're taking notes.

*Boom: You're unforgettable.*

---

### **Round 2: Quantitative Crusher** 📊

**The Brainteaser**: *"Calculate the probability of 7 consecutive heads in all three coins tossed at same time in 100 coin tosses."*

- **With Aura (Stealth Mode is your superpower here)**:
  1. `Alt+Shift+S` → **Proctoring Stealth Mode** activates. Aura becomes a transparent, click-through overlay, invisible to screen recording and proctoring software.
  2. `Alt+V` → Vision Mode activates, ready to analyze.
  3. `Alt+S` → Silently screenshots the problem from the exam platform.
  4. `Alt+P` → Quantitative AI analyzes the problem in the background.
  5. Solutions appear ghosted on your screen—only you can see them.
  6. Submit answers confidently without ever switching tabs or alerting proctoring systems.
  7. Control Aura's window movements and scroll through suggestions using global hotkeys, all while the exam window remains active and focused.

*You solve complex problems with ease, leaving no trace.*

---

### **Round 3: Coding Glory** 💻

**The Puzzle**: Reverse-engineer a slow API call under pressure during a live coding session.

- **Without Aura**: Sweat-soaked guesswork.
- **With Aura (Stealth Mode ensuring seamless assistance)**:
  1. `Alt+V` → Vision Mode ignites, ready for the code.
  2. `Alt+S` → Screenshot the problematic code or error message, discreetly.
  3. `Alt+P` → Vision AI unleashes its power, overlaying suggestions:
     - **Killer solutions** in JS, Python, Java, SQL, and more.
     - **Time complexity breakdowns** for optimal answers.
     - **Pro-level explanations** to articulate your thought process.
     - All assistance is delivered via Aura's overlay, invisible to screen sharing.

*You code like a rockstar, navigating complex challenges with AI-powered insights, leaving them stunned.*

---

### **Round 4: System Design Triumph** 🏗️

**The Beast**: *"Design a global payment system for millions."*

- **With Aura (Stealth Mode providing discreet guidance)**:
  - **Real-time transcription** catches the requirements as the interviewer speaks.
  - Aura provides quick analysis of constraints, goals, and trade-offs—visible only to you.
  - **API Design**: RESTful/GraphQL endpoint suggestions with detailed descriptions.
  - **Scalable architectures**—sharding, replication, microservices, oh my!
  - **Caching tricks** and **load balancing hacks**.
  - Buzzwords like Kafka, Redis, Kubernetes—served hot and contextually.

*You sketch a masterpiece, guided by expert insights, and they're hiring you yesterday.*

---

## 🌟 Why Aura Obliterates the Competition

Aura doesn't just compete—it **crushes** subscription traps like **Interview Coder**, **Parakeet AI**, **LockedIn AI** and similars. Check the carnage:

| **Feature** | **Aura** | **Interview Coder** | **Parakeet AI** | **LockedIn AI** |
|---|---|---|---|---|
| **Cost** | 🆓 Free Forever | 💸 $25/month | 💸 Credits | 💸 Subscription |
| **Vision AI** | ✅ Screenshots + Diagrams + Code | ❌ Nope | ❌ Nada | ❌ Never |
| **Stealth** | ✅ **Undetectable** (Screen Capture Proof, Focus-Free, Taskbar Invisible, Ghost Mode) | ✅ Half-Baked | ✅ Kinda | ❌ Exposed |
| **AI Muscle** | ✅ Multi-Provider Dual Engines + Key Rotation | ❌ One-Trick | ❌ Weak | ❌ Lame |
| **Scope** | ✅ Coding, System Design, Aptitude, Quantitative, Behavioral | ✅ Coding Only | ✅ Barely | ✅ Meh |
| **Speed** | ⚡ **Fastest on Earth** — Cerebras (~2,000 tok/s) + Groq (~400 tok/s) = sub-second full answers | ❌ Slow (GPT latency) | ❌ Sluggish | ❌ Laggy |

**Aura's Knockout Punch**: Fastest inference in the game (Cerebras + Groq), totally invisible (screen-capture-proof stealth), and **$0 forever**. Competitors charge $25/month for slower, weaker, detectable tools. Aura buries them all.

---

## 🎯 Core Capabilities at a Glance

### 👻 **Stealth Mode: The Undetectable Edge**

Aura's Stealth Mode is engineered to provide powerful AI assistance while remaining **completely invisible and undetectable** to proctoring software, screen recording tools, and human observers. This is crucial for high-stakes online exams, remote interviews, and any situation requiring discreet support.

**What it is:** Stealth Mode transforms Aura into a transparent, click-through overlay that seamlessly integrates with your workflow. It operates without creating new windows that could trigger alerts, and all interactions are managed via global hotkeys—meaning you **never need to switch focus** from your primary application.

**Core Components:**

| Component | What It Does |
|-----------|-------------|
| 🛡️ **Screen Capture Protection** | Invisible to screen recording, browser screen-share, Zoom, Teams, Google Meet, and GoToMeeting — uses low-level `WDA_EXCLUDEFROMCAPTURE` API |
| 🤫 **Silent Operation** | Zero system sounds, zero focus stealing — type in your exam while Aura overlays information |
| 🔒 **Taskbar & Alt+Tab Immunity** | Hidden from taskbar, Alt+Tab switcher, and application monitoring via `WS_EX_TOOLWINDOW` |
| 👻 **Ghost Mode** (`Alt+X`) | Click-through UI — interact with apps *underneath* Aura while seeing its content |
| ✨ **Focus-Free Control** | Show, hide, move, scroll — all via global hotkeys without ever clicking on Aura |
| 🚀 **Silent Launch** | `silent_run.vbs` starts Aura with zero visible terminal windows |

> 📖 **Full stealth guide:** [PROCTORING_STEALTH_GUIDE.md](PROCTORING_STEALTH_GUIDE.md)

---

### 👁️ **Revolutionary Vision AI (Enhanced by Stealth)**

When combined with Stealth Mode, Vision AI becomes even more potent:

- **Multi-Screenshot Queue** — Capture **up to 4 screenshots** with `Alt+S`, building a queue of problems. Process the entire batch at once with `Alt+P` — perfect for multi-part exam questions or complex code spanning multiple files
- **Auto Content-Type Detection** — Aura automatically identifies whether a screenshot contains code, a diagram, a math problem, a database schema, or plain text — and adapts its analysis strategy accordingly
- **Instant Problem Analysis** — Screenshot questions from any platform (LeetCode, HackerRank, CodeSignal, Google Docs, PDF exams), process them, get solutions overlaid invisibly
- **Multi-Language Code Solutions** — Python, Java, C++, JavaScript, TypeScript, SQL, Go, Rust, C#, and more — with syntax-highlighted answers
- **System Architecture Understanding** — Analyzes architecture diagrams, UML, flowcharts — suggests optimizations, identifies bottlenecks, recommends design patterns
- **Database Schema Analysis** — Understands ER diagrams, table relationships, generates optimal queries, suggests indexing strategies
- **Quantitative Problem Solving** — Breaks down complex math, probability, statistics, logic puzzles, and financial modeling problems step-by-step
- **Multiple Solution Approaches** — Every problem gets multiple approaches with time/space complexity analysis, trade-off comparisons, and interview presentation tips
- **Vision Model Cycling** — Switch between vision providers on the fly with `Alt+T` (e.g., Gemini for accuracy, Groq Llama 4 for speed)
- **Queue Management** — Clear your screenshot queue with `Alt+R` to start fresh between problems

**Best vision setup:** Use **Gemini** (free, excellent accuracy) as primary + **Groq Llama 4** (fastest) as backup. Switch between them with `Alt+T`.

---

### 🤖 **Multi-Provider AI Engine (Operates Seamlessly in Stealth)**

- **Primary + Secondary Models** — Run two different AIs simultaneously (e.g., Cerebras for speed + Groq for vision). All processing happens invisibly
- **Instant Model Switching** — `Alt+Q` (primary), `Alt+W` (secondary), `Alt+E` (auto-select fastest healthy provider) — swap AI strategies mid-interview without leaving your active window
- **Auto-Failover System** — If one provider hits rate limits, Aura auto-switches to the next key or provider. Zero downtime, zero manual intervention
- **API Key Rotation** — Add multiple free keys per provider via `apiKeys` array — Aura round-robins between them, multiplying your effective throughput
- **Multi-Provider Support** — Cerebras (fastest inference), Groq (fast + vision), Gemini (best vision accuracy), OpenRouter (gateway to 100+ models) — all free tiers
- **Health Monitoring** — Aura continuously monitors provider health and response times, auto-selecting the fastest available provider when you press `Alt+E`
- **Configurable Per-Session** — Choose different provider combinations for different interview types (e.g., Cerebras for behavioral, Gemini for system design with diagrams)

---

### 🎤 **Real-Time Voice Intelligence (Completely Stealthy)**

- **Live Transcription** — Deepgram-powered, high-accuracy speech-to-text with continuous streaming. Captures both interviewer questions and your responses in real-time
- **Context-Aware Coaching** — Aura knows your resume, job description, target role, and the full conversation history. Every response is hyper-personalized to *you* and the specific question being asked
- **Conversation Memory** — Remembers the entire interview (configurable up to 20 exchanges) for cross-referencing past questions, detecting follow-ups, and maintaining consistent narrative
- **Candidate Response Tracking** — Optionally tracks what you say so Aura can provide follow-up suggestions, catch mistakes, and help you build on previous answers
- **Smart Audio Controls** — `Alt+M` to toggle mic mute, `Alt+U` for universal pause/resume of all AI processing — all without touching the mouse
- **Auto-Reconnect** — If the Deepgram connection drops, Aura automatically reconnects and resumes transcription seamlessly
- **Full or Brief Answers** — Toggle between detailed, interview-ready responses and quick bullet-point hints via `GENERATE_FULL_ANSWERS` in `.env`

---

## 🏗️ Architecture

This diagram illustrates Aura's multi-layered architecture—designed for real-time performance, intelligence, and **unparalleled discretion through its Stealth Mode capabilities.**

<div align="center">

![Aura Operational Flow](flow.png)

</div>

*The "Stealth & Privacy" layer in the OS Interaction component is key to Aura's undetectable nature.*

### Key Components

| Component | Path | Role |
|-----------|------|------|
| **Entry point** | `main.py` | FastAPI + Uvicorn server, pywebview window, asyncio orchestration |
| **Window manager** | `window_manager.py` | Win32 stealth, global hotkeys, transparency, scrolling |
| **WebSocket API** | `api/websocket.py` | Real-time client ↔ server event streaming |
| **Config API** | `api/config_api.py` | REST endpoints for settings, providers, transparency |
| **Session manager** | `api/session_manager.py` | Interview lifecycle and state management |
| **LLM service** | `services/llm_service.py` | Multi-provider AI with key rotation, failover, health checks |
| **STT service** | `services/stt_service.py` | Deepgram real-time transcription with auto-reconnect |
| **Vision service** | `services/vision_service.py` | Screenshot analysis with auto content-type detection |
| **Context manager** | `services/context_manager.py` | Persistent profile, resume, JD, conversation history |
| **Prompts** | `core/prompts.py` | AI system prompts and expert coaching instructions |
| **Config** | `core/config.py` | Pydantic settings loaded from `.env` |
| **Frontend** | `web/` | Vanilla HTML/CSS/JS with WebSocket streaming and live UI |

---

## ⌨️ The Control Room: Global Hotkeys for Stealth Operations

Never leave the interview window. Control everything instantly with our ergonomic hotkey system, designed for maximum discretion and efficiency. **All hotkeys function seamlessly while Aura is in Stealth Mode.**

| Category | Hotkey | Action | Stealth Utility |
|:---|:---|:---|:---|
| **Stealth & Window** | `Alt + Shift + S` | **Activate Proctoring Stealth Mode** | The master key for full undetectability |
| | `Alt + Z` | Toggle window visibility | Show/hide Aura for your eyes only |
| | `Alt + X` | Toggle Ghost Mode (click-through) | Interact with apps underneath Aura |
| | `Alt + 1 / 2 / 3` | Set transparency (40% / 70% / 100%) | Adjust Aura's visibility to your comfort |
| **Window Movement** | `Alt + I` | Move window up | Position Aura's overlay precisely |
| | `Alt + J` | Move window down | Position Aura's overlay precisely |
| | `Alt + ←` | Move window left | Position Aura's overlay precisely |
| | `Alt + →` | Move window right | Position Aura's overlay precisely |
| **Content Scrolling** | `Alt + ↑` | Scroll up (hold for continuous) | Navigate AI suggestions within overlay |
| | `Alt + ↓` | Scroll down (hold for continuous) | Navigate AI suggestions within overlay |
| | `Home` | Jump to top (reading mode) | Quickly review earlier answers |
| | `End` | Jump to bottom (auto-scroll) | Return to latest AI response |
| | `Escape` | Toggle reading mode | Pause auto-scroll to study answers |
| **Vision AI** | `Alt + V` | Toggle Vision Mode | Enable screenshot capabilities in stealth |
| | `Alt + S` | Capture screenshot (up to 4) | Discreetly capture problems/diagrams |
| | `Alt + P` | Process screenshot queue | Get AI analysis overlaid invisibly |
| | `Alt + R` | Clear screenshot queue | Reset captured images |
| | `Alt + T` | Cycle vision model | Switch between Gemini/Groq vision |
| **AI & Audio** | `Alt + Q` | Switch to primary model | Fastest model on demand |
| | `Alt + W` | Switch to secondary model | Alternative AI personality |
| | `Alt + E` | Auto-select best model | Let Aura pick the fastest available |
| | `Alt + M` | Toggle microphone mute | Control your audio input |
| | `Alt + U` | Universal pause/resume AI | Instantly pause all AI processing |
| | `Alt + O` | Reset interview session | Start fresh |

*Complete control. Zero disruption. Maximum advantage. All under the cloak of Stealth Mode.*

> **💡 Scroll Speed** is configurable via `SCROLL_SPEED_PX` and `SCROLL_INTERVAL_MS` in your `.env` file. See [Configuration](#-configuration) for preset combos.

---

## 💻 System Requirements

| Requirement | Details |
|------------|---------|
| **Operating System** | **Windows 10 or 11** — fully supported on `master` (stealth features use Win32 APIs). <br>**macOS** — work-in-progress port on the [`macos`](https://github.com/Rkcr7/Aura-AI/tree/macos) branch (AppKit/pyobjc, some features still being ported). |
| **Python** | 3.8 or newer ([download here](https://www.python.org/downloads/)) — check **"Add Python to PATH"** during install |
| **Microphone** | Any mic — built-in laptop mic, headset, or USB mic all work |
| **Internet** | Required for API calls to Deepgram (STT) and LLM providers |
| **API Keys** | Deepgram + at least one LLM provider (all free — see below) |

---

## 🚀 Getting Started

### Step 1 · Clone & Install

```bash
git clone https://github.com/Rkcr7/Aura-AI
cd Aura-AI

click run.bat to auto install depedencies
OR
# Create & activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

### Step 2 · Get Your API Keys (All Free!)

You need **two types** of keys: one for speech-to-text (Deepgram) and one or more for AI models (Groq, Cerebras, Gemini). **All providers offer generous free tiers — no credit card required.**

> 📖 Full guide: [Obtaining API Keys](#-obtaining-api-keys-all-free)

### Step 3 · Configure Environment

The app **auto-creates `.env`** from `.env.example` on first launch. Just add your Deepgram key:

```bash
cp .env.example .env
```

```env
DEEPGRAM_API_KEY="your_deepgram_api_key_here"
```

### Step 4 · Configure AI Providers

```bash
cp ai_providers.example.json ai_providers.json
```

Open `ai_providers.json` and replace placeholder keys with your actual keys. You don't need all 4 providers — even a **single provider with one key works fine**.

### Step 5 · Launch Aura

**Option A — Direct launch:**
```bash
python main.py
```

**Option B — One-click automated launcher** (recommended):
```bash
run.bat
```
> `run.bat` automatically checks Python is installed, creates the virtual environment, installs/updates all dependencies, and launches the app — **all in one double-click**. No terminal commands needed.

**Option C — Silent/invisible launch** (maximum stealth):
```
silent_run.vbs
```
> Double-click `silent_run.vbs` to launch Aura with **zero visible terminal windows**. The entire startup process runs completely hidden — perfect for stealth situations.

### Step 6 · Onboarding

1. **Profile** — Enter your name, target company, role
2. **Resume** — Paste your full resume (unlimited length, no truncation)
3. **Job Description** — Paste the JD for tailored coaching
4. **AI Models** — Select primary and secondary LLM providers
5. **Vision** (optional) — Choose a vision model for screenshot analysis
6. **Start** — Hit "Start Interview" and you're live!

> **💡 Tip:** Click the **⚡ Demo** button on the profile tab to instantly fill the form with sample data for quick testing.

---

## 🔑 Obtaining API Keys (All Free!)

Every provider Aura supports offers **free tiers** that are more than enough for interview and exam use. No credit card required for any of them.

### 🎤 Deepgram (Required — Speech-to-Text Engine)

Deepgram is the **core engine** that powers Aura's real-time transcription. It listens to your microphone and the interviewer's audio, converting speech to text that gets fed to the AI for instant coaching responses. **Without Deepgram, Aura can't hear the interview.**

| | Details |
|---|---------|
| **Sign up** | [console.deepgram.com](https://console.deepgram.com/) |
| **Free tier** | **$200 in credits** — enough for ~100+ hours of transcription |
| **Why it's required** | Core STT engine — powers all voice intelligence features |

### ⚡ Cerebras (Recommended — Fastest Text AI)

Cerebras is the **fastest inference provider on the planet**. Responses come back almost instantly. Ideal as your primary model for text-based coaching.

| | Details |
|---|---------|
| **Sign up** | [cloud.cerebras.ai](https://cloud.cerebras.ai/) |
| **Free tier** | Free API access — **no credit card required** |
| **Best for** | Lightning-fast text responses (use as primary model) |
| **Top models** | `gpt-oss-120b` (fastest, default), `gemma-4-31b` |
| **Vision models** | `gemma-4-31b` — Cerebras now supports image input, and at ~1850 tok/s it is the fastest vision path available |

### 🚀 Groq (Recommended — Fast Text + Vision)

Groq provides **extremely fast inference** with both text and vision model support. Great as a secondary model or for Vision AI.

| | Details |
|---|---------|
| **Sign up** | [console.groq.com](https://console.groq.com/) |
| **Free tier** | Generous rate limits — **no credit card required** |
| **Best for** | Fast text + Vision AI (Llama 4 Scout/Maverick) |
| **Top models** | `openai/gpt-oss-120b`, `openai/gpt-oss-20b` (fastest) |
| **Vision models** | `qwen/qwen3.6-27b` — **paid tier only**, Groq retired its free vision models |

### 🔮 Gemini (Recommended — Best Vision AI)

Google's Gemini models deliver **excellent Vision AI accuracy**—best for analyzing screenshots of code, database schemas, and diagrams. Also strong for text.

| | Details |
|---|---------|
| **Sign up** | [aistudio.google.com](https://aistudio.google.com/) |
| **Free tier** | 15 requests/minute — **no credit card required** |
| **Best for** | Vision AI (screenshot analysis) with top-tier accuracy |
| **Vision models** | `gemini-3.6-flash` (most accurate), `gemini-3.5-flash-lite` (fastest), `gemini-3.5-flash` |

### 🌐 OpenRouter (Optional — Multi-Provider Gateway)

OpenRouter acts as a **gateway** to multiple providers through a single API key. Route specific models through preferred backends (e.g., Llama via Cerebras for speed).

| | Details |
|---|---------|
| **Sign up** | [openrouter.ai](https://openrouter.ai/) |
| **Free tier** | Many free models available |
| **Best for** | Unified access to multiple providers + custom routing |

### 💡 Why Use Multiple API Keys? (Free Reliability Hack)

Aura supports **multiple API keys per provider** via the `apiKeys` array in `ai_providers.json`:

```json
"apiKeys": ["KEY_1", "KEY_2", "KEY_3"]
```

**Why this is a game-changer:**

| Benefit | How It Works |
|---------|-------------|
| **Rate limit resilience** | Free tiers have per-key rate limits. Multiple keys = Aura rotates between them, multiplying your throughput |
| **Zero downtime** | If one key hits its limit, Aura auto-switches to the next — you never notice |
| **No cost** | All providers above offer free keys. Create 2–3 accounts, add all keys — instant reliability |
| **Auto-failover** | Aura also fails over between *providers* (Cerebras → Groq → Gemini), not just keys |

**A single key works perfectly fine** — multiple keys are optional but recommended for heavy use.

> **🏆 Recommended setup:** 2–3 free keys from **Cerebras** (primary, fastest) + 2–3 from **Groq** (secondary + vision) + 1 from **Gemini** (vision backup). **Total cost: $0. Reliability: bulletproof.**

---

## ⚙️ Configuration

### 📄 Environment Variables (`.env`)

The app **auto-creates** `.env` from `.env.example` on first run.

```env
# ─── API Keys ───
DEEPGRAM_API_KEY="your_key"              # Required — Deepgram speech-to-text

# ─── Logging ───
LOG_LEVEL=INFO                            # DEBUG, INFO, WARNING, ERROR

# ─── Development ───
DEV_MODE=false                            # Verbose logging & dev shortcuts

# ─── AI Behaviour ───
TRACK_CANDIDATE_RESPONSES=true            # Track what the candidate says
INCLUDE_CONVERSATION_HISTORY=true         # Send conversation history to AI
MAX_CONVERSATION_HISTORY=6                # Past exchanges to include (6–20)
GENERATE_FULL_ANSWERS=true                # Full answers vs. brief hints
PERSONALIZE_ANSWERS=true                  # Tailor to your resume/JD

# ─── Stealth / Proctoring ───
SCREEN_SHARE_SCAN_INTERVAL_S=1.0          # Seconds between indicator sweeps

# ─── Scroll Speed (Alt+Up/Down) ───
SCROLL_SPEED_PX=200                       # Pixels per tick
SCROLL_INTERVAL_MS=50                     # Ms between ticks
```

#### 📜 Scroll Speed Presets

Fine-tune how scrolling feels during a live interview:

| Feel | `SCROLL_SPEED_PX` | `SCROLL_INTERVAL_MS` |
|------|-------------------|----------------------|
| 🐢 Slow & precise | `100` | `80` |
| ⚡ Default | `200` | `50` |
| 🚀 Fast scanning | `400` | `30` |

### 🤖 AI Providers (`ai_providers.json`)

Created from `ai_providers.example.json`. **Not committed to git** — your keys stay private.

#### Pre-configured Providers

| Provider | Text Models | Vision Models | Speed |
|----------|------------|---------------|-------|
| **Cerebras** | GPT-OSS 120B, Gemma 4 31B | Gemma 4 31B | ⚡⚡⚡ Fastest (~3000 tok/s) |
| **Groq** | GPT-OSS 120B, GPT-OSS 20B | Qwen 3.6 27B (paid tier) | ⚡⚡ Very fast (~500-1000 tok/s) |
| **Gemini** | Gemini 3.1/3.5/3.6 Flash | All Gemini models | ⚡ Fast, best accuracy |
| **OpenRouter** | Routed to Cerebras/Groq | Gemma 4 31B via Cerebras | Varies |

> **Choosing a vision model:** `gemma-4-31b` on Cerebras is the default because
> speed matters most under exam pressure. If a screenshot is dense or ambiguous
> and you can spare a second, switch to `gemini-3.6-flash` with `Alt+T` for the
> most accurate reading.

#### Provider Schema

```jsonc
{
  "name": "ProviderName",
  "baseURL": "https://api.provider.com/openai/v1",
  "apiKey": "YOUR_KEY",                    // Single key (minimum)
  "apiKeys": ["KEY_1", "KEY_2", "KEY_3"],  // Multiple keys for rotation
  "models": ["model-a", "model-b"],
  "visionModels": ["vision-model-a"],
  "supportsVision": true,
  "defaultModel": "model-a"
}
```

---

## 💎 Who Rules with Aura?

### **For Job Seekers (Using Stealth Mode for an Edge)**

- **Junior Developers** — Compete with senior-level confidence with discreet access to best practices
- **Career Changers** — Navigate technical interviews in new domains with stealthy guidance
- **Experienced Engineers** — Excel in high-pressure FAANG interviews with an invisible partner for system design and algorithms
- **International Candidates** — Overcome language barriers with real-time phrasing suggestions, delivered discreetly
- **Students** — Ace aptitude tests and certifications using Vision AI in Stealth Mode

### **For Exam Takers (Where Stealth Mode is Essential)**

- **Quantitative Analysts** — Master complex math with on-screen, invisible formula assistance
- **Professional Certifications** — Navigate difficult cert exams with key information and strategies, undetectable
- **Aptitude Tests** — Crush pre-employment assessments by leveraging Vision AI to analyze diverse question types

**Free. Fast. Flawless. And Fully Stealthy.**

---

## 🔧 Troubleshooting

<details>
<summary><b>🎤 Microphone not working</b></summary>

1. Check Windows privacy: **Settings → Privacy → Microphone → Allow apps**
2. Verify `DEEPGRAM_API_KEY` in `.env` is correct
3. Close other apps with mic access (Zoom, Teams, etc.)
4. In dev mode (`DEV_MODE=true`), check browser console (F12) for errors
</details>

<details>
<summary><b>🤖 AI responses failing or slow</b></summary>

1. Verify API keys in `ai_providers.json` aren't placeholders
2. Press `Alt + E` to auto-select best available model
3. Add more API keys to `apiKeys` array — you may be hitting rate limits
4. Check terminal for error messages
5. App auto-fails over to secondary model — if both fail, check internet
</details>

<details>
<summary><b>👁️ Vision AI not working</b></summary>

1. Ensure a vision-capable provider is configured (Gemini or Groq with Llama 4)
2. Enter vision mode (`Alt + V`) *before* capturing (`Alt + S`)
3. Process the queue (`Alt + P`) after capturing
4. Check `supportsVision: true` in your provider config
</details>

<details>
<summary><b>🖥️ Window not visible</b></summary>

1. Press `Alt + Z` to toggle visibility
2. Press `Alt + 3` for 100% opacity (may be transparent)
3. Some fullscreen apps override always-on-top — try windowed mode
4. Re-enable stealth with `Alt + Shift + S`
</details>

<details>
<summary><b>📜 Scrolling too fast or slow</b></summary>

Adjust in `.env` and restart:
```env
SCROLL_SPEED_PX=150      # Lower = slower
SCROLL_INTERVAL_MS=70    # Higher = less frequent
```
</details>

<details>
<summary><b>🔧 App won't start</b></summary>

1. Use `run.bat` — it handles venv and deps automatically
2. Verify Python 3.8+ is installed and in PATH
3. Recreate venv: `rmdir /s venv` then `python -m venv venv`
4. Run `pip install -r requirements.txt` manually
</details>

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Runtime** | Python 3.8+, asyncio |
| **Web framework** | FastAPI + Uvicorn |
| **Desktop shell** | pywebview (WinForms backend) |
| **Speech-to-text** | Deepgram SDK v3 |
| **LLM clients** | OpenAI-compatible SDK (Groq, Cerebras, Gemini, OpenRouter) |
| **Global hotkeys** | pynput |
| **Win32 integration** | ctypes — capture protection, transparency, window management |
| **Frontend** | Vanilla HTML/CSS/JS with WebSocket streaming |
| **Config** | pydantic-settings + python-dotenv |

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [PROCTORING_STEALTH_GUIDE.md](PROCTORING_STEALTH_GUIDE.md) | Complete stealth mode guide — proctoring countermeasures, screen capture protection, and detection avoidance in detail |

---

## 💰 Own It Forever

### 🎁 **Free and Open-Source**
- No recurring fees or subscriptions for **any** feature, including advanced Stealth Mode
- Full access to all features — no premium tiers, no paywalls
- Your data stays on **your** machine — zero telemetry, zero tracking

### 🔑 **Bring Your Own AI**
- **OpenAI-compatible** — works with any provider using the standard API format
- **Multiple providers** — mix and match Cerebras, Groq, Gemini, OpenRouter
- **Cost control** — pay only for what you use, directly to providers (or use free tiers forever)
- **No middleman** — direct API access at provider rates

---

## ⚖️ Fair Play, Big Wins

Aura's Stealth Mode is a powerful tool. It's designed to level the playing field and provide support—not to encourage dishonesty or misrepresentation.

### 🚨 **Important Legal Notice**

**BY USING AURA, INCLUDING ITS STEALTH MODE FEATURES, YOU ACKNOWLEDGE AND AGREE:**

### 📋 **User Responsibility**
- **Full Responsibility**: Users are solely responsible for compliance with all applicable laws, regulations, company policies, and exam guidelines when using Stealth Mode
- **Policy Review Required**: Review your target company's interview policies or exam rules *before* using Aura
- **Legal Compliance**: Comply with all local, state, federal, and international laws regarding privacy, recording, and technology use
- **Professional Ethics**: Stealth Mode augments your abilities and confidence — it shouldn't misrepresent your fundamental skills

### ⚠️ **Risks & Limitations**
- **Policy Violations**: Using Stealth Mode in violation of policies may result in disqualification, offer withdrawal, or legal consequences
- **No Guarantees**: Aura does not guarantee success, job offers, or career advancement
- **Technical Reliability**: Issues may occur — don't solely rely on Aura without backup plans
- **AI Limitations**: Validate AI responses — don't blindly rely on them

### 🎯 **Ethical Use**
- **Enhancement, Not Deception**: Use Aura to enhance your knowledge and confidence — not to fake competence
- **Learning Tool**: Treat Aura as an advanced study and performance aid
- **Honest Representation**: Maintain honesty about your capabilities
- **Respect the Process**: Respect the integrity of interviews and exams

---

### 🤝 **Agreement**

By downloading, installing, or using Aura, you acknowledge that you have read, understood, and agree to comply with all terms and guidelines above.

---

## 🤝 Contributing

```bash
git clone https://github.com/Rkcr7/Aura-AI
cd Aura-AI
Click run.bat to auto install dependecies
OR
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env && cp ai_providers.example.json ai_providers.json
# Add your API keys, then:
python main.py
```

- **🐛 Bugs** — Open an issue with steps to reproduce + terminal output
- **💡 Features** — Describe the use case and expected behavior
- **🔧 PRs** — Fork → branch → commit → pull request

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<div align="center">

<img src="logo.png" alt="Aura AI" width="100" />

### 🏆 **Aura: Victory Is Yours**

**Grab Aura. Crush it. Today.**

[⬆ Back to Top](#-aura-your-ultimate-ally-for-interviews-and-examsbuilt-in-48-hours-free-forever)

</div>
