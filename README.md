# Strike-Estate Data Linkage Tool

A GUI application for linking agricultural strike data (1905-1907) with estate data (1895) using LLM-based matching.

## Features

- **Dual Table View**: Browse strikes and matched estates side-by-side
- **LLM-Powered Matching**: Uses OpenAI's GPT models to intelligently match strikes to estates
- **Manual & Auto Mode**: Process records one-by-one or automatically iterate through all
- **Customizable Prompts**: Edit the LLM prompt on the fly for better matching
- **Persistent Storage**: Save matches directly to CSV with gt_ids column

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up OpenAI API**:
   - Get an API key from https://platform.openai.com/api-keys
   - Set environment variable:
     ```bash
     # Windows (Command Prompt)
     set OPENAI_API_KEY=your-api-key-here
     
     # Windows (PowerShell)
     $env:OPENAI_API_KEY="your-api-key-here"
     
     # Linux/Mac
     export OPENAI_API_KEY=your-api-key-here
     ```

3. **Run the application**:
   ```bash
   python estate_lookup_gui.py
   ```

## Usage

### Manual Mode

1. **Select a strike**: Click on any row in the "Strikes Data" table
   - If the row already has matches (gt_ids), they'll be displayed in the "Matched Estates" table
   - Otherwise, all estates from the same county will be shown

2. **Perform lookup**: Click the "Lookup" button
   - The LLM will analyze the strike data and county estates
   - Matched estates will appear in the bottom table

3. **Save matches**: Click "Save" to write the gt_ids to the CSV file

### Auto-Play Mode

1. Click on a strike row to set the starting point (or start from row 1)
2. Click "▶ Play" to begin automatic processing
3. The tool will:
   - Process each strike sequentially
   - Query the LLM for matches
   - Auto-save every 10 rows
   - Continue until stopped or all rows are processed
4. Click "⬛ Stop" to pause processing at any time

### Customizing the Prompt

- The prompt text box contains the default LLM instruction
- Edit it as needed to improve matching accuracy
- Variables like `{county}`, `{owner_renter}`, etc. will be replaced with actual data
- The prompt should instruct the LLM to return a JSON list of gt_id values

## Data Format

### Strikes Data (`strikes_with_names_raw.csv`)
- Columns: year, date, county, settlement, owner_renter, striketype, strike_id, gt_ids
- The `gt_ids` column stores matches (created automatically if missing)

### Estates Data (`transdanubia_estates.csv`)
- Columns: gt_id, within_id, county, settlement, district, renter_name, renter_occupation, renter_status, owner_name
- The `gt_id` is the unique identifier used for matching

## Notes

- The tool uses `gpt-4o-mini` by default (cost-effective)
- Auto-play includes a 1-second delay between requests to avoid rate limits
- Matches are stored as JSON arrays, e.g., `["11003", "11005"]`
- The original CSV separator (`;`) is preserved when saving
