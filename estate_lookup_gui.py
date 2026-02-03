import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pandas as pd
import os
from pathlib import Path
import json

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
            self.strikes_df = self.strikes_df.fillna('')
            
            # Add gt_ids column if it doesn't exist
            if 'gt_ids' not in self.strikes_df.columns:
                self.strikes_df['gt_ids'] = ''
            
            # Load estates data
            self.estates_df = pd.read_csv(self.estates_path, dtype=str)
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
        
        # Configure columns
        for col in strikes_columns:
            self.strikes_tree.heading(col, text=col)
            self.strikes_tree.column(col, width=100)
        
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
        
        # === SECTION 3: Prompt Text Box ===
        prompt_label = ttk.Label(main_frame, text="LLM Prompt", font=('Arial', 12, 'bold'))
        prompt_label.grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        
        self.prompt_text = scrolledtext.ScrolledText(main_frame, height=8, wrap=tk.WORD)
        self.prompt_text.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Default prompt
        default_prompt = """You are a historical data matching assistant. Your task is to link strike data to estate data.

Given a strike record with the following information:
- Year: {year}
- Date: {date}
- County: {county}
- Settlement: {settlement}
- Owner/Renter: {owner_renter}
- Strike Type: {striketype}

And a list of estates in the same county ({county}), identify which estate(s) are most likely associated with this strike.

Return your answer as a JSON list of gt_id values, e.g.: ["11003", "11005"]
If no clear match exists, return an empty list: []

Consider:
1. Owner/renter name similarities
2. Settlement location matches
3. Historical context and naming variations

Estates in {county}:
{estates_json}

Return ONLY the JSON list of gt_id values, nothing else."""
        
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
        
        self.up_btn = ttk.Button(button_frame, text="Up", command=self.go_to_previous, underline=0)
        self.up_btn.grid(row=0, column=2, padx=5)
        
        self.down_btn = ttk.Button(button_frame, text="Down", command=self.go_to_next, underline=0)
        self.down_btn.grid(row=0, column=3, padx=5)
        
        self.reload_btn = ttk.Button(button_frame, text="Reload", command=self.reload_data, underline=0)
        self.reload_btn.grid(row=0, column=4, padx=5)
        
        self.play_btn = ttk.Button(button_frame, text="▶ Play", command=self.start_auto_play, underline=2)
        self.play_btn.grid(row=0, column=5, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="⬛ sTop", command=self.stop_auto_play, state='disabled', underline=2)
        self.stop_btn.grid(row=0, column=6, padx=5)
        
        # Status label
        self.status_label = ttk.Label(button_frame, text="Ready", foreground="green")
        self.status_label.grid(row=0, column=7, padx=20)
        
        # Bind keyboard shortcuts (store for later unbinding)
        self.hotkeys_enabled = True
        self.enable_hotkeys()
    
    def populate_strikes_table(self):
        """Populate the strikes table with data"""
        # Clear existing items
        for item in self.strikes_tree.get_children():
            self.strikes_tree.delete(item)
        
        # Add rows
        for idx, row in self.strikes_df.iterrows():
            values = [row[col] for col in self.strikes_df.columns]
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
        """Handle double-click on strike to edit it"""
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
        current_value = self.strikes_df.at[strike_idx, col_name]
        
        # Create edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit {col_name}")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Label
        label = ttk.Label(dialog, text=f"Edit {col_name}:")
        label.pack(pady=(20, 5), padx=20)
        
        # Entry field
        entry = ttk.Entry(dialog, width=50)
        entry.insert(0, current_value)
        entry.pack(pady=5, padx=20)
        entry.focus()
        entry.select_range(0, tk.END)
        
        # Save function
        def save_edit():
            new_value = entry.get()
            self.strikes_df.at[strike_idx, col_name] = new_value
            self.populate_strikes_table()
            # Re-select the edited row
            self.strikes_tree.selection_set(str(strike_idx))
            self.status_label.config(text="Strike data updated", foreground="green")
            dialog.destroy()
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15)
        
        save_btn = ttk.Button(button_frame, text="Save", command=save_edit)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to save
        entry.bind('<Return>', lambda e: save_edit())
        entry.bind('<Escape>', lambda e: dialog.destroy())
    
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
    
    def on_strike_selected(self, event):
        """Handle strike row selection"""
        selection = self.strikes_tree.selection()
        if not selection:
            return
        
        self.selected_strike_idx = int(selection[0])
        strike_row = self.strikes_df.iloc[self.selected_strike_idx]
        
        # If gt_ids already exist, display those estates
        if strike_row['gt_ids']:
            self.display_estates_by_ids(strike_row['gt_ids'], strike_row['county'])
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
        """Perform LLM lookup for the selected strike"""
        if self.selected_strike_idx is None:
            messagebox.showwarning("Warning", "Please select a strike row first")
            return
        
        if not self.client:
            messagebox.showerror("Error", "OpenAI client not configured. Please install openai package and set OPENAI_API_KEY environment variable.")
            return
        
        self.status_label.config(text="Looking up...", foreground="orange")
        self.root.update()
        
        try:
            gt_ids = self.perform_llm_lookup(self.selected_strike_idx)
            
            if gt_ids:
                strike_row = self.strikes_df.iloc[self.selected_strike_idx]
                self.display_estates_by_ids(json.dumps(gt_ids), strike_row['county'])
                self.status_label.config(text=f"Found {len(gt_ids)} matches", foreground="green")
            else:
                self.status_label.config(text="No matches found", foreground="blue")
        
        except Exception as e:
            messagebox.showerror("Error", f"Lookup failed: {str(e)}")
            self.status_label.config(text="Lookup failed", foreground="red")
    
    def perform_llm_lookup(self, strike_idx):
        """Perform the actual LLM lookup"""
        strike_row = self.strikes_df.iloc[strike_idx]
        county = strike_row['county']
        
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
        
        # Call OpenAI API
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a historical data matching assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        # Parse response
        result_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON from response
        try:
            # Remove markdown code blocks if present
            if result_text.startswith('```'):
                lines = result_text.split('\n')
                result_text = '\n'.join(lines[1:-1])
            
            gt_ids = json.loads(result_text)
            
            # Update the strikes dataframe
            if isinstance(gt_ids, list):
                self.strikes_df.at[strike_idx, 'gt_ids'] = json.dumps(gt_ids)
                return gt_ids
            else:
                return []
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract IDs from text
            import re
            ids = re.findall(r'"(\d+)"', result_text)
            if ids:
                self.strikes_df.at[strike_idx, 'gt_ids'] = json.dumps(ids)
                return ids
            return []
    
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
            if checked_gt_ids:
                self.strikes_df.at[self.selected_strike_idx, 'gt_ids'] = json.dumps(checked_gt_ids)
            else:
                self.strikes_df.at[self.selected_strike_idx, 'gt_ids'] = ''
            
            # Save to CSV
            self.strikes_df.to_csv(self.strikes_path, sep=';', index=False)
            
            # Refresh the table to show updated gt_ids
            self.populate_strikes_table()
            
            # Update status (no popup)
            self.status_label.config(text=f"Saved {len(checked_gt_ids)} matches", foreground="green")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
            self.status_label.config(text="Save failed", foreground="red")
    
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
        if strike_row['gt_ids']:
            self.display_estates_by_ids(strike_row['gt_ids'], strike_row['county'])
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
        if strike_row['gt_ids']:
            self.display_estates_by_ids(strike_row['gt_ids'], strike_row['county'])
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
            
            # Display results
            if gt_ids:
                strike_row = self.strikes_df.iloc[self.current_auto_idx]
                self.display_estates_by_ids(json.dumps(gt_ids), strike_row['county'])
            
            # Auto-save every 10 rows
            if (self.current_auto_idx + 1) % 10 == 0:
                self.strikes_df.to_csv(self.strikes_path, sep=';', index=False)
            
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
