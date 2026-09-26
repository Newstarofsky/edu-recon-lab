# edu-recon-lab

An educational prototype that reproduces the **core mechanism** of three
recon / social-engineering tools inside a single Flask app, for a supervised
cybersecurity lab **on systems you own**.

| Module | Real tool it models | Technique demonstrated |
|--------|--------------------|------------------------|
| `/geo`    | **Seeker**    | `navigator.geolocation.getCurrentPosition` + passive device fingerprinting |
| `/cam`    | **CamHacker** | `navigator.mediaDevices.getUserMedia` + `<canvas>` frame export |
| `/portal` | **Zphisher**  | Look-alike login form → server-side credential logger |
| `/dashboard` | (operator view) | Shows exactly what each technique leaked |

## Security / architecture review

**Data flow — everything stays local (no external egress):**

```
   Browser (victim/tester)
        │  POST JSON / form
        ▼
   Flask app  @ 127.0.0.1:5000        <-- the only server involved
        │  writes
        ▼
   Local storage:  lab.db (sqlite)  +  ./captures/*.png
        │  reads
        ▼
   /dashboard  (operator view, same host)
```

- **Endpoints are all first-party.** Each module POSTs to the app's own routes —
  `/api/geo`, `/api/cam`, `/api/portal` — and results are written to `lab.db`
  and `./captures/`. No module sends data to any third party.
- **No tunneling wired in.** The names `*.trycloudflare.com`, `*.ngrok-free.app`,
  `*.loclx.io`, `*.serveo.net` appear only as *text* in the README and the
  blue-team page (`detect.html`) — they are listed as **detection signals**, not
  used. No code imports or connects to any tunnel service.
- **Only one outbound link, user-initiated.** The dashboard renders an
  OpenStreetMap URL for a captured coordinate; it opens only if *you* click it.
  Nothing is fetched automatically.
- **Bind scope is explicit.** Defaults to `127.0.0.1` (local only). LAN exposure
  requires deliberately setting `LAB_HOST=0.0.0.0`, intended for isolated
  lab VMs you own.
- **Captured data is git-ignored.** `.gitignore` excludes `lab.db` and
  `captures/`, so lab results never end up in the repo.

**Residual risk (the point of the lab):** the danger is not in the plumbing —
it is that the *techniques themselves work*. A look-alike form plus a logger
really does capture a password; a consented `getUserMedia` call really does
return a camera frame. The lab keeps that mechanism intact for study while
stripping the covert delivery (no tunnels, consent banners on every page, and a
"this was a simulation" ending on the credential flow).

## Why this is a *demo*, not a weapon

Real versions of these tools are dangerous because they are **covert** and
**deceptive**. This prototype deliberately keeps the mechanism but removes the
weaponization — and the gap between the two is the most important thing to
write up:

| Real tool does | This lab does instead | Lesson |
|----------------|----------------------|--------|
| Hides that capture is happening | Unavoidable consent banner on every page | Awareness is the primary defence |
| Auto-exposes via ngrok/cloudflared tunnel | Binds to `127.0.0.1` only | Ephemeral tunnel domains are a detection signal |
| Clones a real brand's login | Fictional "ACME" portal | Brand impersonation is itself the crime |
| Silently redirects victim to real site | Ends on a "this was a simulation" screen | The silence is the trick |

## Run on Kali Linux (primary target)

```bash
cd edu-recon-lab
sudo apt update && sudo apt install -y python3-venv   # one-time, if needed
chmod +x run.sh
./run.sh
```

`run.sh` creates a venv, installs deps, and starts the app on
<http://127.0.0.1:5000> (dashboard at `/dashboard`, blue-team module at
`/detect`).

### Testing across your own lab VMs

To reach the app from another **VM you own** on an isolated lab network
(the standard attacker-VM → victim-VM setup):

```bash
LAB_HOST=0.0.0.0 ./run.sh
```

Then browse to `http://<kali-lab-ip>:5000` from the other VM. Do this **only**
on a private lab segment with machines you control. `LAB_PORT` overrides the port.

> Camera/geolocation APIs require a secure context. `localhost`/`127.0.0.1`
> qualifies. Over a LAN IP, browsers may require HTTPS — for a lab, add a
> self-signed cert (`app.run(..., ssl_context="adhoc")` with `pyopenssl`) or
> test those two modules from the Kali box itself via `127.0.0.1`.

## Run on Windows

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Test the modules in your own browser, then open the dashboard to inspect the
captured footprint. Data lives in `lab.db` and `./captures/` — delete them to reset.

> **Note on the camera/geolocation modules:** browsers only expose these APIs
> on `https://` or `http://localhost`. `127.0.0.1` counts as a secure context,
> so the prompts work locally without a TLS cert.

## How each mechanism works (for the writeup)

**Geolocation (Seeker).** Two data classes: (1) *passive* signals readable with
zero permission — `navigator.platform`, `screen`, `language`,
`hardwareConcurrency`, and the server-visible IP; (2) *consent-gated* precise
GPS coordinates that require the user to click "Allow". No exploit is involved —
the accuracy comes entirely from user consent.

**Webcam (CamHacker).** `getUserMedia({video:true})` triggers the browser's
camera prompt. On approval, one video frame is drawn to a hidden `<canvas>`,
exported with `toDataURL()`, and POSTed as base64. The browser's active-camera
indicator is the defensive tell.

**Credentials (Zphisher).** A form that visually resembles a login and whose
`action` points at a logging endpoint. The endpoint records the fields; a real
attacker would then redirect to the genuine site. The defence is entirely
client-side vigilance: URL inspection, password managers (which key on domain),
and 2FA.

## Detection & defence (blue-team section)

- **Network:** flag look-alike pages served from `*.trycloudflare.com`,
  `*.ngrok-free.app`, `*.loclx.io`, `*.serveo.net`.
- **Browser policy:** audit/limit `camera` and `geolocation` Permissions-Policy;
  train users to read permission prompts and the camera indicator.
- **Identity:** enforce phishing-resistant 2FA (FIDO2/passkeys) so captured
  passwords are insufficient.
- **Email/web:** brand-impersonation and new-domain heuristics catch the
  credential-phishing stage.

## Scope / ethics

For authorized education only, on systems and accounts you own or have written
permission to test. Do not deploy against anyone without informed consent —
covert location/camera capture and credential theft are illegal under
computer-crime and privacy law (incl. Thailand's Computer Crime Act & PDPA).
