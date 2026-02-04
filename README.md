# Strike-Estate Data Linkage Tool

A GUI application for linking Hungarian agricultural strike data (1905-1907) with estate data (1895) using LLM-based matching. The tool uses AI to intelligently match strike records to historical estates by analyzing settlement names, owner/renter information, and historical naming variations.

## Features

- **Dual Table View**: Browse strikes and matched estates side-by-side with proportional column widths
- **LLM-Powered Matching**: Uses OpenAI's GPT models (including gpt-5) to intelligently match strikes to estates
- **Model Selection**: Choose from multiple OpenAI models (gpt-5, gpt-4o, o1, etc.) via dropdown menu
- **Manual & Auto Mode**: Process records one-by-one or automatically iterate through unprocessed strikes
- **Customizable Prompts**: Edit the LLM prompt on the fly for better matching accuracy
- **Reasoning Capture**: LLM explanations are saved alongside matches with model name prefix
- **Checkbox Selection**: Fine-tune matches by checking/unchecking estates before saving
- **Double-Click Editing**: View and edit full cell content in a large, readable window
- **Persistent Storage**: All changes (matches, reasoning, edits) are immediately saved to CSV
- **Non-Blocking API Calls**: GUI remains responsive during slow API requests (threaded)
- **Comprehensive Logging**: Full API request/response logged to console for debugging
- **Auto-Skip**: Play mode automatically skips rows that already have matches
- **County Filtering**: Estates are automatically filtered by county from strike data
- **Sortable Columns**: Double-click estate table headers to sort alphabetically
- **Reset Function**: Clear matches and reasoning, restore full county estate list

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Data files in the `data/` folder:
  - `strikes_with_names_raw.csv` (strike records)
  - `transdanubia_estates.csv` (estate records)

## Installation

1. **Clone or download** this repository

