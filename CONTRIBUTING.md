# 🤝 Contributing to Aura

First off — **thank you** for wanting to contribute! Every bug report, feature idea, and pull request makes Aura better for everyone.

---

## 🚀 Quick Start

```bash
# 1. Fork & clone
git clone https://github.com/YOUR_USERNAME/aura.git
cd aura

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy config templates
cp .env.example .env
cp ai_providers.example.json ai_providers.json

# 5. Add your API keys to .env and ai_providers.json

# 6. Run
python main.py
```

---

## 📋 How to Contribute

### 🐛 Found a Bug?

1. **Search existing issues** first to avoid duplicates
2. Open a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Terminal/console output (if applicable)
   - Your OS version and Python version

### 💡 Have a Feature Idea?

1. Open an issue with the **`feature request`** label
2. Describe:
   - The use case — what problem does it solve?
   - Your proposed solution
   - Any alternatives you've considered

### 🔧 Want to Submit a PR?

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** — keep commits focused and atomic
4. **Test** your changes locally. For changes to the web UI's markdown or math rendering, run the JS tests (needs Node 20+):
   ```bash
   npm install
   npm test
   ```
5. **Push** and open a Pull Request:
   ```bash
   git push origin feature/your-feature-name
   ```

---

## 📁 Project Structure

```
aura/
├── main.py                 # App entry point — FastAPI server + pywebview
├── window_manager.py       # Stealth mode, hotkeys, Win32 API integration
├── api/                    # FastAPI route handlers
├── core/                   # Core business logic and config
├── services/               # AI providers, Deepgram, vision processing
├── web/                    # Frontend — HTML/CSS/JS served by pywebview
├── .env                    # Environment variables (secrets — not committed)
├── ai_providers.json       # AI provider config (secrets — not committed)
├── run.bat                 # Automated setup & launch script
└── silent_run.vbs          # Invisible launch (no terminal window)
```

---

## 🎯 Areas We Need Help With

| Area | Description |
|:-----|:------------|
| 🐧 **Linux Support** | Port Win32 stealth APIs to X11/Wayland equivalents |
| 🍎 **macOS Support** | Port Win32 stealth APIs to Cocoa/AppKit |
| 🌐 **More AI Providers** | Add support for new LLM providers (Anthropic, Mistral, etc.) |
| 🎨 **UI/UX** | Improve the overlay interface, themes, animations |
| 📝 **Documentation** | Better setup guides, tutorials, video walkthroughs |
| 🧪 **Testing** | Unit tests, integration tests, CI/CD pipeline |
| 🌍 **Localization** | Multi-language support for the UI |

---

## 📐 Code Style

- **Python**: Follow PEP 8 conventions
- **JavaScript**: Use vanilla JS (no frameworks in the frontend)
- **CSS**: Vanilla CSS — no Tailwind or preprocessors
- **Naming**: Descriptive variable/function names, snake_case for Python, camelCase for JS
- **Comments**: Explain *why*, not *what* — code should be self-documenting

---

## ⚠️ Important Notes

- **Never commit secrets** — `.env` and `ai_providers.json` are in `.gitignore` for a reason
- **Test stealth features** on Windows 10/11 before submitting stealth-related PRs
- **Keep PRs focused** — one feature or fix per PR
- **Be respectful** — we're all here to build something awesome

---

## 💬 Questions?

Open a GitHub issue or start a Discussion — we're happy to help!

---

**⭐ Star the repo if you find Aura useful — it helps more people discover it!**
