import os
import requests
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

# 1. Configuración
load_dotenv()
app = FastAPI(title="API de Análisis TikTok (VADER)")

# CORS (Permitir que tu futuro frontend se conecte)
origins = ["*"]  # Por ahora permitimos todo para probar fácil
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Inicializar VADER
analyzer = SentimentIntensityAnalyzer()
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")


# 3. Función para obtener comentarios (CORREGIDA)
def obtener_comentarios_tiktok(video_url: str):
    if not RAPIDAPI_KEY:
        print("❌ Error: Falta RAPIDAPI_KEY")
        return []

    # URL limpia (quitamos la basura del final)
    video_url = video_url.split("?")[0]
    print(f"🔎 Consultando URL limpia: {video_url}")

    url = "https://tiktok-scraper7.p.rapidapi.com/comment/list"
    querystring = {"url": video_url, "count": "50"}

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "tiktok-scraper7.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        # --- 🛑 IMPRIMIR RESPUESTA PARA VER EL ERROR ---
        print("📩 RESPUESTA DE RAPIDAPI:", data)
        # ---------------------------------------------

        comentarios_texto = []
        lista_comentarios = data.get("data", {}).get("comments", [])

        if not lista_comentarios:
            print("⚠️ La lista de comentarios llegó vacía. Revisa el JSON impreso arriba.")

        for c in lista_comentarios:
            texto = c.get("text")
            if texto:
                comentarios_texto.append(texto)

        return comentarios_texto

    except Exception as e:
        print(f"❌ Error conectando a RapidAPI: {e}")
        return []


# 4. Función de Análisis (VADER)
def analizar_con_vader(lista_textos):
    resultados = {"Positivo": 0, "Neutral": 0, "Negativo": 0}
    lista_clasificada = []

    for texto in lista_textos:
        scores = analyzer.polarity_scores(texto)
        compound = scores['compound']

        if compound >= 0.05:
            sentimiento = "Positivo"
            resultados["Positivo"] += 1
        elif compound <= -0.05:
            sentimiento = "Negativo"
            resultados["Negativo"] += 1
        else:
            sentimiento = "Neutral"
            resultados["Neutral"] += 1

        lista_clasificada.append({
            "comentario": texto,
            "sentimiento": sentimiento
        })

    return resultados, lista_clasificada


# 5. Endpoint Principal
@app.get("/analizar-tiktok/")
async def analizar_tiktok(video_url: str = Query(..., description="URL del video de TikTok")):
    # A. Obtener
    comentarios = obtener_comentarios_tiktok(video_url)

    if not comentarios:
        raise HTTPException(status_code=404, detail="No se encontraron comentarios o el link es inválido")

    # B. Analizar
    counts, detalles = analizar_con_vader(comentarios)

    return {
        "plataforma": "TikTok",
        "video_url": video_url,
        "total_comentarios": len(comentarios),
        "sentimientos": counts,
        "lista_comentarios": detalles
    }