2. **Install required Python packages**:
   ```bash
   pip install pandas openai tkinter
   ```
   
   Or if you have a requirements.txt:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up OpenAI API key**:
   
   Get an API key from https://platform.openai.com/api-keys
   
   Then set the environment variable:
   
   **Windows (Command Prompt)**:
   ```cmd
   set OPENAI_API_KEY=your-api-key-here
   ```
   
   **Windows (PowerShell)**:
   ```powershell
   $env:OPENAI_API_KEY="your-api-key-here"
   ```
   
   **Linux/Mac**:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```
   
   *Note*: Set this each time you open a new terminal, or add it to your system environment variables permanently.

4. **Verify data files** exist in `data/` folder:
   - `data/strikes_with_names_raw.csv`
   - `data/transdanubia_estates.csv`

## Running the Application

```bash
python estate_lookup_gui.py
```

The GUI window will open with two main tables and control buttons.

## Usage Guide

### Basic Workflow

1. **Select a strike row**: Click any row in the "Strikes Data" table (top)
   - If the row has existing matches (gt_ids), matched estates appear below
   - Otherwise, all estates from that county are shown

2. **Perform LLM lookup**: Click "Lookup" button (or press 'L')
   - The selected model queries the LLM with strike and estate data
   - Matched estates appear in the "Matched Estates" table with checkboxes
   - Reasoning is displayed in the right panel and saved with model name prefix

3. **Review and adjust**: 
   - Check/uncheck estates as needed
   - Click checkbox header (✓) to toggle all
   - Double-click estate headers to sort by column

4. **Save matches**: Click "Save" button (or press 'S')
   - Only checked estates are saved as gt_ids
   - Immediately written to CSV file

5. **Navigate**: Use "Up" (U) and "Down" (D) buttons to move between strikes

### Auto-Play Mode (Batch Processing)

Process multiple unprocessed strikes automatically:

1. **Select starting row** (optional - defaults to first row)
2. **Click "▶ Play"** (or press 'P')
3. The tool will:
   - Process only strikes without gt_ids (skips completed rows)
   - Query the LLM for each strike
   - Auto-save to CSV every 10 rows
   - Continue until stopped or all unprocessed strikes are done
4. **Click "⬛ sTop"** (or press 'T') to pause anytime

### Viewing/Editing Cell Content

Double-click any cell in the Strikes Data table to:
- View full content in a large, scrollable text window (700x400)
- Edit the content if needed
- Click "Save to CSV" to immediately write changes to the CSV file
- Or click "Close (no save)" to cancel

This is especially useful for the `reasoning` column which can contain long explanations.

### Model Selection

Use the "Model:" dropdown to choose:
- **gpt-5** - Latest, most capable (slower, more expensive)
- **gpt-5-mini** - Faster gpt-5 variant
- **gpt-4o** - Fast and smart
- **gpt-4o-mini** - Cost-effective default
- **o1**, **o1-mini** - Reasoning models
- **gpt-4-turbo** - Older but reliable
- **gpt-3.5-turbo** - Fastest, cheapest

Each model's name is prefixed to the reasoning output (e.g., "GPT-5: Settlement matches...").

### Resetting Matches

Click "Reset" button (or press 'E') to:
- Clear gt_ids and reasoning for the selected strike
- Save changes to CSV
- Restore full county estate list (unchecked)

Useful for starting over when LLM makes mistakes.

### Customizing the Prompt

The left text panel contains the LLM prompt:
- Edit it to improve matching logic
- Variables like `{county}`, `{settlement}`, `{owner_renter}` are replaced with actual data
- The prompt emphasizes **location matching** over owner name matching
- Click in the prompt to edit (hotkeys temporarily disabled while typing)
- Click outside to re-enable hotkeys

## Keyboard Shortcuts

- **L** - Lookup (perform LLM query)
- **S** - Save matches
- **U** - Up (previous strike)
- **D** - Down (next strike)
- **R** - Reload data from disk
- **P** - Play (start auto-play)
- **T** - sTop (stop auto-play)
- **E** - Reset matches

*Shortcuts are disabled while typing in the prompt box.*

## Data Format

### Strikes Data (`data/strikes_with_names_raw.csv`)

**Required columns**:
- `year` - Strike year (e.g., 1905)
- `date` - Strike date
- `county` - County name (used for filtering estates)
- `settlement` - Settlement/village name (primary matching factor)
- `owner_renter` - Owner or renter name (secondary matching factor)
- `striketype` - Type of strike
- `strike_id` - Unique strike identifier

**Auto-created columns**:
- `gt_ids` - JSON array of matched estate IDs, e.g., `["11003", "11005"]`
- `reasoning` - LLM explanation with model prefix, e.g., "GPT-5: Settlement 'Bellye' matches..."

**File format**: CSV with `;` (semicolon) separator, UTF-8 encoding

### Estates Data (`data/transdanubia_estates.csv`)

**Required columns**:
- `gt_id` - Unique estate identifier (used for matching)
- `county` - County name (must match strikes data)
- `settlement` - Estate settlement name
- `owner_name` - Owner's name
- `renter_name` - Renter's name (if applicable)

**Optional columns**: district, owner_occupation, renter_occupation, etc.

**File format**: CSV with standard comma separator, UTF-8 encoding

## Matching Logic

The LLM prompt prioritizes:

1. **Settlement/Location Match (Highest Priority)**:
   - Exact matches or historical name variants
   - Handles Hungarian place name changes (1895 → 1905-1907)
   - Phonetic matches, merged settlements, spelling variations

2. **Owner/Renter Name Match (Secondary)**:
   - Estate ownership could transfer within families
   - Same family name but different first name still counts as strong match
   - Noble title variations (gr., hg., fhg.)

3. **Conservative Approach**: Prefers false negatives over false positives

## Logging and Debugging

All API communication is logged to the console:
- Full request messages (system + user prompt)
- Model name and parameters (temperature, etc.)
- Complete response text
- Parsing results and extracted gt_ids/reasoning

This helps debug matching issues and understand LLM behavior.

## GUI Remains Responsive

API calls run in background threads, so:
- You can scroll, click, and navigate during API requests
- Status label shows "API call in progress (non-blocking)..."
- Especially important for slow models like gpt-5

## Cost Considerations

- **gpt-4o-mini**: Most cost-effective (~$0.15 per 1000 strikes)
- **gpt-5**: Most expensive but best accuracy (~$15 per 1000 strikes)
- Auto-play adds 1-second delay between requests (avoid rate limits)
- Auto-saves every 10 rows (minimize data loss if interrupted)

## Troubleshooting

**"OpenAI client not configured" error**:
- Make sure you set the `OPENAI_API_KEY` environment variable
- Restart the terminal after setting it
- Check the key is correct: https://platform.openai.com/api-keys

**GUI freezes during lookup**:
- This shouldn't happen (calls are threaded)
- If it does, check console for error messages
- Try a different model

**Columns are too wide/narrow**:
- Columns are auto-sized based on data (90th percentile)
- Capped at 20% of screen width
- Restart the app to recalculate after data changes

**Wrong matches**:
- Edit the prompt to emphasize location or owner names
- Try a more capable model (gpt-5 vs gpt-4o-mini)
- Use Reset button to clear and try again
- Manually uncheck incorrect estates before saving

**CSV file corrupted**:
- The app always uses UTF-8 encoding and `;` separator for strikes
- Make backup copies before bulk operations
- Use Reload button to reload from disk if in-memory data is wrong

## Technical Notes

- Column names are aggressively cleaned (remove newlines, tabs, spaces)
- Threading uses daemon threads with `root.after()` for GUI updates
- CSV writes use `lineterminator='\n'` for consistency
- Estate table sorting preserves checkbox states
- Double-click dialog uses Consolas font for monospace display
- All changes are written immediately to CSV (no "Save All" needed)

## License

[Add your license here]

## Contact

[Add contact information or repository link here]
