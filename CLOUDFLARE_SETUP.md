# Cloudflare Tunnel Setup for veloxify.dev/ai

To expose your local AI safely without opening router ports, follow these steps to set up **Cloudflare Tunnel (`cloudflared`)**.

## 1. Install Cloudflared
1.  Download the `cloudflared` installer for Windows: [Cloudflared Download](https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.msi).
2.  Install it on your PC.

## 2. Authenticate
Open PowerShell and run:
```powershell
cloudflared tunnel login
```
A browser window will open. Select your domain (`veloxify.dev`) and authorize.

## 3. Create a Tunnel
Run:
```powershell
cloudflared tunnel create local-ai
```
Note the **Tunnel ID** (a long string of characters).

## 4. Map the Tunnel to your Domain
Run:
```powershell
cloudflared tunnel route dns local-ai veloxify.dev
```

## 5. Configure the Tunnel
Create a file named `config.yml` in `%USERPROFILE%\.cloudflared\` with the following content:
*(Replace `YOUR_TUNNEL_ID` with your actual ID and `YOUR_USER` with your Windows username)*

```yaml
url: http://localhost:8000
tunnel: YOUR_TUNNEL_ID
credentials-file: C:\Users\YOUR_USER\.cloudflared\YOUR_TUNNEL_ID.json

ingress:
  - hostname: veloxify.dev
    path: ^/ai
    service: http://localhost:8000
  - service: http_status:404
```

> [!NOTE]
> The `path: ^/ai` ensures that only traffic to `veloxify.dev/ai` reaches your app. However, if your app's frontend expects to be at the root `/`, you might want to route the entire subdomain (e.g., `ai.veloxify.dev`) instead for simplicity.

## 6. Run the Tunnel
To start the tunnel, run:
```powershell
cloudflared tunnel run local-ai
```

---

## Alternative: Cloudflare Zero Trust (UI Based)
If you prefer a dashboard:
1.  Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/).
2.  Navigate to **Networks** -> **Tunnels**.
3.  Click **Create a Tunnel** and follow the "Cloudflared" connector instructions.
4.  In the **Public Hostname** tab, set:
    - **Subdomain**: `ai` (or leave empty if using a path)
    - **Domain**: `veloxify.dev`
    - **Path**: `ai` (optional)
    - **Service Type**: `HTTP`
    - **URL**: `localhost:8000`

---

## 7. Mobile Access
Once the tunnel is running:
1.  Open Chrome on your mobile.
2.  Go to `https://veloxify.dev/ai` (or your chosen URL).
3.  Enter the password: **`AAaa1111$`**.
4.  Chat & enjoy!
