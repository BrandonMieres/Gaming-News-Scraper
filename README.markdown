# Gaming News Scraper

## Descripción
**Gaming News Scraper** es un proyecto personal creado por diversión y aprendizaje. Su objetivo es extraer noticias de videojuegos del sitio web [Vandal](https://vandal.elespanol.com), generar contenido optimizado para TikTok (captions, títulos, descripciones e imágenes) y organizarlo en una estructura de carpetas clara. Este proyecto no tiene fines comerciales; es simplemente una forma de practicar habilidades de programación, web scraping y manejo de datos.

El script está escrito en Python y utiliza bibliotecas como `requests`, `BeautifulSoup` y `logging` para realizar el scraping, procesar datos y registrar actividades. Es un proyecto ideal para aprender sobre scraping web, gestión de archivos, y generación automática de contenido.

## Funcionalidades
- **Scraping de noticias**: Extrae hasta 5 noticias de videojuegos (configurable) desde la sección de noticias de Vandal.
- **Evitar duplicados**: Utiliza un archivo de historial (`news_history.json`) para no procesar noticias ya descargadas.
- **Generación de contenido para TikTok**:
  - Crea **captions** (pies de foto) optimizados para TikTok con título, resumen breve, enlace y hashtags.
  - Genera descripciones y títulos para cada noticia.
- **Descarga de imágenes**: Descarga la imagen destacada de cada noticia (si está disponible).
- **Organización de archivos**:
  - Guarda el contenido en carpetas con formato `YYYY-MM-DD` (por ejemplo, `2025-05-13`).
  - Crea subcarpetas `noticia_1`, `noticia_2`, etc., que contienen:
    - `caption.txt`: Pie de foto para TikTok.
    - `description.txt`: Título y descripción de la noticia.
    - `image_<safe_title>.<ext>`: Imagen descargada.
  - Genera un archivo `news.json` con los datos de todas las noticias.
  - Consolida todos los captions en `all_captions.txt`.
- **Logging y depuración**:
  - Registra actividades en `logs/logs/YYYY-MM-DD.log`.
  - Guarda archivos HTML de depuración en `logs/debug` para analizar problemas.
- **Manejo de errores**: Incluye reintentos automáticos para solicitudes HTTP y un método de respaldo si no se encuentran noticias nuevas.

## Estructura de salida
Ejemplo de estructura tras ejecutar el script el 13 de mayo de 2025:
```
gaming_news_output/
├── contenido/
│   └── 2025-05-13/
│       ├── noticia_1/
│       │   ├── caption.txt
│       │   ├── description.txt
│       │   └── image_nuevo_juego.jpg
│       ├── noticia_2/
│       │   ├── caption.txt
│       │   ├── description.txt
│       │   └── image_actualizacion.jpg
│       ├── ...
│       ├── news.json
│       └── all_captions.txt
├── logs/
│   ├── logs/
│   │   └── 2025-05-13.log
│   └── debug/
│       ├── debug_page_1.html
│       ├── debug_article_<id>.html
│       └── debug_homepage.html
└── news_history.json
```

## Propósito
Este proyecto nació como un pasatiempo para:
- Aprender técnicas de **web scraping** con Python.
- Practicar la manipulación de datos y archivos.
- Explorar la generación automática de contenido para redes sociales.
- Experimentar con logging, manejo de errores y organización de proyectos.

No está diseñado para producción ni para uso comercial, sino como un ejercicio de programación divertido y educativo.

## Requisitos
- Python 3.7 o superior.
- Bibliotecas necesarias (instálalas con `pip`):
  ```bash
  pip install requests beautifulsoup4 urllib3
  ```

## Instalación
1. Clona o descarga el repositorio.
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
   O directamente:
   ```bash
   pip install requests beautifulsoup4 urllib3
   ```
3. Asegúrate de tener una conexión a internet para acceder a Vandal.

## Uso
1. Ejecuta el script:
   ```bash
   python gaming_news_scraper.py
   ```
2. El script:
   - Extrae noticias de Vandal.
   - Genera captions, descripciones e imágenes.
   - Organiza todo en `gaming_news_output/contenido/YYYY-MM-DD`.
   - Registra actividades en `gaming_news_output/logs/logs/YYYY-MM-DD.log`.
3. Revisa la carpeta `contenido/YYYY-MM-DD` para encontrar los archivos generados.
4. Si ejecutas el script varias veces el mismo día, se crearán carpetas con sufijos como `YYYY-MM-DD_V1`, `YYYY-MM-DD_V2`, etc.

## Configuración
El archivo contiene un diccionario `noticias.py` con parámetros ajustables:
- `news_count`: Número de noticias a extraer (por defecto, 5).
- `caption_max_length`: Longitud máxima del caption de TikTok (150 caracteres).
- `summary_length`: Longitud del resumen en el caption (80 caracteres).
- `description_length`: Longitud de la descripción (200 caracteres).
- `hashtags`: Lista de hashtags para los captions.
- `history_limit`: Máximo de noticias en el historial (500).

Modifica `noticias.py` en el código para personalizar el comportamiento.

## Notas
- **Ética**: Respeta los términos de uso de Vandal. Este proyecto es solo para aprendizaje y no debe usarse para violar derechos de autor o políticas del sitio.
- **Limitaciones**: El scraping depende de la estructura del sitio web. Si Vandal cambia su diseño, el script podría requerir ajustes.
- **Depuración**: Los archivos en `logs/debug` son útiles para diagnosticar problemas si el scraping falla.

## Contribuciones
Este es un proyecto personal, pero si quieres contribuir con ideas, mejoras o correcciones, ¡siéntete libre de compartirlas! Puedes abrir un issue o enviar un pull request.

## Licencia
Este proyecto no tiene una licencia formal, ya que es un ejercicio de aprendizaje. Úsalo libremente para aprender, pero no lo redistribuyas con fines comerciales.

---

*Hecho con ☕ y un poco de aburrimiento por Brandon Mieres.*