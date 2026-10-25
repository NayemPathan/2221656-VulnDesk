# VulnDesk — Phase 5.1: Verify Clean TypeScript & Vite Production Build (`bash.md`)

## 1. Terminal 1 — Start the FastAPI Backend Server (`:8000`)
### Using Git Bash / Bash
```bash
cd /e/2221656-VulnDesk/backend
source .venv/Scripts/activate
uvicorn app.main:app --reload --port 8000
```

### Using Windows PowerShell
```powershell
cd E:\2221656-VulnDesk\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

---

## 2. Terminal 2 — Step 5.1: Verify Clean TypeScript & Vite Production Build (`:5173`)
Open a **second terminal** while Terminal 1 keeps running `uvicorn` on port `8000`.

### Using Git Bash / Bash
```bash
# 1. Navigate to the frontend folder
cd /e/2221656-VulnDesk/frontend

# 2. Run TypeScript typechecking (tsc) + Vite production bundle (vite build)
npm run build

# 3. Verify that the production bundle was created in dist/
ls -la dist/

# 4. Start the local Vite development server on http://localhost:5173
npm run dev
```

### Using Windows PowerShell
```powershell
# 1. Navigate to the frontend folder
cd E:\2221656-VulnDesk\frontend

# 2. Run TypeScript typechecking (tsc) + Vite production bundle (vite build)
npm run build

# 3. Verify that the production bundle was created in dist/
dir dist

# 4. Start the local Vite development server on http://localhost:5173
npm run dev
```

### Expected Output from `npm run build`
```text
> vulndesk-frontend@0.1.0 build
> tsc && vite build

vite v5.4.x building for production...
✓ 44 modules transformed.
dist/index.html                   0.42 kB │ gzip:  0.28 kB
dist/assets/index-XXXXXXXX.css    8.12 kB │ gzip:  2.14 kB
dist/assets/index-XXXXXXXX.js   178.45 kB │ gzip: 56.30 kB
✓ built in ~2.5s
```

---

## 3. Optional Check — Verify `api/index.py` Serverless Entrypoint from Repo Root

Before pushing to GitHub/Vercel, you can also run this 1-line check from the repository root to confirm `api/index.py` loads your FastAPI `app` without errors:

### Using Git Bash / Bash
```bash
cd /e/2221656-VulnDesk
./backend/.venv/Scripts/python.exe -c "import api.index; print('Loaded FastAPI app:', api.index.app.title)"
```

### Using Windows PowerShell
```powershell
cd E:\2221656-VulnDesk
.\backend\.venv\Scripts\python.exe -c "import api.index; print('Loaded FastAPI app:', api.index.app.title)"
```
