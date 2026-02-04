import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pandas as pd
import os
from pathlib import Path
import json
import threading

# Try to import OpenAI - user will need to install and configure
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class EstateLookupGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Strike-Estate Data Linkage Tool")
        self.root.geometry("1400x900")
        
        # Data paths
        self.data_dir = Path(__file__).parent / "data"
        self.strikes_path = self.data_dir / "strikes_with_names_raw.csv"
        self.estates_path = self.data_dir / "transdanubia_estates.csv"
        
        # Load data
        self.load_data()
        
        # State variables
        self.selected_strike_idx = None
        self.auto_play_running = False
        self.current_auto_idx = 0
        self.estate_checkboxes = {}  # Track checkbox states by item id
        
        # Initialize OpenAI client if available
        self.client = None
        if OPENAI_AVAILABLE:
            try:
                self.client = OpenAI()  # Will use OPENAI_API_KEY env variable
            except:
                pass
        
        # Create GUI
        self.create_widgets()
        
    def load_data(self):
        """Load CSV data files"""
        try:
            # Load strikes data
            self.strikes_df = pd.read_csv(self.strikes_path, sep=';', dtype=str)
            
            # Aggressively clean column names - remove ALL whitespace including newlines, tabs, etc
            # This handles columns that might already exist with bad names
            cleaned_columns = {}
            for col in self.strikes_df.columns:
                clean_col = col.strip().replace('\n', '').replace('\r', '').replace('\t', '').replace(' ', '_')
                cleaned_columns[col] = clean_col
            
            self.strikes_df.rename(columns=cleaned_columns, inplace=True)
            self.strikes_df = self.strikes_df.fillna('')
            
            # Force add gt_ids column if it doesn't exist
            if 'gt_ids' not in self.strikes_df.columns:
                self.strikes_df['gt_ids'] = ''
            
            # Force add reasoning column if it doesn't exist  
            if 'reasoning' not in self.strikes_df.columns:
                self.strikes_df['reasoning'] = ''
            
            # Load estates data with explicit encoding
            self.estates_df = pd.read_csv(self.estates_path, dtype=str, encoding='utf-8', skipinitialspace=True)
            
            # Aggressively clean column names for estates too
            cleaned_columns = {}
            for col in self.estates_df.columns:
                clean_col = col.strip().replace('\n', '').replace('\r', '').replace('\t', '').replace(' ', '_')
                cleaned_columns[col] = clean_col
            
            self.estates_df.rename(columns=cleaned_columns, inplace=True)
            self.estates_df = self.estates_df.fillna('')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data files: {str(e)}")
            raise
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=2)
        main_frame.rowconfigure(3, weight=2)
        main_frame.rowconfigure(5, weight=1)
        
        # === SECTION 1: Strikes Table ===
        strikes_label = ttk.Label(main_frame, text="Strikes Data", font=('Arial', 12, 'bold'))
        strikes_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Strikes table frame
        strikes_frame = ttk.Frame(main_frame)
        strikes_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        strikes_frame.columnconfigure(0, weight=1)
        strikes_frame.rowconfigure(0, weight=1)
        
        # Create Treeview for strikes
        strikes_columns = list(self.strikes_df.columns)
        self.strikes_tree = ttk.Treeview(strikes_frame, columns=strikes_columns, show='headings', height=10)
        
        # Calculate proportional widths that fit screen
        available_width = 1350  # Approximate available width in pixels
        max_col_width = int(available_width * 0.2)  # Cap at 20% of screen
        col_widths = {}
        
        for col in strikes_columns:
            # Get all lengths in this column
            lengths = [len(str(col))]  # Include header
            lengths.extend([len(str(val)) for val in self.strikes_df[col]])
            
            # Use 90th percentile to avoid outliers
            lengths.sort()
            percentile_90_idx = int(len(lengths) * 0.9)
            representative_len = lengths[percentile_90_idx]
            
            col_widths[col] = max(representative_len, 5)  # Minimum 5 chars
        
        # Scale proportionally to fit available width
        total_width = sum(col_widths.values())
        final_col_widths = {}
        for col in strikes_columns:
            proportional_width = int((col_widths[col] / total_width) * available_width)
            # Apply 20% cap and 40px minimum
            final_width = max(min(proportional_width, max_col_width), 40)
            final_col_widths[col] = final_width
            self.strikes_tree.heading(col, text=col)
            self.strikes_tree.column(col, width=final_width)
        
        # Store column widths for later use in text wrapping
        self.strikes_col_widths = final_col_widths
        
        # Add scrollbars
        strikes_vsb = ttk.Scrollbar(strikes_frame, orient="vertical", command=self.strikes_tree.yview)
        strikes_hsb = ttk.Scrollbar(strikes_frame, orient="horizontal", command=self.strikes_tree.xview)
        self.strikes_tree.configure(yscrollcommand=strikes_vsb.set, xscrollcommand=strikes_hsb.set)
        
        # Grid layout
        self.strikes_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        strikes_vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        strikes_hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Populate strikes table
        self.populate_strikes_table()
        
        # Bind selection event
        self.strikes_tree.bind('<<TreeviewSelect>>', self.on_strike_selected)
        # Bind double-click for editing
        self.strikes_tree.bind('<Double-Button-1>', self.on_strike_double_click)
        
        # === SECTION 2: Estates Table ===
        estates_label = ttk.Label(main_frame, text="Matched Estates", font=('Arial', 12, 'bold'))
        estates_label.grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        
        # Estates table frame
        estates_frame = ttk.Frame(main_frame)
        estates_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        estates_frame.columnconfigure(0, weight=1)
        estates_frame.rowconfigure(0, weight=1)
        
        # Create Treeview for estates with checkbox column
        estates_columns = ['✓'] + list(self.estates_df.columns)
        self.estates_tree = ttk.Treeview(estates_frame, columns=estates_columns, show='headings', height=10)
        
        # Configure columns
        self.estates_tree.heading('✓', text='✓')
        self.estates_tree.column('✓', width=30, anchor='center')
        for col in self.estates_df.columns:
            self.estates_tree.heading(col, text=col)
            self.estates_tree.column(col, width=120)
        
        # Add scrollbars
        estates_vsb = ttk.Scrollbar(estates_frame, orient="vertical", command=self.estates_tree.yview)
        estates_hsb = ttk.Scrollbar(estates_frame, orient="horizontal", command=self.estates_tree.xview)
        self.estates_tree.configure(yscrollcommand=estates_vsb.set, xscrollcommand=estates_hsb.set)
        
        # Grid layout
        self.estates_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        estates_vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        estates_hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Bind click event to toggle checkboxes
        self.estates_tree.bind('<Button-1>', self.on_estate_click)
        
        # Bind double-click on headers for sorting
        self.estates_tree.bind('<Double-Button-1>', self.on_estate_header_double_click)
        
        # Track current sort state
        self.estates_sort_column = None
        self.estates_sort_reverse = False
        
        # === SECTION 3: Prompt Text Box (Split into two columns) ===
        prompt_label = ttk.Label(main_frame, text="LLM Prompt", font=('Arial', 12, 'bold'))
        prompt_label.grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        
        # Create a frame to hold both text boxes side by side
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        text_frame.columnconfigure(0, weight=1)
        text_frame.columnconfigure(1, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        # Left side: Prompt text box
        prompt_container = ttk.Frame(text_frame)
        prompt_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        prompt_container.columnconfigure(0, weight=1)
        prompt_container.rowconfigure(0, weight=1)
        
        self.prompt_text = scrolledtext.ScrolledText(prompt_container, height=8, wrap=tk.WORD)
        self.prompt_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right side: LLM Response log
        response_container = ttk.Frame(text_frame)
        response_container.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        response_container.columnconfigure(0, weight=1)
        response_container.rowconfigure(0, weight=1)
        
        response_label = ttk.Label(response_container, text="LLM Response", font=('Arial', 10, 'bold'))
        response_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 2))
        
        self.response_text = scrolledtext.ScrolledText(response_container, height=8, wrap=tk.WORD, state='disabled', bg='#f0f0f0')
        self.response_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        response_container.rowconfigure(1, weight=1)
        
        # Default prompt
        default_prompt = """You are a historical data matching assistant specializing in Hungarian agricultural history. Your task is to link strike data from 1905-1907 to estate data from 1895.

Given a strike record with the following information:
- Year: {year}
- County: {county}
- Settlement: {settlement}
- Owner/Renter: {owner_renter}

And a list of estates in the same county ({county}) from 1895, identify which estate(s) are most likely associated with this strike.

MATCHING PRIORITY (in order of importance):
1. **SETTLEMENT/LOCATION MATCH (HIGHEST PRIORITY)**: The settlement name is the most important factor. 
   - Exact matches or clear historical variants of the same place should be prioritized
   - Settlement names may have changed between 1895 and 1905-1907 due to:
     * Name evolution and linguistic changes
     * Settlements merging or splitting
     * Official renaming
     * Changes in spelling conventions
   - Consider: Similar-sounding names (phonetic matches), nearby settlements that may have merged, historical name variants

2. **OWNER/RENTER NAME MATCH (SECONDARY)**: Owner names matter but are less decisive than location
   - Estate ownership could have transferred within families between 1895 and 1905-1907
   - If the settlement matches perfectly but the owner is different within the same family (e.g., Zichy Jenő in 1895 → Zichy Ödön in 1905), this is still a STRONG match
   - A location match with related family names (same surname, different first name) is BETTER than a nearby location with identical owner names
   - Noble titles may be abbreviated differently (gr. = gróf/count, hg. = herceg/duke, fhg. = főherceg/archduke)
   - Family names may appear with or without noble predicates
   - Large landowners often had multiple estates

3. When uncertain, prefer false negatives (no match) over false positives

REQUIRED: You MUST provide a clear chain of reasoning that explains:
- How you linked the strike settlement to the estate settlement(s) (most important factor)
- Any name variations or historical changes you considered for the location
- Why you matched (or didn't match) the owner/renter names (secondary factor)
- Your confidence level in the match

Return your answer as a JSON object with this exact format:
{{
  "gt_ids": ["11003", "11005"],
  "reasoning": "Settlement 'Bellye' from the strike matches estate settlement 'Bellye'. Owner 'fhg. Habsburg Frigyes' matches the estate owner 'Habsburg Frigyes főherceg' (fhg. = főherceg/archduke). High confidence match."
}}

If no clear match exists, return:
{{
  "gt_ids": [],
  "reasoning": "No settlement name match found. Checked phonetic variations and nearby settlements but found no convincing matches for '{settlement}'."
}}

Estates in {county}:
{estates_json}

Return ONLY valid JSON in the format shown above, nothing else."""
        
        self.prompt_text.insert('1.0', default_prompt)
        
        # Bind focus events to disable/enable hotkeys when typing in prompt
        self.prompt_text.bind('<FocusIn>', self.disable_hotkeys)
        self.prompt_text.bind('<FocusOut>', self.enable_hotkeys)
        
        # === SECTION 4: Control Buttons ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.lookup_btn = ttk.Button(button_frame, text="Lookup", command=self.lookup_single, underline=0)
        self.lookup_btn.grid(row=0, column=0, padx=5)
        
        self.save_btn = ttk.Button(button_frame, text="Save", command=self.save_matches, underline=0)
        self.save_btn.grid(row=0, column=1, padx=5)
        
        self.reset_btn = ttk.Button(button_frame, text="Reset", command=self.reset_matches, underline=2)
        self.reset_btn.grid(row=0, column=2, padx=5)
        
        self.up_btn = ttk.Button(button_frame, text="Up", command=self.go_to_previous, underline=0)
        self.up_btn.grid(row=0, column=3, padx=5)
        
        self.down_btn = ttk.Button(button_frame, text="Down", command=self.go_to_next, underline=0)
        self.down_btn.grid(row=0, column=4, padx=5)
        
        self.reload_btn = ttk.Button(button_frame, text="Reload", command=self.reload_data, underline=0)
        self.reload_btn.grid(row=0, column=5, padx=5)
        
        self.play_btn = ttk.Button(button_frame, text="▶ Play", command=self.start_auto_play, underline=2)
        self.play_btn.grid(row=0, column=6, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="⬛ sTop", command=self.stop_auto_play, state='disabled', underline=2)
        self.stop_btn.grid(row=0, column=7, padx=5)
        
        # Model selection dropdown
        model_label = ttk.Label(button_frame, text="Model:")
        model_label.grid(row=0, column=8, padx=(20, 5))
        
        self.model_var = tk.StringVar(value="gpt-5")
        self.model_dropdown = ttk.Combobox(button_frame, textvariable=self.model_var, 
                                           values=["gpt-5", "gpt-5-mini", "gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
                                           state="readonly", width=15)
        self.model_dropdown.grid(row=0, column=9, padx=5)
        
        # Status label
        self.status_label = ttk.Label(button_frame, text="Ready", foreground="green")
        self.status_label.grid(row=0, column=10, padx=20)
        
        # Bind keyboard shortcuts (store for later unbinding)
        self.hotkeys_enabled = True
        self.enable_hotkeys()
    
    def populate_strikes_table(self):
        """Populate the strikes table with data"""
        # Clear existing items
        for item in self.strikes_tree.get_children():
            self.strikes_tree.delete(item)
        
        # Update treeview columns to match dataframe columns
        current_columns = list(self.strikes_df.columns)
        self.strikes_tree['columns'] = current_columns
        
        # Calculate proportional widths that fit screen
        available_width = 1350  # Approximate available width in pixels
        max_col_width = int(available_width * 0.2)  # Cap at 20% of screen
        col_widths = {}
        
        for col in current_columns:
            # Get all lengths in this column
            lengths = [len(str(col))]  # Include header
            lengths.extend([len(str(val)) for val in self.strikes_df[col]])
            
            # Use 90th percentile to avoid outliers
            lengths.sort()
            percentile_90_idx = int(len(lengths) * 0.9)
            representative_len = lengths[percentile_90_idx]
            
            col_widths[col] = max(representative_len, 5)  # Minimum 5 chars
        
        # Scale proportionally to fit available width
        total_width = sum(col_widths.values())
        final_col_widths = {}
        for col in current_columns:
            proportional_width = int((col_widths[col] / total_width) * available_width)
            # Apply 20% cap and 40px minimum
            final_width = max(min(proportional_width, max_col_width), 40)
            final_col_widths[col] = final_width
            self.strikes_tree.heading(col, text=col)
            self.strikes_tree.column(col, width=final_width)
        
        # Store column widths for reference
        self.strikes_col_widths = final_col_widths
        
        # Add rows without wrapping - single line only
        for idx, row in self.strikes_df.iterrows():
            values = [str(row[col]) for col in current_columns]
            self.strikes_tree.insert('', 'end', iid=idx, values=values)
    
    def enable_hotkeys(self, event=None):
        """Enable keyboard shortcuts"""
        if self.hotkeys_enabled:
            return
        self.hotkeys_enabled = True
        self.root.bind('<KeyPress-l>', lambda e: self.lookup_single())
        self.root.bind('<KeyPress-L>', lambda e: self.lookup_single())
        self.root.bind('<KeyPress-s>', lambda e: self.save_matches())
        self.root.bind('<KeyPress-S>', lambda e: self.save_matches())
        self.root.bind('<KeyPress-p>', lambda e: self.start_auto_play())
        self.root.bind('<KeyPress-P>', lambda e: self.start_auto_play())
        self.root.bind('<KeyPress-t>', lambda e: self.stop_auto_play())
        self.root.bind('<KeyPress-T>', lambda e: self.stop_auto_play())
        self.root.bind('<KeyPress-d>', lambda e: self.go_to_next())
        self.root.bind('<KeyPress-D>', lambda e: self.go_to_next())
        self.root.bind('<KeyPress-u>', lambda e: self.go_to_previous())
        self.root.bind('<KeyPress-U>', lambda e: self.go_to_previous())
        self.root.bind('<KeyPress-r>', lambda e: self.reload_data())
        self.root.bind('<KeyPress-R>', lambda e: self.reload_data())
    
    def disable_hotkeys(self, event=None):
        """Disable keyboard shortcuts when typing in prompt"""
        if not self.hotkeys_enabled:
            return
        self.hotkeys_enabled = False
        self.root.unbind('<KeyPress-l>')
        self.root.unbind('<KeyPress-L>')
        self.root.unbind('<KeyPress-s>')
        self.root.unbind('<KeyPress-S>')
        self.root.unbind('<KeyPress-p>')
        self.root.unbind('<KeyPress-P>')
        self.root.unbind('<KeyPress-t>')
        self.root.unbind('<KeyPress-T>')
        self.root.unbind('<KeyPress-d>')
        self.root.unbind('<KeyPress-D>')
        self.root.unbind('<KeyPress-u>')
        self.root.unbind('<KeyPress-U>')
        self.root.unbind('<KeyPress-r>')
        self.root.unbind('<KeyPress-R>')
    
    def on_strike_double_click(self, event):
        """Handle double-click on strike to view/edit cell content"""
        region = self.strikes_tree.identify('region', event.x, event.y)
        if region != 'cell':
            return
        
        item = self.strikes_tree.identify_row(event.y)
        if not item:
            return
        
        column = self.strikes_tree.identify_column(event.x)
        col_idx = int(column.replace('#', '')) - 1
        col_name = self.strikes_df.columns[col_idx]
        
        # Get current value
        strike_idx = int(item)
        current_value = str(self.strikes_df.at[strike_idx, col_name])
        
        # Create view/edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"View/Edit: {col_name} (Row {strike_idx})")
        dialog.geometry("700x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Label
        label = ttk.Label(main_frame, text=f"Column: {col_name}", font=('Arial', 10, 'bold'))
        label.pack(pady=(0, 5), anchor=tk.W)
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, height=15, font=('Consolas', 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert('1.0', current_value)
        text_widget.focus()
        
        # Save function
        def save_edit():
            new_value = text_widget.get('1.0', tk.END).strip()
            # Update dataframe
            self.strikes_df.at[strike_idx, col_name] = new_value
            # Save to CSV immediately
            self.strikes_df.to_csv(self.strikes_path, sep=';', index=False, encoding='utf-8', lineterminator='\n')
            # Refresh the table
            self.populate_strikes_table()
            # Re-select the edited row
            self.strikes_tree.selection_set(str(strike_idx))
            self.strikes_tree.see(str(strike_idx))
            self.status_label.config(text="Changes saved to CSV", foreground="green")
            dialog.destroy()
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        save_btn = ttk.Button(button_frame, text="Save to CSV", command=save_edit)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = ttk.Button(button_frame, text="Close (no save)", command=dialog.destroy)
        close_btn.pack(side=tk.LEFT, padx=5)
        
        # Info label
        info_label = ttk.Label(button_frame, text="Changes will be saved to CSV file", foreground="blue", font=('Arial', 8))
        info_label.pack(side=tk.RIGHT, padx=5)
        
        # Bind Escape key to close
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def reload_data(self):
        """Reload data from CSV files"""
        try:
            self.load_data()
            self.populate_strikes_table()
            
            # Clear estates view
            for item in self.estates_tree.get_children():
                self.estates_tree.delete(item)
            self.estate_checkboxes.clear()
            
            # Reset selection
            self.selected_strike_idx = None
            
            self.status_label.config(text="Data reloaded from disk", foreground="green")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reload data: {str(e)}")
            self.status_label.config(text="Reload failed", foreground="red")
    
    def on_estate_click(self, event):
        """Handle click on estate row or header to toggle checkbox"""
        region = self.estates_tree.identify('region', event.x, event.y)
        column = self.estates_tree.identify_column(event.x)
        
        # Only handle clicks on the checkbox column
        if column != '#1':
            return
        
        # Check if clicking on header
        if region == 'heading':
            self.toggle_all_checkboxes()
            return
        
        if region != 'cell':
            return
        
        item = self.estates_tree.identify_row(event.y)
        if not item:
            return
        
        # Toggle checkbox state
        current_state = self.estate_checkboxes.get(item, False)
        new_state = not current_state
        self.estate_checkboxes[item] = new_state
        
        # Update display
        values = list(self.estates_tree.item(item, 'values'))
        values[0] = '☑' if new_state else '☐'
        self.estates_tree.item(item, values=values)
    
    def toggle_all_checkboxes(self):
        """Toggle all checkboxes on or off"""
        # Check if any checkbox is unchecked
        all_checked = all(self.estate_checkboxes.get(item, False) for item in self.estates_tree.get_children())
        
        # If all are checked, uncheck all. Otherwise, check all.
        new_state = not all_checked
        
        # Update all checkboxes
        for item in self.estates_tree.get_children():
            self.estate_checkboxes[item] = new_state
            values = list(self.estates_tree.item(item, 'values'))
            values[0] = '☑' if new_state else '☐'
            self.estates_tree.item(item, values=values)
    
    def on_estate_header_double_click(self, event):
        """Handle double-click on estate table header to sort"""
        region = self.estates_tree.identify('region', event.x, event.y)
        if region != 'heading':
            return
        
        column = self.estates_tree.identify_column(event.x)
        col_idx = int(column.replace('#', '')) - 1
        
        # Get the column name (accounting for checkbox column)
        if col_idx == 0:
            # Don't sort by checkbox column
            return
        
        col_name = list(self.estates_df.columns)[col_idx - 1]  # -1 because first column is checkbox
        
        # Toggle sort direction if clicking the same column
        if self.estates_sort_column == col_name:
            self.estates_sort_reverse = not self.estates_sort_reverse
        else:
            self.estates_sort_column = col_name
            self.estates_sort_reverse = False
        
        # Get current data from treeview with checkbox states
        current_data = []
        for item in self.estates_tree.get_children():
            values = self.estates_tree.item(item, 'values')
            checkbox_state = self.estate_checkboxes.get(item, False)
            current_data.append((values, checkbox_state))
        
        # Sort the data by the selected column (skip checkbox column)
        sorted_data = sorted(current_data, key=lambda x: str(x[0][col_idx]), reverse=self.estates_sort_reverse)
        
        # Clear and repopulate the treeview
        for item in self.estates_tree.get_children():
            self.estates_tree.delete(item)
        self.estate_checkboxes.clear()
        
        for values, checkbox_state in sorted_data:
            # Update checkbox character based on saved state
            values_list = list(values)
            values_list[0] = '☑' if checkbox_state else '☐'
            item_id = self.estates_tree.insert('', 'end', values=values_list)
            self.estate_checkboxes[item_id] = checkbox_state
    
    def on_strike_selected(self, event):
        """Handle strike row selection"""
        selection = self.strikes_tree.selection()
        if not selection:
            return
        
        self.selected_strike_idx = int(selection[0])
        strike_row = self.strikes_df.iloc[self.selected_strike_idx]
        
        # Ensure gt_ids column exists
        if 'gt_ids' not in self.strikes_df.columns:
            self.strikes_df['gt_ids'] = ''
        
        # If gt_ids already exist, display those estates
        gt_ids_value = strike_row.get('gt_ids', '')
        if gt_ids_value and gt_ids_value != '':
            self.display_estates_by_ids(gt_ids_value, strike_row['county'])
        else:
            # Show all estates from the same county
            self.display_estates_by_county(strike_row['county'])
    
    def display_estates_by_county(self, county):
        """Display all estates from a specific county"""
        # Clear existing items
        for item in self.estates_tree.get_children():
            self.estates_tree.delete(item)
        self.estate_checkboxes.clear()
        
        # Filter estates by county
        county_estates = self.estates_df[self.estates_df['county'] == county]
        
        # Add rows with checkboxes (all checked by default)
        for idx, row in county_estates.iterrows():
            values = ['☐'] + [row[col] for col in self.estates_df.columns]
            item_id = self.estates_tree.insert('', 'end', values=values)
            self.estate_checkboxes[item_id] = False  # Unchecked for county view
        
        self.status_label.config(text=f"Showing {len(county_estates)} estates from {county}")
    
    def display_estates_by_ids(self, gt_ids_str, county):
        """Display estates matching the given gt_ids"""
        # Clear existing items
        for item in self.estates_tree.get_children():
            self.estates_tree.delete(item)
        self.estate_checkboxes.clear()
        
        # Parse gt_ids
        try:
            if gt_ids_str.startswith('['):
                gt_ids = json.loads(gt_ids_str)
            else:
                gt_ids = [id.strip() for id in gt_ids_str.split(',') if id.strip()]
        except:
            gt_ids = []
        
        if not gt_ids:
            self.display_estates_by_county(county)
            return
        
        # Filter estates by gt_ids
        matched_estates = self.estates_df[self.estates_df['gt_id'].isin(gt_ids)]
        
        # Add rows with checkboxes (all checked by default for matched estates)
        for idx, row in matched_estates.iterrows():
            values = ['☑'] + [row[col] for col in self.estates_df.columns]
            item_id = self.estates_tree.insert('', 'end', values=values)
            self.estate_checkboxes[item_id] = True  # Checked by default
        
        self.status_label.config(text=f"Showing {len(matched_estates)} matched estates")
    
    def lookup_single(self):
        """Perform LLM lookup for the selected strike (non-blocking)"""
        if self.selected_strike_idx is None:
            messagebox.showwarning("Warning", "Please select a strike row first")
            return
        
        if not self.client:
            messagebox.showerror("Error", "OpenAI client not configured. Please install openai package and set OPENAI_API_KEY environment variable.")
            return
        
        print("\n" + "#"*80)
        print("### STARTING API CALL (non-blocking) ###")
        print("#"*80 + "\n")
        
        self.status_label.config(text="API call in progress (non-blocking)...", foreground="orange")
        self.lookup_btn.config(state='disabled')
        self.root.update_idletasks()  # Force GUI update
        
        # Run the lookup in a separate thread to keep GUI responsive
        def lookup_thread():
            try:
                print("[Thread] Starting LLM lookup...")
                gt_ids = self.perform_llm_lookup(self.selected_strike_idx)
                print("[Thread] LLM lookup completed successfully")
                
                # Update GUI from main thread
                self.root.after(0, self._finish_lookup, gt_ids, None)
            except Exception as e:
                import traceback
                error_details = f"Lookup failed: {type(e).__name__}: {str(e)}\n\nFull traceback:\n{traceback.format_exc()}"
                print("\n=== DETAILED ERROR ===")
                print(error_details)
                print("======================\n")
                self.root.after(0, self._finish_lookup, None, error_details)
        
        thread = threading.Thread(target=lookup_thread, daemon=True)
        thread.start()
        print("[Main thread] API call thread started, GUI remains responsive\n")
    
    def _finish_lookup(self, gt_ids, error):
        """Callback to finish lookup from main thread"""
        self.lookup_btn.config(state='normal')
        
        if error:
            messagebox.showerror("Error", error)
            self.status_label.config(text="Lookup failed", foreground="red")
        elif gt_ids:
            strike_row = self.strikes_df.iloc[self.selected_strike_idx]
            self.display_estates_by_ids(json.dumps(gt_ids), strike_row['county'])
            self.status_label.config(text=f"Found {len(gt_ids)} matches", foreground="green")
        else:
            self.status_label.config(text="No matches found", foreground="blue")

    
    def perform_llm_lookup(self, strike_idx):
        """Perform the actual LLM lookup"""
        # Ensure required columns exist
        if 'gt_ids' not in self.strikes_df.columns:
            self.strikes_df['gt_ids'] = ''
        if 'reasoning' not in self.strikes_df.columns:
            self.strikes_df['reasoning'] = ''
        
        print("\n=== DEBUG: perform_llm_lookup called ===")
        print(f"Strike index: {strike_idx}")
        print(f"Strikes df shape: {self.strikes_df.shape}")
        print(f"Strikes columns: {self.strikes_df.columns.tolist()}")
        
        try:
            print("Getting strike_row with iloc...")
            strike_row = self.strikes_df.iloc[strike_idx]
            print(f"Strike row type: {type(strike_row)}")
            print(f"Strike row index: {strike_row.index.tolist()}")
            print("\nAttempting to access 'county' column...")
            county = strike_row['county']
            print(f"County value: {county}")
            
            # Get all estates from the same county
            county_estates = self.estates_df[self.estates_df['county'] == county]
            
            # Prepare estates data for prompt
            estates_list = []
            for idx, estate in county_estates.iterrows():
                estates_list.append({
                    'gt_id': estate['gt_id'],
                    'settlement': estate['settlement'],
                    'owner_name': estate['owner_name'],
                    'renter_name': estate['renter_name']
                })
        except KeyError as e:
            raise Exception(f"Column not found in dataframe: {str(e)}. Available columns: {', '.join(self.estates_df.columns.tolist())}")
        
        # Format prompt
        prompt = self.prompt_text.get('1.0', tk.END).strip()
        prompt = prompt.format(
            year=strike_row['year'],
            date=strike_row['date'],
            county=county,
            settlement=strike_row['settlement'],
            owner_renter=strike_row['owner_renter'],
            striketype=strike_row['striketype'],
            estates_json=json.dumps(estates_list, ensure_ascii=False, indent=2)
        )
        
        # Get selected model
        selected_model = self.model_var.get()
        
        # Prepare system message
        system_msg = "You are a historical data matching assistant specializing in Hungarian agricultural history. Use careful reasoning to match strike records to estates, considering historical place name changes and noble title variations. Return only valid JSON."
        
        # Log the API request with FULL details
        print("\n" + "="*80)
        print(f"=== API REQUEST to {selected_model} ===")
        print("="*80)
        
        # Call OpenAI API with model-specific parameters
        if selected_model.startswith('o1'):
            # o1 models don't support system messages or temperature
            # Combine system message with user prompt
            full_prompt = f"{system_msg}\n\n{prompt}"
            messages = [{"role": "user", "content": full_prompt}]
            print("\nMESSAGE [0]:")
            print(f"  Role: user")
            print(f"  Content length: {len(full_prompt)} characters")
            print(f"\n--- FULL CONTENT START ---")
            print(full_prompt)
            print("--- FULL CONTENT END ---\n")
            
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=messages
            )
        elif selected_model == 'gpt-5' or selected_model == 'gpt-5-mini':
            # gpt-5 doesn't support temperature parameter
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ]
            print("\nMESSAGE [0] (system):")
            print(f"  Content length: {len(system_msg)} characters")
            print(f"\n--- SYSTEM MESSAGE START ---")
            print(system_msg)
            print("--- SYSTEM MESSAGE END ---\n")
            
            print("\nMESSAGE [1] (user):")
            print(f"  Content length: {len(prompt)} characters")
            print(f"\n--- USER PROMPT START ---")
            print(prompt)
            print("--- USER PROMPT END ---\n")
            
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=messages
            )
        else:
            # Other models (gpt-4o, gpt-4-turbo, gpt-3.5-turbo) support temperature
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ]
            print("\nMESSAGE [0] (system):")
            print(f"  Content length: {len(system_msg)} characters")
            print(f"\n--- SYSTEM MESSAGE START ---")
            print(system_msg)
            print("--- SYSTEM MESSAGE END ---\n")
            
            print("\nMESSAGE [1] (user):")
            print(f"  Content length: {len(prompt)} characters")
            print(f"\n--- USER PROMPT START ---")
            print(prompt)
            print("--- USER PROMPT END ---\n")
            
            print(f"Temperature: 0.2\n")
            
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=0.2
            )
        
        print("\n" + "="*80)
        print("=== API RESPONSE ===")
        print("="*80)
        
        # Parse response
        result_text = response.choices[0].message.content.strip()
        print(f"\nResponse length: {len(result_text)} characters")
        print(f"\n--- FULL RESPONSE START ---")
        print(result_text)
        print("--- FULL RESPONSE END ---")
        print("\n" + "="*80 + "\n")
        
        # Display the raw response in the response text box
        self.response_text.config(state='normal')
        self.response_text.delete('1.0', tk.END)
        self.response_text.insert('1.0', f"=== RAW LLM RESPONSE ===\n\n{result_text}\n\n=== END RESPONSE ===")
        self.response_text.config(state='disabled')
        
        # Try to extract JSON from response
        try:
            # Remove markdown code blocks if present (more robust)
            cleaned_text = result_text.strip()
            
            # Check for code block markers and remove them
            if cleaned_text.startswith('```'):
                # Find the end of the first line (e.g., ```json or just ```)
                first_newline = cleaned_text.find('\n')
                if first_newline != -1:
                    cleaned_text = cleaned_text[first_newline + 1:]
                else:
                    # No newline after ```, just remove the ```
                    cleaned_text = cleaned_text[3:]
            
            # Remove trailing code block marker if present
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3].strip()
            
            result_json = json.loads(cleaned_text)
            
            # Extract gt_ids and reasoning
            if isinstance(result_json, dict):
                gt_ids = result_json.get('gt_ids', [])
                reasoning = result_json.get('reasoning', '')
                
                # Ensure gt_ids is a list
                if not isinstance(gt_ids, list):
                    gt_ids = []
                    reasoning = f'Invalid gt_ids format: {type(gt_ids).__name__}. ' + reasoning
                
                # Prepend model name to reasoning
                model_name = selected_model.upper()
                reasoning = f"{model_name}: {reasoning}"
                    
                # Update response text with parsing success
                self.response_text.config(state='normal')
                current = self.response_text.get('1.0', tk.END)
                self.response_text.insert(tk.END, f"\n\n=== PARSED ===\ngt_ids: {gt_ids}\nreasoning: {reasoning}")
                self.response_text.config(state='disabled')
            elif isinstance(result_json, list):
                # Fallback: old format compatibility
                gt_ids = result_json
                model_name = selected_model.upper()
                reasoning = f'{model_name}: No reasoning provided (old format)'
                
                # Update response text
                self.response_text.config(state='normal')
                self.response_text.insert(tk.END, f"\n\n=== PARSED (old format) ===\ngt_ids: {gt_ids}")
                self.response_text.config(state='disabled')
            else:
                gt_ids = []
                model_name = selected_model.upper()
                reasoning = f'{model_name}: Invalid response format: {type(result_json).__name__}'
                
                # Update response text
                self.response_text.config(state='normal')
                self.response_text.insert(tk.END, f"\n\n=== PARSING ERROR ===\n{reasoning}")
                self.response_text.config(state='disabled')
            
            # Update the strikes dataframe with both gt_ids and reasoning
            # Ensure columns exist before assignment
            if 'gt_ids' not in self.strikes_df.columns:
                self.strikes_df['gt_ids'] = ''
            if 'reasoning' not in self.strikes_df.columns:
                self.strikes_df['reasoning'] = ''
            
            # Now safely assign values using iat for position-based access
            gt_ids_col_idx = self.strikes_df.columns.get_loc('gt_ids')
            reasoning_col_idx = self.strikes_df.columns.get_loc('reasoning')
            
            self.strikes_df.iat[strike_idx, gt_ids_col_idx] = json.dumps(gt_ids) if gt_ids else ''
            self.strikes_df.iat[strike_idx, reasoning_col_idx] = str(reasoning)
            return gt_ids
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract IDs from text
            import re
            ids = re.findall(r'"(\d+)"', result_text)
            
            # Update response text with error
            self.response_text.config(state='normal')
            self.response_text.insert(tk.END, f"\n\n=== JSON PARSE ERROR ===\n{str(e)}\nExtracted IDs: {ids}")
            self.response_text.config(state='disabled')
            
            # Ensure columns exist
            if 'gt_ids' not in self.strikes_df.columns:
                self.strikes_df['gt_ids'] = ''
            if 'reasoning' not in self.strikes_df.columns:
                self.strikes_df['reasoning'] = ''
            
            gt_ids_col_idx = self.strikes_df.columns.get_loc('gt_ids')
            reasoning_col_idx = self.strikes_df.columns.get_loc('reasoning')
            
            model_name = selected_model.upper()
            
            if ids:
                self.strikes_df.iat[strike_idx, gt_ids_col_idx] = json.dumps(ids)
                self.strikes_df.iat[strike_idx, reasoning_col_idx] = f'{model_name}: JSON parse error - extracted IDs from text: {str(e)}'
                return ids
            self.strikes_df.iat[strike_idx, gt_ids_col_idx] = ''
            self.strikes_df.iat[strike_idx, reasoning_col_idx] = f'{model_name}: Parse error: {str(e)}. Response: {result_text[:200]}'
            return []
        except Exception as e:
            # Catch any other errors
            # Update response text with error
            self.response_text.config(state='normal')
            self.response_text.insert(tk.END, f"\n\n=== UNEXPECTED ERROR ===\n{type(e).__name__}: {str(e)}")
            self.response_text.config(state='disabled')
            
            if 'gt_ids' not in self.strikes_df.columns:
                self.strikes_df['gt_ids'] = ''
            if 'reasoning' not in self.strikes_df.columns:
                self.strikes_df['reasoning'] = ''
            
            gt_ids_col_idx = self.strikes_df.columns.get_loc('gt_ids')
            reasoning_col_idx = self.strikes_df.columns.get_loc('reasoning')
            
            model_name = selected_model.upper()
            
            self.strikes_df.iat[strike_idx, gt_ids_col_idx] = ''
            self.strikes_df.iat[strike_idx, reasoning_col_idx] = f'{model_name}: Unexpected error: {str(e)}'
            raise
    
    def reset_matches(self):
        """Reset matches for the selected strike and show all county estates"""
        if self.selected_strike_idx is None:
            messagebox.showwarning("Warning", "Please select a strike row first")
            return
        
        try:
            strike_row = self.strikes_df.iloc[self.selected_strike_idx]
            county = strike_row['county']
            
            # Clear gt_ids and reasoning for this row
            if 'gt_ids' in self.strikes_df.columns:
                gt_ids_col_idx = self.strikes_df.columns.get_loc('gt_ids')
                self.strikes_df.iat[self.selected_strike_idx, gt_ids_col_idx] = ''
            
            if 'reasoning' in self.strikes_df.columns:
                reasoning_col_idx = self.strikes_df.columns.get_loc('reasoning')
                self.strikes_df.iat[self.selected_strike_idx, reasoning_col_idx] = ''
            
            # Save to CSV
            self.strikes_df.to_csv(self.strikes_path, sep=';', index=False, encoding='utf-8', lineterminator='\n')
            
            # Refresh the strikes table
            self.populate_strikes_table()
            
            # Re-select the row
            self.strikes_tree.selection_set(str(self.selected_strike_idx))
            self.strikes_tree.see(str(self.selected_strike_idx))
            
            # Display all estates from the county
            self.display_estates_by_county(county)
            
            self.status_label.config(text="Matches reset", foreground="green")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset: {str(e)}")
            self.status_label.config(text="Reset failed", foreground="red")
    
    def save_matches(self):
        """Save the current matches to CSV (only checked estates)"""
        if self.selected_strike_idx is None:
            messagebox.showwarning("Warning", "Please select a strike row first")
            return
        
        try:
            # Get only checked estates
            checked_gt_ids = []
            for item_id, is_checked in self.estate_checkboxes.items():
                if is_checked:
                    values = self.estates_tree.item(item_id, 'values')
                    if len(values) > 1:  # Skip checkbox column
                        gt_id = values[1]  # gt_id is the first column after checkbox
                        checked_gt_ids.append(gt_id)
            
            # Update the strikes dataframe with only checked IDs
            # Ensure column exists
            if 'gt_ids' not in self.strikes_df.columns:
                self.strikes_df['gt_ids'] = ''
            
            gt_ids_col_idx = self.strikes_df.columns.get_loc('gt_ids')
            
            if checked_gt_ids:
                self.strikes_df.iat[self.selected_strike_idx, gt_ids_col_idx] = json.dumps(checked_gt_ids)
            else:
                self.strikes_df.iat[self.selected_strike_idx, gt_ids_col_idx] = ''
            
            # Save to CSV with explicit parameters to prevent corruption
            self.strikes_df.to_csv(self.strikes_path, sep=';', index=False, encoding='utf-8', lineterminator='\n')
            
            # Refresh the table to show updated gt_ids
            self.populate_strikes_table()
            
            # Update status (no popup)
            self.status_label.config(text=f"Saved {len(checked_gt_ids)} matches", foreground="green")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
            self.status_label.config(text="Save failed", foreground="red")
    
    def reset_matches(self):
        """Reset matches for the selected strike and show all county estates"""
        if self.selected_strike_idx is None:
            messagebox.showwarning("Warning", "Please select a strike row first")
            return
        
        try:
            strike_row = self.strikes_df.iloc[self.selected_strike_idx]
            county = strike_row['county']
            
            # Clear gt_ids and reasoning for this row
            if 'gt_ids' in self.strikes_df.columns:
                gt_ids_col_idx = self.strikes_df.columns.get_loc('gt_ids')
                self.strikes_df.iat[self.selected_strike_idx, gt_ids_col_idx] = ''
            
            if 'reasoning' in self.strikes_df.columns:
                reasoning_col_idx = self.strikes_df.columns.get_loc('reasoning')
                self.strikes_df.iat[self.selected_strike_idx, reasoning_col_idx] = ''
            
            # Save to CSV
            self.strikes_df.to_csv(self.strikes_path, sep=';', index=False, encoding='utf-8', lineterminator='\n')
            
            # Refresh the strikes table
            self.populate_strikes_table()
            
            # Re-select the row
            self.strikes_tree.selection_set(str(self.selected_strike_idx))
            self.strikes_tree.see(str(self.selected_strike_idx))
            
            # Display all estates from the county
            self.display_estates_by_county(county)
            
            self.status_label.config(text="Matches reset", foreground="green")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset: {str(e)}")
            self.status_label.config(text="Reset failed", foreground="red")
    
    def go_to_next(self):
        """Move to the next row in strikes table"""
        if self.selected_strike_idx is None:
            # If nothing selected, select first row
            next_idx = 0
        else:
            next_idx = self.selected_strike_idx + 1
        
        # Check bounds
        if next_idx >= len(self.strikes_df):
            self.status_label.config(text="Already at last row", foreground="blue")
            return
        
        # Select and show the row
        self.strikes_tree.selection_set(str(next_idx))
        self.strikes_tree.see(str(next_idx))
        self.selected_strike_idx = next_idx
        
        # Trigger the selection event
        strike_row = self.strikes_df.iloc[next_idx]
        gt_ids_value = strike_row.get('gt_ids', '') if 'gt_ids' in self.strikes_df.columns else ''
        if gt_ids_value and gt_ids_value != '':
            self.display_estates_by_ids(gt_ids_value, strike_row['county'])
        else:
            self.display_estates_by_county(strike_row['county'])
    
    def go_to_previous(self):
        """Move to the previous row in strikes table"""
        if self.selected_strike_idx is None:
            self.status_label.config(text="No row selected", foreground="blue")
            return
        
        prev_idx = self.selected_strike_idx - 1
        
        # Check bounds
        if prev_idx < 0:
            self.status_label.config(text="Already at first row", foreground="blue")
            return
        
        # Select and show the row
        self.strikes_tree.selection_set(str(prev_idx))
        self.strikes_tree.see(str(prev_idx))
        self.selected_strike_idx = prev_idx
        
        # Trigger the selection event
        strike_row = self.strikes_df.iloc[prev_idx]
        gt_ids_value = strike_row.get('gt_ids', '') if 'gt_ids' in self.strikes_df.columns else ''
        if gt_ids_value and gt_ids_value != '':
            self.display_estates_by_ids(gt_ids_value, strike_row['county'])
        else:
            self.display_estates_by_county(strike_row['county'])
    
    def start_auto_play(self):
        """Start automatic iteration through strikes"""
        if not self.client:
            messagebox.showerror("Error", "OpenAI client not configured. Please install openai package and set OPENAI_API_KEY environment variable.")
            return
        
        self.auto_play_running = True
        self.play_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.lookup_btn.config(state='disabled')
        
        # Start from selected row or first row
        if self.selected_strike_idx is not None:
            self.current_auto_idx = self.selected_strike_idx
        else:
            self.current_auto_idx = 0
        
        self.status_label.config(text="Auto-play running...", foreground="orange")
        
        # Start processing
        self.root.after(100, self.process_next_strike)
    
    def stop_auto_play(self):
        """Stop automatic iteration"""
        self.auto_play_running = False
        self.play_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.lookup_btn.config(state='normal')
        self.status_label.config(text="Auto-play stopped", foreground="blue")
    
    def process_next_strike(self):
        """Process the next strike in auto-play mode"""
        if not self.auto_play_running or self.current_auto_idx >= len(self.strikes_df):
            self.stop_auto_play()
            if self.current_auto_idx >= len(self.strikes_df):
                messagebox.showinfo("Complete", "All strikes processed!")
            return
        
        # Skip rows that already have gt_ids (non-empty)
        while self.current_auto_idx < len(self.strikes_df):
            current_gt_ids = self.strikes_df.iloc[self.current_auto_idx]['gt_ids']
            # Check if gt_ids is empty or just whitespace
            if not current_gt_ids or str(current_gt_ids).strip() == '':
                break  # Found a row without gt_ids
            # Skip this row, move to next
            self.current_auto_idx += 1
        
        # Check again if we've reached the end after skipping
        if self.current_auto_idx >= len(self.strikes_df):
            self.stop_auto_play()
            messagebox.showinfo("Complete", "All unprocessed strikes completed!")
            return
        
        # Select current row
        self.strikes_tree.selection_set(str(self.current_auto_idx))
        self.strikes_tree.see(str(self.current_auto_idx))
        self.selected_strike_idx = self.current_auto_idx
        
        # Update status
        self.status_label.config(
            text=f"Processing {self.current_auto_idx + 1}/{len(self.strikes_df)}...",
            foreground="orange"
        )
        self.root.update()
        
        try:
            # Perform lookup
            gt_ids = self.perform_llm_lookup(self.current_auto_idx)
            
            # Refresh the strikes table to show updated gt_ids and reasoning
            self.populate_strikes_table()
            
            # Re-select the current row after refresh
            self.strikes_tree.selection_set(str(self.current_auto_idx))
            self.strikes_tree.see(str(self.current_auto_idx))
            
            # Display results
            if gt_ids:
                strike_row = self.strikes_df.iloc[self.current_auto_idx]
                self.display_estates_by_ids(json.dumps(gt_ids), strike_row['county'])
            
            # Auto-save every 10 rows
            if (self.current_auto_idx + 1) % 10 == 0:
                self.strikes_df.to_csv(self.strikes_path, sep=';', index=False, encoding='utf-8', lineterminator='\n')
            
            # Move to next
            self.current_auto_idx += 1
            
            # Schedule next iteration
            self.root.after(1000, self.process_next_strike)  # 1 second delay
        
        except Exception as e:
            self.status_label.config(text=f"Error at row {self.current_auto_idx}: {str(e)}", foreground="red")
            self.stop_auto_play()
            messagebox.showerror("Error", f"Processing failed at row {self.current_auto_idx}: {str(e)}")

def main():
    root = tk.Tk()
    app = EstateLookupGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
