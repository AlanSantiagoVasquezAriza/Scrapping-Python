import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from fastapi.routing import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/scrape-news")
def scrape_news():
    return main()

# ------------------------------ Código de scraping ------------------------------

# Headers para simular navegador real y evitar bloqueos del servidor
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

## Descarga el contenido HTML de una URL y lo convierte en un objeto BeautifulSoup.
def obtener_sopa(url):    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        print(f"Error al obtener la página {url}: {e}")
        return None

## Extrae la información de las noticias de la página HTML.
def extraer_noticias(soup):    
    noticias = []
    if soup is None:
        return noticias

    # Buscar cada noticia en los elementos <li> con clase específica
    items = soup.find_all('li', class_='bbc-t44f9r')
    for item in items:
        try:
            # Título de la noticia
            titulo_tag = item.find('h2')
            titulo = titulo_tag.get_text(strip=True) if titulo_tag else 'N/A'

            # Enlace a la noticia
            enlace_tag = item.find('a', href=True)
            enlace = enlace_tag['href'] if enlace_tag else 'N/A'

            # URL de la imagen
            foto_url = item.find('img', src=True)
            foto = foto_url['src'] if foto_url else 'N/A'

            # Fecha de publicación
            fecha_tag = item.find('time')
            fecha = fecha_tag['datetime'] if fecha_tag and fecha_tag.has_attr('datetime') else 'N/A'

            noticias.append({
                'Título': titulo,
                'Fecha': fecha,
                'Enlace': enlace,
                'Foto_url': foto
            })
        except Exception as e:
            print(f"Error al extraer un ítem: {e}")
            continue
    return noticias

## Busca el enlace a la siguiente página de noticias.
def obtener_siguiente_pagina(soup):
    if soup is None:
        return None
    # Buscar el enlace de paginación con aria-labelledby="pagination-next-page"
    next_page = soup.find('a', attrs={'aria-labelledby': 'pagination-next-page'})
    if next_page and next_page.has_attr('href'):
        href = next_page['href']
        # Si el href ya es absoluto, úsalo tal cual; si es relativo, agrégale el dominio
        if href.startswith('http'):
            return href
        else:
            return 'https://www.bbc.com/mundo/topics/cyx5krnw38vt' + href if href.startswith('?') else 'https://www.bbc.com' + href
    return None

## Función principal del script.
def main():
    url_inicial = 'https://www.bbc.com/mundo/topics/cyx5krnw38vt'  # URL de la sección de tecnología
    todas_noticias = []  # Lista para almacenar todas las noticias extraídas
    url_actual = url_inicial
    paginas_a_crawl = 3  # Limitar a 3 páginas para no sobrecargar el servidor

    for i in range(paginas_a_crawl):
        print(f"Procesando página {i+1}: {url_actual}")
        sopa = obtener_sopa(url_actual)
        noticias = extraer_noticias(sopa)
        if not noticias:
            print("No se encontraron noticias o error en la página.")
            break
        todas_noticias.extend(noticias)

        siguiente = obtener_siguiente_pagina(sopa)
        if not siguiente:
            print("No hay más páginas para procesar.")
            break
        url_actual = siguiente
        time.sleep(2)  # Pausa para no saturar el servidor

    # Guardar los datos en un archivo Excel si se extrajo al menos una noticia
    if todas_noticias:
        df = pd.DataFrame(todas_noticias)
        df.to_excel('noticias.xlsx', index=False)
        print("Datos guardados en 'noticias.xlsx'")
        return JSONResponse(content=df.to_dict(orient="records"))
    else:
        print("No se extrajeron datos.")