# Deployment — Family Stories

Stack:

```
Vercel (frontend, free)
  │  HTTPS 443
  ▼
Render web service (FastAPI backend, free)
  │  TCP 6543
  ▼
Supabase (Postgres + Storage + Auth)
```

The Render data centre has no eduroam firewall, so the Supabase
connection that fails on your laptop will work fine in cloud.

---

## 0. Prerequisites

* GitHub account with this repo pushed
* Vercel account (sign in with GitHub)
* Render account (sign in with GitHub)
* Supabase project already set up (you already have it)

---

## 1. Push the repo

```bash
cd /home/diogo05/family-stories
git add .
git commit -m "deploy: render + vercel config"
git push origin main
```

Confirm `.env` is **not** committed (it should be in `.gitignore`).

---

## 2. Backend — Render

1. Render dashboard → **New → Blueprint**.
2. Pick your `family-stories` repo. Render reads [render.yaml](render.yaml) and
   shows a confirmation screen.
3. Fill in the secret environment variables (Render asks you for each
   one marked `sync: false` in the YAML):

   | Variable                       | Value                                                                                       |
   | ------------------------------ | ------------------------------------------------------------------------------------------- |
   | `SUPABASE_URL`                 | `https://tzkpstjrufevqllunvzu.supabase.co`                                                  |
   | `SUPABASE_ANON_KEY`            | `sb_publishable_FHTvANgQ56OwQphfr8J1rA_bxrxPmZN`                                            |
   | `SUPABASE_SERVICE_ROLE_KEY`    | (the `sb_secret_...` key — keep it private)                                                 |
   | `SUPABASE_DB_URL`              | `postgresql://postgres.tzkp...:memoria_viva13@aws-0-eu-west-1.pooler.supabase.com:6543/...` |
   | `SUPABASE_DB_DIRECT_URL`       | the direct connection variant (same password)                                               |
   | `GEMINI_API_KEY`               | your Google AI Studio key                                                                   |
   | `CORS_ORIGINS`                 | `https://your-app.vercel.app` *(fill in after step 3)*                                      |

4. Click **Apply**. The build takes ~3 minutes. When it finishes you'll
   see a URL like `https://family-stories-backend.onrender.com`.
5. Hit `https://family-stories-backend.onrender.com/healthz` in a browser —
   should return `{"status":"ok"}`.

> ⚠️ Free tier sleeps after 15 min idle. First request after sleep takes
> ~30 s while it warms up. For demo days, hit `/healthz` 1 min before
> the demo to wake it.

---

## 3. Frontend — Vercel

1. Vercel dashboard → **Add New → Project** → pick the same repo.
2. Configure project:
   * Framework Preset: **Vite**
   * Root directory: **frontend**
   * Build command: `npm run build` (auto-detected)
   * Output directory: `dist` (auto-detected)
3. Environment variables (Project → Settings → Environment Variables):

   | Variable                | Value                                                              |
   | ----------------------- | ------------------------------------------------------------------ |
   | `VITE_SUPABASE_URL`     | `https://tzkpstjrufevqllunvzu.supabase.co`                         |
   | `VITE_SUPABASE_ANON_KEY`| `sb_publishable_FHTvANgQ56OwQphfr8J1rA_bxrxPmZN`                   |
   | `VITE_API_BASE_URL`     | the Render URL from step 2 (e.g. `https://family-stories-backend.onrender.com`) |

4. Hit **Deploy**. After ~1 min you get `https://family-stories-xxx.vercel.app`.

---

## 4. Wire the CORS loop

1. Copy the Vercel URL.
2. Render dashboard → your backend service → **Environment** → edit
   `CORS_ORIGINS` to:
   ```
   https://family-stories-xxx.vercel.app
   ```
3. Render redeploys automatically (~2 min). When it finishes, open the
   Vercel URL in your browser, sign up / log in — should just work.

---

## 5. Supabase Auth redirect URLs

If you set up password reset, the email link points to
`window.location.origin/reset-password`. For that to land on the live
site instead of `localhost`:

1. Supabase dashboard → **Authentication → URL Configuration**.
2. **Site URL**: `https://family-stories-xxx.vercel.app`.
3. **Redirect URLs**: add both `https://family-stories-xxx.vercel.app/**`
   and `http://localhost:5173/**` (so local dev still works).

---

## 6. Smoke test

From any network — eduroam, mobile data, anywhere:

1. `https://family-stories-xxx.vercel.app` opens the landing.
2. Sign up with a fresh email. Should land on the dashboard.
3. Upload a photo. Should appear in the Library.
4. Generate a narrative (mode auto-downgrades to **sync** since no
   Celery worker is deployed). 30–60 s wait, then the story shows up.

---

## 7. Notes & limits

* **First request after sleep** on Render free tier: ~30 s. To stay
  awake, ping `/healthz` from a free uptime monitor every 10 min
  (Uptime Robot, BetterStack, etc.) — but only do that if you really
  need 24/7 availability; the free tier has 750 hours/mo total.
* **Logs**: Render dashboard shows live tail. Supabase dashboard shows
  Postgres + Storage logs.
* **Local dev still works**: `~/family-stories/start.sh` keeps running
  exactly as before on the laptop. Local Vite picks up `.env`, deployed
  Vite picks up Vercel's env vars — never a conflict.
* **Costs**: the whole thing runs 0€/month at this size. If you need
  more, the next jumps are:
  * Render Starter (7$/mo, no sleep) for the backend.
  * Add a `worker` service in [render.yaml](render.yaml) for Celery if
    you ever want true background processing (7$/mo extra).
  * Supabase free tier is fine until ~500 MB of database storage.
