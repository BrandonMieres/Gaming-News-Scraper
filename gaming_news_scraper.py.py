#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extractor de noticias de videojuegos y generador de contenido para TikTok.
Obtiene noticias de Vandal, genera pies de foto, títulos, descripciones e imágenes.
Organiza el contenido en carpetas por fecha (YYYY-MM-DD) con subcarpetas por noticia.
"""

import json
import logging
import requests
import random
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict, field
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

# Configuración del logger global
logger = logging.getLogger("gaming_news_scraper")

# Configuración de constantes
BASE_URL = "https://vandal.elespanol.com"
NEWS_URL = f"{BASE_URL}/noticias/videojuegos"
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0'
]
OUTPUT_DIR = Path("gaming_news_output")
CONTENT_DIR = OUTPUT_DIR / "contenido"
LOGS_DIR = OUTPUT_DIR / "logs"
LOG_SUBDIR = LOGS_DIR / "logs"
DEBUG_SUBDIR = LOGS_DIR / "debug"
HISTORY_FILE = OUTPUT_DIR / "news_history.json"
CONFIG = {
    "news_count": 5,  # Número de noticias a extraer
    "caption_max_length": 150,  # Longitud máxima del caption para TikTok
    "summary_length": 80,  # Longitud del resumen en el caption
    "description_length": 200,  # Longitud máxima de la descripción
    "request_timeout": 15,  # Timeout para las solicitudes HTTP en segundos
    "sleep_range": (1, 3),  # Rango de espera entre solicitudes (segundos)
    "hashtags": ["Gaming", "Videojuegos", "Noticias", "Gamer", "PlayStation", "Xbox", "Nintendo", "PC"],
    "max_retries": 3,  # Número máximo de reintentos para obtener noticias
    "retry_delay": 5,  # Tiempo de espera entre reintentos (segundos)
    "history_limit": 500  # Límite de noticias en el historial
}

# Configuración de logging
def setup_logging(date_str: str) -> None:
    """Configura el logging para escribir en archivo y consola."""
    LOG_SUBDIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_SUBDIR / f"{date_str}.log"
    logger.setLevel(logging.INFO)
    logger.handlers = []
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

@dataclass
class NewsItem:
    """Clase para representar un artículo de noticias."""
    title: str
    summary: str
    link: str
    image_url: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[str] = None
    news_id: str = field(default="", init=False)
    
    def __post_init__(self):
        """Genera un ID único para la noticia basado en su título y enlace."""
        if not self.news_id:
            content = f"{self.title}|{self.link}".encode('utf-8')
            self.news_id = hashlib.md5(content).hexdigest()

class NewsHistory:
    """Clase para gestionar el historial de noticias descargadas."""
    
    def __init__(self, history_file: Path = HISTORY_FILE, limit: int = CONFIG["history_limit"]):
        """Inicializa el gestor de historial."""
        self.history_file = history_file
        self.limit = limit
        self.news_ids = self._load_history()
    
    def _load_history(self) -> Set[str]:
        """Carga el historial de noticias desde el archivo."""
        if not self.history_file.exists():
            return set()
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                return set(history_data.get("news_ids", []))
        except Exception as e:
            logger.error(f"Error al cargar el historial de noticias: {e}")
            return set()
    
    def save_history(self) -> None:
        """Guarda el historial de noticias en el archivo."""
        try:
            news_ids_list = list(self.news_ids)
            if len(news_ids_list) > self.limit:
                news_ids_list = news_ids_list[-self.limit:]
                self.news_ids = set(news_ids_list)
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({"news_ids": list(self.news_ids)}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error al guardar el historial de noticias: {e}")
    
    def is_duplicate(self, news_item: NewsItem) -> bool:
        """Verifica si una noticia ya ha sido descargada."""
        return news_item.news_id in self.news_ids
    
    def add_item(self, news_item: NewsItem) -> None:
        """Añade una noticia al historial."""
        self.news_ids.add(news_item.news_id)

class GamingNewsScraper:
    """Clase para extraer noticias de videojuegos."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Inicializa el scraper con la configuración proporcionada."""
        self.config = config or CONFIG
        self.session = self._create_session()
        self._ensure_output_dir()
        self.history = NewsHistory(limit=self.config["history_limit"])
    
    @staticmethod
    def _create_session() -> requests.Session:
        """Crea una sesión HTTP con reintentos automáticos."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    @staticmethod
    def _ensure_output_dir() -> None:
        """Asegura que los directorios de salida existan."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        LOG_SUBDIR.mkdir(parents=True, exist_ok=True)
        DEBUG_SUBDIR.mkdir(parents=True, exist_ok=True)
    
    def _get_random_headers(self) -> Dict[str, str]:
        """Genera encabezados HTTP aleatorios para evitar detección."""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
    
    def fetch_gaming_news(self, page: int = 1) -> List[NewsItem]:
        """Extrae las noticias de videojuegos del sitio web."""
        news_list = []
        
        try:
            if page > 1:
                page_url = f"{NEWS_URL}/{page}"
            else:
                page_url = NEWS_URL
                
            logger.info(f"Obteniendo noticias desde {page_url}")
            
            response = self.session.get(
                page_url,
                headers=self._get_random_headers(),
                timeout=self.config["request_timeout"]
            )
            response.raise_for_status()
            
            debug_path = DEBUG_SUBDIR / f"debug_page_{page}.html"
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.debug(f"HTML guardado para depuración en {debug_path}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            selectors = [
                'article.noticia', 'div.article', 'div.card', '.cardNoticia',
                '.noticia', 'div.item', 'article', '.article-item'
            ]
            
            articles = []
            for selector in selectors:
                articles = soup.select(selector)
                if articles:
                    logger.info(f"Selector exitoso: '{selector}'")
                    break
            
            if not articles:
                titles = soup.select('h2 a, h1 a, h3 a')
                if titles:
                    logger.info(f"Usando método alternativo, se encontraron {len(titles)} títulos")
                    for title_tag in titles:
                        href = title_tag.get('href', '')
                        if 'noticia' in href.lower() and '/n.' in href.lower():
                            articles.append(title_tag.parent.parent)
            
            if not articles:
                logger.warning(f"No se encontraron artículos en la página {page}")
                return []
            
            logger.info(f"Se encontraron {len(articles)} artículos en la página {page}")
            
            for article in articles:
                try:
                    title_selectors = ['h2.titular a', 'h2 a', 'h1 a', 'h3 a', '.title a', 'a.title', 'a[title]']
                    title_tag = None
                    for selector in title_selectors:
                        title_tag = article.select_one(selector)
                        if title_tag:
                            break
                    
                    if not title_tag:
                        continue
                        
                    title = title_tag.get_text(strip=True)
                    
                    summary_selectors = ['p.texto', 'p.description', '.summary', '.excerpt', 'p:not(.meta)', 'p']
                    summary_tag = None
                    for selector in summary_selectors:
                        summary_tag = article.select_one(selector)
                        if summary_tag:
                            break
                    
                    summary = summary_tag.get_text(strip=True) if summary_tag else 'Sin resumen disponible'
                    
                    link = title_tag['href'] if 'href' in title_tag.attrs else ''
                    if link and not link.startswith(('http://', 'https://')):
                        link = f"{BASE_URL}{link}"
                    
                    image_selectors = ['img', '.image img', '.thumbnail img', 'figure img']
                    image_tag = None
                    for selector in image_selectors:
                        image_tag = article.select_one(selector)
                        if image_tag:
                            break
                    
                    image_url = None
                    if image_tag:
                        for attr in ['src', 'data-src', 'data-lazy-src', 'data-srcset']:
                            if attr in image_tag.attrs:
                                image_url = image_tag[attr].split(' ')[0] if ' ' in image_tag[attr] else image_tag[attr]
                                break
                    
                    if image_url and not image_url.startswith(('http://', 'https://')):
                        image_url = f"{BASE_URL}{image_url}"
                    
                    author_selectors = ['.autor', '.author', '.meta .author', 'span.author']
                    author_tag = None
                    for selector in author_selectors:
                        author_tag = article.select_one(selector)
                        if author_tag:
                            break
                    
                    author = author_tag.get_text(strip=True) if author_tag else None
                    
                    date_selectors = ['.fecha', '.date', '.meta .date', 'time', 'span.date']
                    date_tag = None
                    for selector in date_selectors:
                        date_tag = article.select_one(selector)
                        if date_tag:
                            break
                    
                    published_date = date_tag.get_text(strip=True) if date_tag else None
                    
                    if title and link:
                        news_item = NewsItem(
                            title=title,
                            summary=summary,
                            link=link,
                            image_url=image_url,
                            author=author,
                            published_date=published_date
                        )
                        news_list.append(news_item)
                        logger.info(f"Noticia extraída: {title}")
                
                except Exception as e:
                    logger.error(f"Error al procesar un artículo: {e}")
                    continue
            
        except requests.RequestException as e:
            logger.error(f"Error en la solicitud HTTP: {e}")
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
        
        return news_list
    
    def fetch_article_details(self, news_item: NewsItem) -> NewsItem:
        """Obtiene detalles adicionales del artículo visitando su página."""
        if not news_item.link:
            return news_item
            
        try:
            sleep_time = random.uniform(*self.config["sleep_range"])
            logger.debug(f"Esperando {sleep_time:.2f} segundos antes de la próxima solicitud")
            time.sleep(sleep_time)
            
            logger.info(f"Obteniendo detalles del artículo: {news_item.link}")
            response = self.session.get(
                news_item.link,
                headers=self._get_random_headers(),
                timeout=self.config["request_timeout"]
            )
            response.raise_for_status()
            
            debug_path = DEBUG_SUBDIR / f"debug_article_{news_item.news_id[:8]}.html"
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            summary_selectors = [
                'div.entradilla', '.article-summary', '.summary', 
                '.intro', '.excerpt', 'meta[name="description"]'
            ]
            
            for selector in summary_selectors:
                full_summary_tag = soup.select_one(selector)
                if full_summary_tag:
                    if selector == 'meta[name="description"]':
                        news_item.summary = full_summary_tag.get('content', '')
                    else:
                        news_item.summary = full_summary_tag.get_text(strip=True)
                    break
            
            if not news_item.image_url:
                image_selectors = [
                    'div.imagen img', '.article-featured-image img', 
                    '.featured-image img', 'article img', '.content img', 
                    'meta[property="og:image"]'
                ]
                
                for selector in image_selectors:
                    main_image = soup.select_one(selector)
                    if main_image:
                        if selector == 'meta[property="og:image"]':
                            news_item.image_url = main_image.get('content', '')
                        elif 'data-src' in main_image.attrs:
                            news_item.image_url = main_image['data-src']
                        elif 'src' in main_image.attrs:
                            news_item.image_url = main_image['src']
                        
                        if news_item.image_url and not news_item.image_url.startswith(('http://', 'https://')):
                            news_item.image_url = f"{BASE_URL}{news_item.image_url}"
                        break
            
        except Exception as e:
            logger.error(f"Error al obtener detalles del artículo: {e}")
        
        return news_item
    
    def download_image(self, news_item: NewsItem, output_dir: Path) -> Optional[Path]:
        """Descarga la imagen de la noticia y la guarda en el directorio especificado."""
        if not news_item.image_url:
            logger.warning(f"No hay URL de imagen para la noticia: {news_item.title}")
            return None
        
        try:
            response = self.session.get(
                news_item.image_url,
                headers=self._get_random_headers(),
                timeout=self.config["request_timeout"]
            )
            response.raise_for_status()
            
            image_ext = news_item.image_url.split('.')[-1].split('?')[0]
            if image_ext.lower() not in ['jpg', 'jpeg', 'png', 'gif']:
                image_ext = 'jpg'
            safe_title = re.sub(r'[^\w\s-]', '', news_item.title).replace(' ', '_')[:50]
            image_filename = output_dir / f"image_{safe_title}.{image_ext}"
            
            with open(image_filename, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Imagen descargada: {image_filename}")
            return image_filename
        
        except Exception as e:
            logger.error(f"Error al descargar la imagen para {news_item.title}: {e}")
            return None
    
    def get_unique_news(self, count: int = None) -> Tuple[List[NewsItem], List[NewsItem]]:
        """Obtiene un número específico de noticias únicas."""
        if count is None:
            count = self.config["news_count"]
        
        new_news = []
        duplicate_news = []
        max_pages = 5
        current_page = 1
        
        while len(new_news) < count and current_page <= max_pages:
            all_news = self.fetch_gaming_news(page=current_page)
            
            if not all_news:
                current_page += 1
                continue
            
            for news_item in all_news:
                if len(new_news) >= count:
                    break
                
                if self.history.is_duplicate(news_item):
                    duplicate_news.append(news_item)
                    logger.info(f"Noticia duplicada: {news_item.title}")
                else:
                    new_news.append(news_item)
                    logger.info(f"Nueva noticia encontrada: {news_item.title}")
            
            if len(new_news) < count:
                current_page += 1
                time.sleep(random.uniform(*self.config["sleep_range"]))
        
        return new_news, duplicate_news

class ContentGenerator:
    """Clase para generar contenido a partir de noticias."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Inicializa el generador con la configuración proporcionada."""
        self.config = config or CONFIG
    
    def format_tiktok_caption(self, news_item: NewsItem) -> str:
        """Genera un pie de foto optimizado para TikTok."""
        selected_hashtags = random.sample(self.config["hashtags"], min(3, len(self.config["hashtags"])))
        caption = f"🎮 {news_item.title}\n\n"
        summary = news_item.summary[:self.config["summary_length"]]
        if len(news_item.summary) > self.config["summary_length"]:
            summary += "..."
        caption += f"{summary}\n\n"
        caption += f"👉 Leer más: {news_item.link}\n\n"
        caption += " ".join([f"#{tag}" for tag in selected_hashtags])
        
        max_length = self.config["caption_max_length"]
        if len(caption) > max_length:
            caption = caption[:max_length-3] + "..."
        
        return caption
    
    def format_description(self, news_item: NewsItem) -> str:
        """Genera una descripción para la noticia."""
        description = news_item.summary[:self.config["description_length"]]
        if len(news_item.summary) > self.config["description_length"]:
            description += "..."
        return description
    
    def save_content(self, news_items: List[NewsItem], captions: List[str], scraper: GamingNewsScraper, date_str: str) -> Tuple[str, Path]:
        """Guarda las noticias, captions, imágenes, títulos y descripciones en subcarpetas por noticia."""
        base_date_dir = CONTENT_DIR / date_str
        version = 1
        date_dir = base_date_dir
        while date_dir.exists():
            date_dir = CONTENT_DIR / f"{date_str}_V{version}"
            version += 1
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar las noticias en formato JSON
        news_filename = date_dir / "news.json"
        with open(news_filename, 'w', encoding='utf-8') as f:
            json.dump([asdict(item) for item in news_items], f, ensure_ascii=False, indent=2)
        logger.info(f"Noticias guardadas en {news_filename}")
        
        # Guardar cada noticia en su propia subcarpeta
        for i, (news_item, caption) in enumerate(zip(news_items, captions)):
            news_dir = date_dir / f"noticia_{i+1}"
            news_dir.mkdir(parents=True, exist_ok=True)
            
            # Guardar caption
            caption_filename = news_dir / "caption.txt"
            with open(caption_filename, 'w', encoding='utf-8') as f:
                f.write(caption)
            logger.info(f"Caption guardado en {caption_filename}")
            
            # Guardar título y descripción
            description_filename = news_dir / "description.txt"
            with open(description_filename, 'w', encoding='utf-8') as f:
                f.write(f"Título: {news_item.title}\n\n")
                f.write(f"Descripción: {self.format_description(news_item)}")
            logger.info(f"Título y descripción guardados en {description_filename}")
            
            # Descargar y guardar imagen
            image_path = scraper.download_image(news_item, news_dir)
            if image_path:
                logger.info(f"Imagen para noticia {i+1} guardada en {image_path}")
        
        # Guardar todos los captions en un solo archivo
        all_captions_filename = date_dir / "all_captions.txt"
        with open(all_captions_filename, 'w', encoding='utf-8') as f:
            for i, caption in enumerate(captions):
                f.write(f"=== CAPTION {i+1} ===\n{caption}\n\n")
        
        logger.info(f"Todos los pies de foto guardados en {all_captions_filename}")
        return str(all_captions_filename), date_dir

def main():
    """Función principal del programa."""
    try:
        date_str = datetime.now().strftime('%Y-%m-%d')
        setup_logging(date_str)
        logger.info("Iniciando el extractor de noticias de videojuegos")
        
        scraper = GamingNewsScraper()
        generator = ContentGenerator()
        
        new_news, duplicate_news = scraper.get_unique_news()
        
        if duplicate_news:
            logger.info(f"Se encontraron {len(duplicate_news)} noticias duplicadas:")
            for item in duplicate_news:
                logger.info(f" - {item.title}")
        
        if not new_news:
            logger.warning("No se obtuvieron noticias nuevas. Intentando método de respaldo.")
            fallback_news = []
            try:
                logger.info("Intentando método de respaldo...")
                response = requests.get(
                    "https://vandal.elespanol.com",
                    headers={'User-Agent': random.choice(USER_AGENTS)},
                    timeout=CONFIG["request_timeout"]
                )
                if response.status_code == 200:
                    debug_path = DEBUG_SUBDIR / "debug_homepage.html"
                    with open(debug_path, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    all_links = soup.find_all('a')
                    news_links = []
                    for link in all_links:
                        href = link.get('href', '')
                        if '/noticia/' in href or '/noticias/' in href:
                            title = link.get_text(strip=True)
                            if title and len(title) > 15:
                                news_links.append((title, href))
                    
                    news_links = list(set(news_links))
                    logger.info(f"Método de respaldo encontró {len(news_links)} posibles noticias")
                    
                    for i, (title, href) in enumerate(news_links[:CONFIG["news_count"]]):
                        if not href.startswith('http'):
                            href = f"{BASE_URL}{href}"
                        fallback_news.append(NewsItem(
                            title=title,
                            summary="",
                            link=href
                        ))
            except Exception as e:
                logger.error(f"Error en el método de respaldo: {e}")
            
            if fallback_news:
                new_news = fallback_news
                logger.info(f"Método de respaldo encontró {len(new_news)} noticias")
            else:
                all_news = scraper.fetch_gaming_news()
                if not all_news:
                    logger.error("No se pudo obtener ninguna noticia. Finalizando.")
                    return 1
                new_news = all_news[:CONFIG["news_count"]]
                logger.info(f"Se utilizarán {len(new_news)} noticias aunque sean duplicadas.")
        else:
            logger.info(f"Se obtuvieron {len(new_news)} noticias nuevas")
        
        detailed_news = []
        for item in new_news:
            detailed_item = scraper.fetch_article_details(item)
            detailed_news.append(detailed_item)
            if not scraper.history.is_duplicate(detailed_item):
                scraper.history.add_item(detailed_item)
        
        scraper.history.save_history()
        
        captions = [generator.format_tiktok_caption(item) for item in detailed_news]
        
        if captions:
            example_index = random.randint(0, len(captions)-1)
            logger.info("Ejemplo de pie de foto para TikTok:")
            logger.info(f"\n{captions[example_index]}")
        
        output_file, output_dir = generator.save_content(detailed_news, captions, scraper, date_str)
        
        logger.info(f"Proceso completado.")
        logger.info(f"Noticias nuevas: {len(new_news)}, Noticias duplicadas: {len(duplicate_news)}")
        logger.info(f"Revisa los archivos generados en: {output_dir}")
        
    except Exception as e:
        logger.error(f"Error en la ejecución del programa: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())