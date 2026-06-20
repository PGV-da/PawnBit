# PawnBit

A bot for Chess.com and Lichess.org that automatically plays chess for you.

---

## Installation

1. Clone or download this repository as a `.zip`

2. Download **Stockfish** from https://stockfishchess.org/
   > On Linux you must add execute permissions: `chmod +x stockfish`

3. Open a terminal in the `PawnBit` folder

4. Create a virtual environment:
   - Windows: `python -m venv venv`
   - Linux: `python3 -m venv venv`

5. Install dependencies:
   - Windows: `venv\Scripts\pip.exe install -r requirements.txt`
   - Linux: `venv/bin/pip3 install -r requirements.txt`

---

## Connecting PawnBit to Your Browser

PawnBit attaches to your **already-running** browser using Chrome's remote debugging protocol.  
You must launch your browser with a special flag **before** starting PawnBit.

### Step 1 — Close your browser completely

Make sure Chrome, Edge, or Brave is fully closed before continuing.

### Step 2 — Launch your browser with remote debugging enabled

Open a terminal and run the command for your browser:

**Chrome (Windows)**
```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**Chrome (Linux)**
```
google-chrome --remote-debugging-port=9222
```

**Microsoft Edge (Windows)**
```
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222
```

**Brave (Windows)**
```
"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222
```

> **Tip:** You only need to do this once per session. Create a desktop shortcut with the flag so you don't have to type it every time (see below).

### Step 3 — Open the chess site

In the browser you just opened, navigate to:
- **Chess.com** → https://www.chess.com
- **Lichess.org** → https://lichess.org

Then go to a **live game** (vs a human, a bot, or puzzles).

### Step 4 — Start PawnBit

Open a terminal in the `PawnBit` folder and run:

- Windows: `venv\Scripts\python.exe src\gui.py`
- Linux: `venv/bin/python3 src/gui.py`

In the GUI:
1. Select your **website** (Chess.com or Lichess.org)
2. Select your **browser** (Chrome, Edge, or Brave)
3. Click **Select Stockfish** and navigate to the Stockfish executable
4. Click **Start** (or press **1**)

PawnBit will automatically detect your open browser, switch to the chess tab, and begin playing.

> **Note:** You can stop the bot at any time by clicking **Stop** or pressing **2**.

---

## Creating a Browser Shortcut with Remote Debugging (Windows)

To avoid typing the command every time:

1. Right-click your browser's desktop shortcut → **Properties**
2. In the **Target** field, append ` --remote-debugging-port=9222` at the end  
   Example:
   ```
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
   ```
3. Click **OK**

Now every time you open Chrome via that shortcut, remote debugging will be enabled automatically.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| *Browser Not Detected* | Browser wasn't launched with `--remote-debugging-port=9222` | Close browser fully and relaunch with the flag |
| *Site Not Open* | The selected chess site isn't open in any tab | Navigate to the site in the browser, then click Start again |
| *Attach Failed / ChromeDriver version mismatch* | Outdated ChromeDriver on your system | PawnBit uses `webdriver-manager` to auto-fix this — try again; it will download the correct driver |
| *Can't find board* | You're not on a game page | Make sure you're on an active game or puzzle page before clicking Start |
| *Can't find player color* | Board loaded but the orientation wasn't detected | Refresh the page and click Start again |

---

## Features

- **Platforms:** Windows / Linux
- **Sites:** Chess.com · Lichess.org
- **Play modes:** vs humans · vs bots · Puzzles
- **Manual Mode** — press or hold `3` to trigger the next move; best move shown as an arrow
- **Mouseless Mode** — moves are sent directly to the site (no mouse movement required)
  - ✅ Lichess.org · ❌ Chess.com
- **Non-stop Mode** — bot plays game after game automatically
  - ✅ Lichess.org · ❌ Chess.com
- **Bongcloud Mode** ( ͡° ͜ʖ ͡° )
- **Skill Level** — 0 to 20
- **Depth** — 1 to 20
- **Slow Mover** — 10 to 1000 (lower = faster moves)
- **Memory & CPU threads** control
- **Mouse latency** — add artificial delay before moving
- **Evaluation bar** — live display next to the board
- **WDL / Accuracy / Material** tracking
- **Export to PGN**

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` | Start |
| `2` | Stop |
| `3` | Make move (Manual Mode only) |

---

## Disclaimer

This project is for **educational purposes only**.  
Do not use this bot to cheat in online games or tournaments — it is against the Terms of Service of Chess.com and Lichess.org and may result in a permanent ban.
