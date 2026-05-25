import os
import re
import csv
import time
import argparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver(headless=True):
    """Sets up the Chrome WebDriver with options to prevent blocking and ensure English language."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=en-US")
    # Set headers/prefs to force English
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option('prefs', {'intl.accept_languages': 'en,en-US'})
    
    # Using webdriver-manager to auto-install and setup driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_imdb_top250(driver):
    """Navigates to IMDb Top 250 page and scrapes movies."""
    url = "https://www.imdb.com/chart/top/"
    print(f"Loading URL: {url} ...")
    driver.get(url)
    
    # Wait for the main list element to load
    print("Waiting for page content to load...")
    wait = WebDriverWait(driver, 15)
    
    # Wait for the metadata list summary items to appear
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ipc-metadata-list-summary-item")))
    
    # Scroll slowly to the bottom to make sure all items render and load their images/ratings
    print("Scrolling page to ensure all items are loaded...")
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # Find all movie items
    items = soup.select("li.ipc-metadata-list-summary-item")
    print(f"Found {len(items)} movie items in page source.")
    
    movies_data = []
    
    for item in items:
        try:
            # 1. Rank & Title & URL
            # Typically inside an h3 with class ipc-title__text
            title_el = item.select_one("h3.ipc-title__text")
            if not title_el:
                continue
            
            title_text = title_el.get_text(strip=True)
            # title_text looks like "1. The Shawshank Redemption"
            match = re.match(r"^(\d+)\.\s+(.*)$", title_text)
            if match:
                rank = int(match.group(1))
                title = match.group(2)
            else:
                # Fallback if pattern doesn't match
                rank = None
                title = title_text
            
            # Extract URL
            movie_url = ""
            a_tags = item.select("a")
            for a in a_tags:
                href = a.get("href", "")
                if "/title/" in href:
                    base_path = href.split("?")[0]
                    movie_url = "https://www.imdb.com" + base_path
                    break
            
            # 2. Metadata: Year, Duration, Certificate
            metadata_items = []
            
            # Look for a div or span that contains the metadata spans
            meta_container = item.select_one("div.cli-title-metadata")
            if not meta_container:
                # Fallback: search for elements with metadata in class
                for div in item.select("div"):
                    classes = div.get("class", [])
                    if any("metadata" in c for c in classes):
                        meta_container = div
                        break
            
            if meta_container:
                ul = meta_container.select_one("ul")
                if ul:
                    spans = ul.select("li")
                else:
                    spans = meta_container.find_all(recursive=False)
                metadata_items = [s.get_text(strip=True) for s in spans]
            
            # Extract fields from metadata items
            year = None
            duration = ""
            certificate = ""
            
            # Parse year (first item matching 4 digits)
            for m_item in metadata_items:
                if re.match(r"^\d{4}$", m_item):
                    year = int(m_item)
                    break
            
            # Duration: check for format like '2h 22m', '1h 30m', '90m'
            for m_item in metadata_items:
                if "h" in m_item or "m" in m_item:
                    duration = m_item
                    break
            
            # Certificate: Usually anything left over
            other_items = [x for x in metadata_items if x != str(year) and x != duration]
            if other_items:
                certificate = other_items[0]
            
            # 3. Rating & Votes
            rating = None
            votes = ""
            
            rating_container = item.select_one("[class*='ipc-rating-star']")
            if rating_container:
                rating_text = rating_container.get_text(strip=True)
                rating_match = re.search(r"(\d+\.\d+)", rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
                
                votes_match = re.search(r"\(([^)]+)\)", rating_text)
                if votes_match:
                    votes = votes_match.group(1)
            
            if not rank:
                rank = len(movies_data) + 1
                
            movies_data.append({
                "Rank": rank,
                "Title": title,
                "Year": year,
                "Rating": rating,
                "Duration": duration,
                "Certificate": certificate,
                "Votes": votes,
                "URL": movie_url,
                "Genres": "",
                "Director": "",
                "Cast": "",
                "Synopsis": ""
            })
            
        except Exception as e:
            print(f"Error parsing movie item: {e}")
            
    # Sort by rank
    movies_data = sorted(movies_data, key=lambda x: x["Rank"] if x["Rank"] is not None else 999)
    return movies_data

def scrape_movie_detail(driver, movie_url):
    """Fetches a single movie detail page and extracts deep information (Genres, Director, Cast, Synopsis)."""
    if not movie_url:
        return {
            "Genres": "",
            "Director": "",
            "Cast": "",
            "Synopsis": ""
        }
        
    print(f"Scraping detail page: {movie_url} ...")
    try:
        driver.get(movie_url)
        # Wait for either JSON-LD or general content
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, "//script[@type='application/ld+json']"))
            )
        except Exception:
            time.sleep(2)
            
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        details = {
            "Genres": "",
            "Director": "",
            "Cast": "",
            "Synopsis": ""
        }
        
        # 1. Try parsing JSON-LD first (highly robust)
        try:
            import json
            json_ld_tags = soup.find_all('script', type='application/ld+json')
            for tag in json_ld_tags:
                if not tag.string:
                    continue
                try:
                    data = json.loads(tag.string)
                    if isinstance(data, dict) and data.get("@type") in ["Movie", "CreativeWork", "TVSeries"]:
                        # Extract Genres
                        if "genre" in data:
                            genres = data["genre"]
                            if isinstance(genres, list):
                                details["Genres"] = ", ".join(genres)
                            else:
                                details["Genres"] = str(genres)
                        
                        # Extract Director
                        if "director" in data:
                            directors = data["director"]
                            if isinstance(directors, list):
                                details["Director"] = ", ".join([d.get("name", "") for d in directors if isinstance(d, dict) and "name" in d])
                            elif isinstance(directors, dict):
                                details["Director"] = directors.get("name", "")
                        
                        # Extract Cast (actors)
                        if "actor" in data:
                            actors = data["actor"]
                            if isinstance(actors, list):
                                details["Cast"] = ", ".join([a.get("name", "") for a in actors[:5] if isinstance(a, dict) and "name" in a])
                            elif isinstance(actors, dict):
                                details["Cast"] = actors.get("name", "")
                                
                        # Extract Synopsis
                        if "description" in data:
                            details["Synopsis"] = data["description"]
                            
                        if details["Genres"] or details["Director"] or details["Cast"] or details["Synopsis"]:
                            break
                except Exception as e:
                    print(f"Error parsing single JSON-LD block: {e}")
        except Exception as e:
            print(f"Error locating/parsing JSON-LD: {e}")
            
        # 2. Fallbacks using CSS Selectors (HTML fallback)
        # Genres fallback
        if not details["Genres"]:
            try:
                genre_elements = soup.select('div[data-testid="genres"] a')
                if genre_elements:
                    details["Genres"] = ", ".join([g.get_text(strip=True) for g in genre_elements])
            except Exception:
                pass
                
        # Synopsis fallback
        if not details["Synopsis"]:
            try:
                plot_element = soup.select_one('span[data-testid="plot-xl"]') or \
                               soup.select_one('span[data-testid="plot-l"]') or \
                               soup.select_one('p[data-testid="plot"]')
                if plot_element:
                    details["Synopsis"] = plot_element.get_text(strip=True)
            except Exception:
                pass
                
        # Director fallback
        if not details["Director"]:
            try:
                for li in soup.select('li[data-testid="title-pc-principal-credits"]'):
                    text = li.get_text()
                    if "Director" in text or "Directors" in text:
                        names = [a.get_text(strip=True) for a in li.select('a') if '/name/' in a.get('href', '')]
                        details["Director"] = ", ".join(names)
                        break
            except Exception:
                pass
                
        # Cast fallback
        if not details["Cast"]:
            try:
                actor_elements = soup.select('a[data-testid="title-cast-item__actor"]')
                if actor_elements:
                    details["Cast"] = ", ".join([a.get_text(strip=True) for a in actor_elements[:5]])
            except Exception:
                pass
                
        return details
        
    except Exception as e:
        print(f"Failed to scrape detail page {movie_url}: {e}")
        return {
            "Genres": "",
            "Director": "",
            "Cast": "",
            "Synopsis": ""
        }
def save_to_csv(movies, filepath):
    """Saves movies list of dicts to a CSV file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    fields = ["Rank", "Title", "Year", "Rating", "Duration", "Certificate", "Votes", "Genres", "Director", "Cast", "Synopsis", "URL"]
    
    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for movie in movies:
            # Clean dictionary keys to only write the expected ones
            row = {key: movie.get(key, "") for key in fields}
            writer.writerow(row)
            
    print(f"Successfully saved {len(movies)} movies to {filepath}")

