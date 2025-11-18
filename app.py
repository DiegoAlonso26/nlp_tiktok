import os
import requests
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

# 1. Cargar variables y configurar
load_dotenv()
app = FastAPI(title="API de Análisis TikTok (VADER)")

# CORS (Permitir todo para pruebas, luego restringir si quieres)
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = SentimentIntensityAnalyzer()
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

# --- DIAGNÓSTICO AL INICIAR ---
if not RAPIDAPI_KEY:
    print("❌ ERROR CRÍTICO: No se encontró RAPIDAPI_KEY. Revisa tu archivo .env")
else:
    print(f"✅ API Key cargada (Empieza con: {RAPIDAPI_KEY[:5]}...)")


# 3. Función para obtener comentarios
def obtener_comentarios_tiktok(video_url: str):
    if not RAPIDAPI_KEY:
        print("❌ Error: Falta RAPIDAPI_KEY")
        return []

    # Limpieza de URL (por si acaso el frontend mandó basura)
    video_url = video_url.split("?")[0]
    print(f"🔎 Analizando URL: {video_url}")

    url = "https://tiktok-scraper7.p.rapidapi.com/comment/list"
    querystring = {"url": video_url, "count": "50"}

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "tiktok-scraper7.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)

        # --- BLOQUE DE SEGURIDAD ---
        if response.status_code != 200:
            print(f"⚠️ Error de RapidAPI (Código {response.status_code}):")
            print(f"📩 Respuesta: {response.text}")
            return []  # Retornamos lista vacía para no romper el servidor

        data = response.json()

        comentarios_texto = []
        # La estructura común es data -> data -> comments
        lista_comentarios = data.get("data", {}).get("comments", [])

        if not lista_comentarios:
            print(f"⚠️ La API respondió OK (200) pero no trajo comentarios. Respuesta: {data}")

        for c in lista_comentarios:
            texto = c.get("text")
            if texto:
                comentarios_texto.append(texto)

        print(f"✅ Se encontraron {len(comentarios_texto)} comentarios.")
        return comentarios_texto

    except Exception as e:
        print(f"❌ Error interno en la función: {e}")
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
        # En vez de lanzar error 404, devolvemos estructura vacía para que el front no explote
        # y puedas ver el error en la consola del servidor
        print("⚠️ Devolviendo respuesta vacía por falta de comentarios.")
        return {
            "plataforma": "TikTok",
            "video_url": video_url,
            "total_comentarios": 0,
            "sentimientos": {"Positivo": 0, "Neutral": 0, "Negativo": 0},
            "lista_comentarios": []
        }

    # B. Analizar
    counts, detalles = analizar_con_vader(comentarios)

    return {
        "plataforma": "TikTok",
        "video_url": video_url,
        "total_comentarios": len(comentarios),
        "sentimientos": counts,
        "lista_comentarios": detalles
    }