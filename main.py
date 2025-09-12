# -*- coding: utf-8 -*-
import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_first_image_src(img_elem):
    """Devuelve la mejor URL disponible de un <img> (src, data-src, srcset, etc.)."""
    if img_elem is None:
        return ''
    for attr in ('src', 'data-src', 'data-lazy-src', 'data-original', 'data-srcset', 'srcset'):
        val = img_elem.get_attribute(attr)
        if val:
            # si es srcset tomar la primera URL
            if attr in ('srcset', 'data-srcset'):
                parts = [p.strip() for p in val.split(',') if p.strip()]
                if parts:
                    first = parts[0]
                    # "url 1x" -> quedarnos con la url
                    url = first.split()[0]
                    return url
            return val
    return ''

# ----- Configuración Selenium -----
chrome_options = Options()
chrome_options.add_argument('--headless')            # comenta esta línea para ver el navegador
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')
# user-agent ayuda a parecer navegador real
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

driver = webdriver.Chrome(options=chrome_options)

try:
    url = "https://www.ktronix.com/electrodomesticos/grandes-electrodomesticos/c/BI_151_KTRON?sort=relevance&q=%3Arelevance%3Abrand%3ASAMSUNG"
    driver.get(url)

    wait = WebDriverWait(driver, 15)
    # esperar a que aparezcan los items
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.product__item")))

    time.sleep(1)  # un pequeño extra para que renderice JS si hace falta

    productos = driver.find_elements(By.CSS_SELECTOR, "li.product__item")

    titles = []
    precios = []
    precios_formateados = []
    url_imagenes = []
    calificaciones = []

    for producto in productos:
        # desplazar para asegurar lazy-load
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", producto)
        except:
            pass
        time.sleep(0.12)

        # título
        try:
            title = producto.find_element(By.CSS_SELECTOR, "h3.product__item__top__title").text.strip()
        except:
            title = ''

        # precio: probar varios selectores y fallback a innerText
        precio_raw_text = ''
        try:
            selectors = [
                'p.product_price--discounts_price span.price',
                'div.product_item_information_base-price span.price',
                'span.price',
                'p.product_price--discounts_price',
                '.product_price--discounts_price .price'
            ]
            for sel in selectors:
                elems = producto.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    precio_raw_text = elems[0].text
                    if precio_raw_text:
                        break

            # fallback: tomar todo el innerText del producto y extraer el número
            if not precio_raw_text:
                precio_raw_text = producto.get_attribute('innerText') or ''
        except Exception:
            precio_raw_text = ''

        # limpieza y extracción del primer grupo numérico (puntos/comas admitidos)
        precio_digits = ''
        if precio_raw_text:
            # normalizar espacios y comillas raras
            texto = precio_raw_text.replace('\xa0', ' ').replace('\n', ' ').strip()
            # buscar primer patrón con dígitos, puntos o comas (ej: 3.499.030 o 3,499.03)
            m = re.search(r'[\d\.,]+', texto)
            if m:
                found = m.group(0)
                # limpiar comillas o símbolos
                found = found.strip().strip('"“”\'')
                # mantener solo dígitos -> número entero (Quitar separadores)
                precio_digits = re.sub(r'[^\d]', '', found)

        # convertir a int si se encontró
        if precio_digits:
            try:
                precio_int = int(precio_digits)
                precio = precio_int
                precio_formateado = f"{precio_int:,}".replace(',', '.')
            except:
                precio = ''
                precio_formateado = ''
        else:
            precio = ''
            precio_formateado = ''

        # imagen
        try:
            img = producto.find_element(By.TAG_NAME, 'img')
            url_imagen = get_first_image_src(img)
        except:
            url_imagen = ''

        # calificacion
        try:
            cal = producto.find_element(By.CSS_SELECTOR, 'span.averageNumber').text.strip()
        except:
            cal = ''

        titles.append(title)
        precios.append(precio)
        precios_formateados.append(precio_formateado)
        url_imagenes.append(url_imagen)
        calificaciones.append(cal)

    # DataFrame
    df = pd.DataFrame({
        "Title": titles,
        "Precio": precios,
        "Precio_formateado": precios_formateados,
        "URL Imagen": url_imagenes,
        "Calificacion": calificaciones
    })

    # Guardar
    df.to_excel("resultados.xlsx", index=False)
    print("✅ Datos exportados a resultados.xlsx")
    print(df.head(30))

finally:
    driver.quit()