def main():
    parser = argparse.ArgumentParser(description="IMDb Top 250 Movie Rating Scraper")
    parser.add_argument("--no-headless", action="store_true", help="Run browser in visible mode")
    parser.add_argument("--output", default="data/imdb_top250.csv", help="Path to save output CSV file")
    parser.add_argument("--deep-limit", type=int, default=10, help="Number of movies to deeply scrape for Cast, Genre, and Synopsis details")
    
    args = parser.parse_args()
    
    start_time = time.time()
    driver = None
    try:
        driver = setup_driver(headless=not args.no_headless)
        movies = scrape_imdb_top250(driver)
        
        if movies:
            # Deep scrape a subset of movies based on the deep-limit argument
            limit = min(args.deep_limit, len(movies))
            if limit > 0:
                print(f"Starting deep scraping for top {limit} movies...")
                for i in range(limit):
                    movie = movies[i]
                    print(f"\n[{i+1}/{limit}] Title: {movie['Title']}")
                    if movie["URL"]:
                        details = scrape_movie_detail(driver, movie["URL"])
                        movie.update(details)
                        # Polite delay to prevent rate-limiting/blocking
                        time.sleep(1)
                    else:
                        print("No URL found for this movie. Skipping detail page.")
            
            save_to_csv(movies, args.output)
        else:
            print("No movies scraped. Please check the page selectors or your connection.")
            
    except Exception as e:
        print(f"An error occurred during execution: {e}")
        
    finally:
        if driver:
            print("Closing browser driver...")
            driver.quit()
            
    duration = time.time() - start_time
    print(f"Process finished in {duration:.2f} seconds.")

if __name__ == "__main__":
    main()
