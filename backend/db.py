import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'zomato.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def search_restaurants(location=None, cuisine=None, budget=None, min_rating=None, limit=10):
    """
    Search restaurants matching strict filters.
    Results are ordered by rate_float descending, then votes descending to get the best candidates.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            name, 
            address, 
            location, 
            cuisines, 
            [approx_cost(for_two_people)] as approx_cost, 
            rate, 
            votes, 
            rest_type, 
            cost_float, 
            rate_float, 
            budget
        FROM restaurants
        WHERE 1=1
    """
    params = []
    
    if location:
        query += " AND location_clean = ?"
        params.append(location.strip().lower())
        
    if cuisine:
        # Search for cuisine within the comma-separated list
        query += " AND cuisines_clean LIKE ?"
        params.append(f"%{cuisine.strip().lower()}%")
        
    if budget:
        query += " AND budget = ?"
        params.append(budget.strip().lower())
        
    if min_rating is not None:
        query += " AND rate_float >= ?"
        params.append(float(min_rating))
        
    # Sort by rating (highest first) and popularity (votes count)
    query += " ORDER BY rate_float DESC, votes DESC LIMIT ?"
    params.append(limit)
    
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert sqlite3.Row objects to dictionaries
        results = [dict(row) for row in rows]
        return results
    except Exception as e:
        print(f"Database query error: {e}")
        return []
    finally:
        conn.close()

def get_unique_locations():
    """Returns a list of all unique locations in the database for validation or UI drop-downs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT location FROM restaurants WHERE location IS NOT NULL AND location != '' ORDER BY location")
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching locations: {e}")
        return []
    finally:
        conn.close()

def get_unique_cuisines():
    """Returns a list of all unique cuisines in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT cuisines FROM restaurants WHERE cuisines IS NOT NULL AND cuisines != ''")
        cuisines_set = set()
        for row in cursor.fetchall():
            parts = [c.strip() for c in row[0].split(',')]
            cuisines_set.update(parts)
        return sorted(list(cuisines_set))
    except Exception as e:
        print(f"Error fetching cuisines: {e}")
        return []
    finally:
        conn.close()
