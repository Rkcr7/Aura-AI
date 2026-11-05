"""The startup splash the Aura window shows while the server boots.

WebView2 can paint this the moment it is ready, because it is inline HTML with
no network or server requests (the logo is embedded). main.py then swaps in the
real UI as soon as the server answers. The colours and wordmark match the
onboarding screen (--bg-primary and .brand-logo in web/css/main.css), so the
swap is seamless.
"""
import base64
from pathlib import Path

# --bg-primary in web/css/main.css. Also the native window colour, so nothing
# flashes white before WebView2 paints its first frame.
WINDOW_BACKGROUND = "#08080F"

LOGO_PATH = Path(__file__).resolve().parent.parent / "web" / "img" / "aura-logo.png"


def _logo_markup() -> str:
    """The logo as an inline image, or nothing if the file is missing."""
    try:
        data = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    except OSError:
        return ""  # the splash still works, just without the mark
    return (
        '<div class="mark-wrap">'
        f'<img class="mark" alt="" src="data:image/png;base64,{data}">'
        "</div>"
    )


_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Aura AI</title>
<style>
  html, body { margin: 0; height: 100%; overflow: hidden; color-scheme: dark; }
  body {
    display: grid;
    place-items: center;
    background: __BACKGROUND__;
    background-image:
      radial-gradient(ellipse at 20% 0%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 100%, rgba(139, 92, 246, 0.06) 0%, transparent 50%);
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    user-select: none;
  }
  /* Fades in after a beat, so a fast start goes straight to the app without a flash */
  .splash {
    display: flex;
    flex-direction: column;
    align-items: center;
    opacity: 0;
    animation: appear 0.35s ease-out 0.15s forwards;
  }
  .mark-wrap {
    position: relative;
    width: 116px;
    height: 116px;
    margin-bottom: 18px;
  }
  .mark-wrap::before {
    content: "";
    position: absolute;
    inset: -30px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.30) 0%, rgba(45, 212, 191, 0.08) 45%, transparent 70%);
    animation: glow 2.8s ease-in-out infinite;
  }
  .mark {
    position: relative;
    width: 100%;
    height: 100%;
    animation: float 2.8s ease-in-out infinite;
  }
  .logo {
    font-size: 28px;
    font-weight: 800;
    letter-spacing: 0.18em;
    padding-left: 0.18em; /* letter-spacing trails the last letter; keep it centred */
    line-height: 1.2;
    background: linear-gradient(110deg, #6366f1 0%, #a78bfa 35%, #e0dbff 50%, #a78bfa 65%, #818cf8 100%);
    background-size: 250% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmer 2.8s ease-in-out infinite;
  }
  .tagline {
    margin-top: 4px;
    padding-left: 0.18em;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: rgba(229, 229, 240, 0.5);
  }
  .track {
    position: relative;
    width: 148px;
    height: 2px;
    margin-top: 24px;
    border-radius: 2px;
    overflow: hidden;
    background: rgba(129, 140, 248, 0.14);
  }
  .track::after {
    content: "";
    position: absolute;
    inset: 0;
    width: 40%;
    border-radius: inherit;
    background: linear-gradient(90deg, transparent, #a78bfa, #2dd4bf, transparent);
    animation: sweep 1.25s ease-in-out infinite;
  }
  .status {
    max-width: 340px;
    margin-top: 20px;
    font-size: 13px;
    line-height: 1.5;
    text-align: center;
    color: #fca5a5;
  }
  /* Set by showStartupError(): stop the "loading" motion, show the message */
  .failed .logo, .failed .mark, .failed .mark-wrap::before { animation: none; }
  .failed .track { visibility: hidden; }
  @keyframes appear { to { opacity: 1; } }
  @keyframes glow {
    0%, 100% { opacity: 0.55; transform: scale(0.94); }
    50% { opacity: 1; transform: scale(1.04); }
  }
  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-4px); }
  }
  @keyframes shimmer {
    0%, 100% { background-position: 100% 0; }
    50% { background-position: 0% 0; }
  }
  @keyframes sweep {
    from { transform: translateX(-100%); }
    to { transform: translateX(250%); }
  }
  @media (prefers-reduced-motion: reduce) {
    .mark, .mark-wrap::before, .logo, .track::after { animation: none; }
    .splash { animation-duration: 0.01s; }
  }
</style>
</head>
<body>
  <div class="splash" role="status" aria-label="Starting Aura AI">
    __LOGO__
    <div class="logo">AURA AI</div>
    <div class="tagline">AI Interview Coach</div>
    <div class="track"></div>
    <div class="status" id="status" hidden></div>
  </div>
  <script>
    // main.py calls this when the local server can't start, so the window
    // says so instead of spinning forever (and the terminal may be hidden)
    window.showStartupError = function () {
      document.body.classList.add('failed');
      var status = document.getElementById('status');
      status.textContent = "Aura couldn't start. The terminal shows why (launch with run.bat to see it).";
      status.hidden = false;
    };
  </script>
</body>
</html>
"""

SPLASH_HTML = _TEMPLATE.replace("__BACKGROUND__", WINDOW_BACKGROUND).replace("__LOGO__", _logo_markup())
