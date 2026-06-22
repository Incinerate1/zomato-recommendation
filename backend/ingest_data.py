import sqlite3
import pandas as pd
from datasets import load_dataset

def clean_rate(rate_str):
    if rate_str is None:
        return None
    rate_str = str(rate_str).strip()
    if rate_str in ('NEW', '-', ''):
        return None
    # Extract rating part (e.g. '4.1/5' -> 4.1, '3.8 /5' -> 3.8)
    if '/' in rate_str:
        rate_str = rate_str.split('/')[0].strip()
    try:
        return float(rate_str)
    except ValueError:
        return None

def clean_cost(cost_str):
    if cost_str is None:
        return None
    cost_str = str(cost_str).strip().replace(",", "")
    if cost_str == '':
        return None
    try:
        return float(cost_str)
    except ValueError:
        return None

def get_budget_category(cost):
    if cost is None:
        return 'medium'  # Fallback default
    if cost <= 400:
        return 'low'
    elif cost <= 800:
        return 'medium'
    else:
        return 'high'

def main():
    print("Downloading Zomato dataset from Hugging Face...")
    try:
        # Load the dataset
        dataset = load_dataset("ManikaSaini/zomato-restaurant-recommendation")
        # Limit to 5000 rows to keep DB size small for GitHub
        df = dataset['train'].to_pandas().head(5000)
        
        print(f"Dataset downloaded successfully. Found {len(df)} records.")
        
        # Drop any completely null rows to be safe.
        df.dropna(how='all', inplace=True)
        
        # Normalize original column names for processing
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        
        print("Cleaning and transforming dataset...")
        
        # Create cleaned and normalized columns
        df['name_clean'] = df['name'].fillna('').astype(str).str.strip()
        df['location_clean'] = df['location'].fillna('').astype(str).str.strip().str.lower()
        df['cuisines_clean'] = df['cuisines'].fillna('').astype(str).str.strip().str.lower()
        
        # Rename original cost column to avoid parens in column name if possible, but keep for compatibility
        df['cost_float'] = df['approx_cost(for_two_people)'].apply(clean_cost)
        df['rate_float'] = df['rate'].apply(clean_rate)
        
        # Add budget tier
        df['budget'] = df['cost_float'].apply(get_budget_category)
        
        # Connect to SQLite
        db_path = 'zomato.db'
        conn = sqlite3.connect(db_path)
        
        print(f"Saving data to SQLite database ({db_path})...")
        # Save to SQLite table named 'restaurants'
        df.to_sql('restaurants', conn, if_exists='replace', index=False)
        
        # Create indexes for optimized querying
        cursor = conn.cursor()
        print("Creating indexes on location, cuisines, rate_float, and budget...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON restaurants(location_clean)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_budget ON restaurants(budget)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate ON restaurants(rate_float)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cuisines ON restaurants(cuisines_clean)")
        
        conn.commit()
        print("Data ingestion and indexing complete!")
        conn.close()
        
    except Exception as e:
        print(f"An error occurred during ingestion: {e}")

if __name__ == "__main__":
    main()
