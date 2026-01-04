from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uuid, json, base64, os, io
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
import qrcode

app = FastAPI()

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>VLESS REALITY Configurator</title>
<style>
body{background:#020617;color:#e5e7eb;font-family:Arial;padding:40px}
.box{max-width:900px;margin:auto}
input,button{width:100%;padding:10px;margin:6px 0;border-radius:6px;border:none}
button{background:#22c55e;color:#000;font-weight:bold;cursor:pointer}
textarea{width:100%;height:260px;background:#020617;color:#22c55e;border:1px solid #334155;padding:10px}
h2,h3{color:#38bdf8}
img{margin-top:10px;border:6px solid #0f172a}
small{color:#94a3b8}
</style>
</head>
<body>
<div class="box">
<h2>VLESS + REALITY Config Generator (QR)</h2>

<form method="post">
<input name="domain" placeholder="SNI (example: www.cloudflare.com)" required>
<input name="ip" placeholder="VPS IP" required>
<input name="port" value="443">
<input name="email" placeholder="Client name (optional)">
<button type="submit">Generate</button>
</form>

{result}

<small>
Server: install xray-core → replace config.json → restart xray
</small>
</div>
</body>
</html>
"""

def gen_reality_keys():
    private = x25519.X25519PrivateKey.generate()
    public = private.public_key()

    priv = base64.urlsafe_b64encode(
        private.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
    ).decode().rstrip("=")

    pub = base64.urlsafe_b64encode(
        public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    ).decode().rstrip("=")

    return priv, pub

def short_id():
    return os.urandom(4).hex()

def build_config(uid, domain, port, priv, sid, email):
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "port": int(port),
            "protocol": "vless",
            "settings": {
                "clients": [{
                    "id": uid,
                    "email": email or "client",
                    "flow": "xtls-rprx-vision"
                }],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": f"{domain}:443",
                    "xver": 0,
                    "serverNames": [domain],
                    "privateKey": priv,
                    "shortIds": [sid]
                }
            }
        }],
        "outbounds": [{
            "protocol": "freedom",
            "settings": {}
        }]
    }

def build_link(uid, ip, port, domain, pub, sid, email):
    name = email or "reality"
    return (
        f"vless://{uid}@{ip}:{port}"
        f"?security=reality"
        f"&encryption=none"
        f"&pbk={pub}"
        f"&sid={sid}"
        f"&sni={domain}"
        f"&fp=chrome"
        f"&type=tcp"
        f"#"+name
    )

def make_qr_base64(data):
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML.format(result="")

@app.post("/", response_class=HTMLResponse)
def generate(
    domain: str = Form(...),
    ip: str = Form(...),
    port: str = Form("443"),
    email: str = Form("")
):
    uid = str(uuid.uuid4())
    priv, pub = gen_reality_keys()
    sid = short_id()

    config = build_config(uid, domain, port, priv, sid, email)
    link = build_link(uid, ip, port, domain, pub, sid, email)
    qr_b64 = make_qr_base64(link)

    result = f"""
<h3>UUID</h3>
<textarea readonly>{uid}</textarea>

<h3>Reality Private Key (server)</h3>
<textarea readonly>{priv}</textarea>

<h3>Reality Public Key (client)</h3>
<textarea readonly>{pub}</textarea>

<h3>Xray config.json</h3>
<textarea readonly>{json.dumps(config, indent=2)}</textarea>

<h3>VLESS Reality Link</h3>
<textarea readonly>{link}</textarea>

<h3>QR Code</h3>
<img src="data:image/png;base64,{qr_b64}">
"""

    return HTML.format(result=result)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
