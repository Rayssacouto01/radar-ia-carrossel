"""Interface web para gerar roteiro ou carrossel a partir de um link, sob demanda."""

import base64
import os
import secrets
import shutil
import sys
import tempfile
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

import anthropic

from src.carousel_generator import generate_carousel
from src.classifier import generate_manual

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
WEBAPP_PASSWORD = os.getenv("WEBAPP_PASSWORD", "")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if not WEBAPP_PASSWORD:
            error = "WEBAPP_PASSWORD não configurado no servidor."
        elif request.form.get("password") == WEBAPP_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("index"))
        else:
            error = "Senha incorreta."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
@login_required
def generate():
    if not _client:
        return jsonify(ok=False, error="ANTHROPIC_API_KEY não configurado no servidor."), 500

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    formato = (data.get("formato") or "").strip()

    if not url or formato not in ("roteiro", "carrossel"):
        return jsonify(ok=False, error="Informe um link e escolha o formato (roteiro ou carrossel)."), 400

    content = generate_manual(url, formato, _client)
    if not content:
        return jsonify(ok=False, error="Não foi possível gerar o conteúdo a partir desse link."), 502

    news = {"title": content.news.title, "url": content.news.url, "source": content.news.source}

    if formato == "roteiro":
        return jsonify(
            ok=True,
            formato="roteiro",
            news=news,
            roteiro={
                "duracao": content.roteiro_duracao,
                "gancho": content.roteiro_gancho,
                "desenvolvimento": content.roteiro_desenvolvimento,
                "cta": content.roteiro_cta,
                "notas_gravacao": content.roteiro_notas_gravacao,
            },
        )

    tmp_dir = tempfile.mkdtemp(prefix="carrossel_manual_")
    try:
        paths = generate_carousel(content, tmp_dir)
        slides = []
        for i, path in enumerate(paths, start=1):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            slides.append({"index": i, "data_uri": f"data:image/png;base64,{b64}"})
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return jsonify(ok=True, formato="carrossel", news=news, slides=slides)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
