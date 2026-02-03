import pandas as pd

# Load the CSV
df = pd.read_csv('data/strikes_with_names_raw.csv', sep=';', dtype=str, encoding='utf-8')

# Clean ALL column names aggressively
new_columns = []
for col in df.columns:
    clean_name = str(col).strip().replace('\n', '').replace('\r', '').replace('\t', '').replace(' ', '_')
    new_columns.append(clean_name)
    print(f"Column: {repr(col)} -> {repr(clean_name)}")

df.columns = new_columns

# Add reasoning column if it doesn't exist
if 'reasoning' not in df.columns:
    df['reasoning'] = ''
    print("Added reasoning column")

# Fill NaN with empty string
df = df.fillna('')

# Save with clean parameters
df.to_csv('data/strikes_with_names_raw.csv', sep=';', index=False, encoding='utf-8', lineterminator='\n')

print(f"\nSaved CSV with columns: {df.columns.tolist()}")
print(f"Shape: {df.shape}")
