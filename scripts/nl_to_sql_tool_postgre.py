import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox, ttk, filedialog, Menu
import psycopg2
import json
import re
import csv
import openai
from openai import OpenAI
from datetime import date

# Initialize OpenAI client with API key
client = OpenAI(api_key="your_openai_api_key")


# Global variables to store connection details and schema
postgres_connection_details = {}
schema = {}
latest_result_list = []  # To store the results of the last executed query
query_history = []  # To store the history of queries, explanations, and results
showing_results = False  # Flag to track the current view state
latest_sql_query = ""  # Store the latest SQL query
latest_explanation = ""  # Store the latest explanation
latest_user_query = ""  # Store the latest user natural language query

class SchemaEntryDialog(simpledialog.Dialog):
    """
    A dialog for manually entering a database schema.

    Allows users to input table names, columns, types, and modes.
    """
    def __init__(self, parent):
        self.schema = {}  # Dictionary to store the schema
        super().__init__(parent, title="Enter Database Schema")

    def body(self, master):
        """
        Creates the dialog body with input fields for schema entry.
        """
        tk.Label(master, text="Table Name:").grid(row=0)
        self.table_name = tk.Entry(master)
        self.table_name.grid(row=0, column=1)

        tk.Label(master, text="Column Name:").grid(row=1)
        self.column_name = tk.Entry(master)
        self.column_name.grid(row=1, column=1)

        tk.Label(master, text="Column Type:").grid(row=2)
        self.column_type = tk.Entry(master)
        self.column_type.grid(row=2, column=1)

        tk.Label(master, text="Column Mode:").grid(row=3)
        self.column_mode = tk.Entry(master)
        self.column_mode.grid(row=3, column=1)

        self.columns = []  # List to store columns
        self.columns_display = tk.Listbox(master, height=5)
        self.columns_display.grid(row=4, columnspan=2)

        tk.Button(master, text="Add Column", command=self.add_column).grid(row=5, columnspan=2)
        return self.table_name

    def add_column(self):
        """
        Adds a column to the schema based on user input.
        """
        column_name = self.column_name.get().strip()
        column_type = self.column_type.get().strip()
        column_mode = self.column_mode.get().strip()
        if column_name and column_type and column_mode:
            if column_type.upper() == "RECORD":
                nested_dialog = NestedColumnDialog(self)
                if nested_dialog.nested_columns:
                    self.columns.append((column_name, column_type, nested_dialog.nested_columns, column_mode))
                    self.columns_display.insert(tk.END, f"{column_name} ({column_type}) MODE({column_mode})")
            else:
                self.columns.append((column_name, column_type, column_mode))
                self.columns_display.insert(tk.END, f"{column_name} ({column_type}) MODE({column_mode})")
            self.column_name.delete(0, tk.END)
            self.column_type.delete(0, tk.END)
            self.column_mode.delete(0, tk.END)
        else:
            messagebox.showwarning("Invalid input", "Column name, type, and mode are required")

    def apply(self):
        """
        Finalizes the schema entry and stores it in the schema dictionary.
        """
        table_name = self.table_name.get().strip()
        if table_name and self.columns:
            self.schema[table_name] = self.columns
        else:
            messagebox.showerror("Invalid input", "Table name and at least one column are required")

# Dialog class for entering nested columns in a RECORD type
class NestedColumnDialog(simpledialog.Dialog):
    """
    A dialog for entering nested columns in a RECORD type.

    Allows users to input nested columns, types, and modes.
    """
    def __init__(self, parent):
        self.nested_columns = []  # List to store nested columns
        super().__init__(parent, title="Enter Nested Columns")

    def body(self, master):
        """
        Creates the dialog body with input fields for nested columns.
        """
        tk.Label(master, text="Nested Column Name:").grid(row=0)
        self.nested_column_name = tk.Entry(master)
        self.nested_column_name.grid(row=0, column=1)

        tk.Label(master, text="Nested Column Type:").grid(row=1)
        self.nested_column_type = tk.Entry(master)
        self.nested_column_type.grid(row=1, column=1)

        tk.Label(master, text="Nested Column Mode:").grid(row=2)
        self.nested_column_mode = tk.Entry(master)
        self.nested_column_mode.grid(row=2, column=1)

        self.nested_columns_display = tk.Listbox(master, height=5)
        self.nested_columns_display.grid(row=3, columnspan=2)

        tk.Button(master, text="Add Nested Column", command=self.add_nested_column).grid(row=4, columnspan=2)
        return self.nested_column_name

    def add_nested_column(self):
        """
        Adds a nested column to the RECORD type based on user input.
        """
        nested_column_name = self.nested_column_name.get().strip()
        nested_column_type = self.nested_column_type.get().strip()
        nested_column_mode = self.nested_column_mode.get().strip()
        if nested_column_name and nested_column_type and nested_column_mode:
            self.nested_columns.append((nested_column_name, nested_column_type, nested_column_mode))
            self.nested_columns_display.insert(tk.END, f"{nested_column_name} ({nested_column_type}) MODE({nested_column_mode})")
            self.nested_column_name.delete(0, tk.END)
            self.nested_column_type.delete(0, tk.END)
            self.nested_column_mode.delete(0, tk.END)
        else:
            messagebox.showwarning("Invalid input", "Nested column name, type, and mode are required")

# Dialog class for entering a JSON schema
class JSONSchemaDialog(simpledialog.Dialog):
    """
    A dialog for entering a database schema as JSON.

    Allows users to input a table name and JSON schema.
    """
    def __init__(self, parent, title=None):
        self.schema = {}  # Dictionary to store the schema
        super().__init__(parent, title=title)

    def body(self, master):
        """
        Creates the dialog body with input fields for JSON schema entry.
        """
        tk.Label(master, text="Table Name:").grid(row=0)
        self.table_name = tk.Entry(master)
        self.table_name.grid(row=0, column=1)

        tk.Label(master, text="Paste or type your JSON schema:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.json_input = scrolledtext.ScrolledText(master, height=15, width=60)
        self.json_input.grid(row=2, column=0, padx=5, pady=5)

        return self.table_name

    def apply(self):
        """
        Finalizes the JSON schema entry and stores it in the schema dictionary.
        """
        json_text = self.json_input.get("1.0", tk.END).strip()
        table_name = self.table_name.get().strip()
        if json_text and table_name:
            try:
                json_data = json.loads(json_text)
                self.schema = self.parse_json_schema(json_data, table_name)
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Failed to parse JSON schema: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load JSON schema: {e}")

    def parse_json_schema(self, json_data, table_name):
        """
        Parses a JSON schema into the internal format used by the program.

        Parameters:
        - json_data: The JSON schema data.
        - table_name: The name of the table.

        Returns:
        - A dictionary representing the parsed schema.
        """
        def parse_fields(fields):
            columns = []
            for col in fields:
                if col['type'] == 'RECORD':
                    nested_columns = parse_fields(col['fields'])
                    columns.append((col['name'], 'RECORD', nested_columns, col.get('mode', 'NULLABLE')))
                else:
                    columns.append((col['name'], col['type'], col.get('mode', 'NULLABLE')))
            return columns

        parsed_schema = {}
        if isinstance(json_data, list):
            parsed_schema[table_name] = parse_fields(json_data)
        return parsed_schema


def execute_query(sql_query):
    conn = get_postgres_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result_list = [dict(zip(columns, row)) for row in results]
        return result_list
    except Exception as e:
        error_message = str(e)
        if "syntax error" in error_message:
            messagebox.showerror("Query Error", "There was an error with the SQL query: Please check the syntax and try again.")
        elif "relation" in error_message and "does not exist" in error_message:
            messagebox.showerror("Not Found", "The specified table was not found: Please check the names and try again.")
        else:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        return None

def get_postgres_connection():
    global postgres_connection_details
    if not postgres_connection_details:
        postgres_connection_details = {
            'dbname': dbname_entry.get(),
            'user': user_entry.get(),
            'password': password_entry.get(),
            'host': host_entry.get(),
            'port': port_entry.get()
        }
    try:
        conn = psycopg2.connect(**postgres_connection_details)
        return conn
    except Exception as e:
        messagebox.showerror("Connection Error", f"Failed to connect to PostgreSQL: {str(e)}")
        return None

def fetch_postgres_schema():
    conn = get_postgres_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
        """)
        tables = cursor.fetchall()
        for table in tables:
            cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table[0]}'")
            columns = cursor.fetchall()
            schema[table[0]] = [(col[0], col[1]) for col in columns]
        populate_treeview()

def on_execute():
    global latest_sql_query, latest_result_list, showing_results

    # Execute the latest refined SQL query
    result_list = execute_query(latest_sql_query)
    
    if result_list:
        latest_result_list = result_list
        display_results(result_list)

        # Enable export options
        export_results_button.config(state="normal")
        export_results_button.bind("<Button-1>", lambda event: show_export_menu(event, result_list))

        toggle_view_button.config(state="normal", text="Switch")
        showing_results = True

def display_results(result_list):
    if result_list:
        result_output.config(state="normal")
        result_output.delete("1.0", tk.END)
        
        columns = result_list[0].keys()  # Extract column names from the first row
        result_output.insert(tk.END, "\t".join(columns) + "\n")
        
        for row in result_list:
            row_values = [str(row[column]) for column in columns]
            result_output.insert(tk.END, "\t".join(row_values) + "\n")
        
        result_output.config(state="disabled")

def export_results_as_csv(result_list):
    if not result_output.get("1.0", tk.END).strip():
        messagebox.showwarning("No Results", "There are no results to export")
        return
    
    file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    if file_path:
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            columns = result_list[0].keys()
            writer.writerow(columns)  # Write the header row
            
            for row in result_list:
                writer.writerow([row[column] for column in columns])
        
        messagebox.showinfo("Success", "Results exported as CSV successfully")

def export_results_as_json(result_list):
    if not result_output.get("1.0", tk.END).strip():
        messagebox.showwarning("No Results", "There are no results to export")
        return
    
    file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if file_path:
        # Convert any date objects to strings before dumping to JSON
        def convert_dates(obj):
            if isinstance(obj, date):
                return obj.isoformat()
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

        with open(file_path, 'w') as f:
            json.dump(result_list, f, default=convert_dates, indent=4)  # Export the list of dictionaries as JSON with indentation
        
        messagebox.showinfo("Success", "Results exported as JSON successfully")

def show_export_menu(event, result_list):
    export_menu = Menu(root, tearoff=0)
    export_menu.add_command(label="Export as CSV", command=lambda: export_results_as_csv(result_list))
    export_menu.add_command(label="Export as JSON", command=lambda: export_results_as_json(result_list))
    export_menu.post(event.x_root, event.y_root)

def populate_treeview():
    for item in schema_tree.get_children():
        schema_tree.delete(item)
    for table, columns in schema.items():
        table_id = schema_tree.insert('', 'end', text=table)
        add_columns_to_treeview(table_id, columns)

def add_columns_to_treeview(parent, columns):
    for col in columns:
        schema_tree.insert(parent, 'end', text=f"{col[0]} ({col[1]})")

def on_submit():
    global latest_sql_query, latest_explanation, latest_user_query
    latest_user_query = user_input.get()  # Store the original user query
    database_schema = schema_to_text(schema)
    if not database_schema:
        messagebox.showerror("Error", "Please enter the database schema.")
        return
    sql_query, explanation = translate_to_sql(latest_user_query, database_schema)
    latest_sql_query = sql_query
    latest_explanation = explanation
    display_query()

    toggle_view_button.config(state="disabled", text="Switch")

def display_query():
    result_output.config(state="normal")
    result_output.delete("1.0", tk.END)
    result_output.insert(tk.END, f"SQL Query:\n{latest_sql_query}\n\nExplanation:\n{latest_explanation}")
    result_output.config(state="disabled")

def display_results_view():
    if latest_result_list:
        display_results(latest_result_list)

def toggle_view():
    global showing_results
    if showing_results:
        display_query()
    else:
        display_results_view()
    showing_results = not showing_results

def on_feedback():
    global latest_sql_query, latest_explanation, latest_user_query

    feedback = simpledialog.askstring("Feedback", "Please provide feedback to refine the query:")
    if feedback:
        database_schema = schema_to_text(schema)
        # Use the latest SQL query instead of the original natural language query
        sql_query, explanation = translate_to_sql(latest_sql_query, database_schema, feedback)
        latest_sql_query = sql_query
        latest_explanation = explanation

        # Display the updated SQL query and explanation
        display_query()

        toggle_view_button.config(state="normal", text="Switch")

        # Update UI to show refined query
        result_output.config(state="normal")
        result_output.delete("1.0", tk.END)
        result_output.insert(tk.END, f"SQL Query:\n{latest_sql_query}\n\nExplanation:\n{latest_explanation}")
        result_output.config(state="disabled")

def translate_to_sql(user_query, database_schema, feedback=None):
    prompt = f"""
    You are an expert SQL query generator. Translate user questions into SQL queries based on the database schema provided.
    - Use PostgreSQL syntax.
    - Provide the SQL query in a format ready to be executed on PostgreSQL.
    - Provide a brief explanation of the SQL query after the query itself. Write it in the following format: Explanation: [explanation itself]
    - If no table or column satisfies the user's natural language request, return a message indicating that it is not possible to create a query.
    - Access nested fields directly using the dot notation. For example, use details.price to access the price field within the details record.
    - If feedback is provided, use it to refine the query. Specifically, adjust the SQL query to incorporate the feedback provided by the user.
    - While providing the SQL query do not give it in comment block.
    Schema: {database_schema}
    Question: {user_query}
    Feedback: {feedback if feedback else "None"}
    SQL Query:
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are an expert SQL query generator."}, {"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.3,
        stop=["SQL Query:"]
    )
    full_response = response.choices[0].message.content.strip()

    sql_query = full_response.split("Explanation:")[0].strip()
    explanation = full_response.split("Explanation:")[1].strip() if "Explanation:" in full_response else "No explanation provided."
    
    sql_query = sql_query.strip()
    
    update_query_history(user_query, sql_query, explanation)
    return sql_query, explanation

def update_query_history(user_query, sql_query, explanation):
    query_history.append((user_query, sql_query, explanation))

def show_context_menu(event):
    context_menu.post(event.x_root, event.y_root)

def schema_to_text(schema):
    def columns_to_text(columns):
        column_texts = []
        for col in columns:
            column_texts.append(f"{col[0]} {col[1]}")
        return ', '.join(column_texts)

    schema_text = "Tables:\n"
    for table, columns in schema.items():
        schema_text += f"- {table} ({columns_to_text(columns)})\n"
    return schema_text

def on_schema_entry():
    """
    Opens the manual schema entry dialog and updates the schema in the program.
    """
    dialog = SchemaEntryDialog(root)
    if dialog.schema:
        global schema
        schema.update(dialog.schema)
        schema_display.config(state="normal")
        schema_display.delete("1.0", tk.END)
        schema_display.insert(tk.END, schema_to_text(schema))
        schema_display.config(state="disabled")
        populate_treeview()

def add_json_schema_as_text():
    """
    Opens the JSON schema entry dialog and adds the schema to the program.
    """
    dialog = JSONSchemaDialog(root, title="Add JSON Schema")
    if dialog.schema:
        global schema
        schema.update(dialog.schema)
        schema_display.config(state='normal')
        schema_display.delete('1.0', tk.END)
        schema_display.insert(tk.END, schema_to_text(schema))
        schema_display.config(state='disabled')
        populate_treeview()

def show_tables():
    """
    Displays the tables and columns in the schema in a separate window.
    """
    tables_window = tk.Toplevel(root)
    tables_window.title("Tables")

    tree = ttk.Treeview(tables_window, columns=("Column", "Type", "Mode"), show="headings")
    tree.heading("Column", text="Column")
    tree.heading("Type", text="Type")
    tree.heading("Mode", text="Mode")
    tree.pack(fill=tk.BOTH, expand=True)

    for table, columns in schema.items():
        table_id = tree.insert("", "end", text=table, values=(table, "", ""))
        for col in columns:
            if col[1] == 'RECORD':
                add_nested_columns(tree, table_id, col[2])
            else:
                tree.insert(table_id, "end", values=(col[0], col[1], col[2]))

def add_nested_columns(tree, parent, columns):
    """
    Adds nested columns to a specific column in the Treeview.

    Parameters:
    - tree: The Treeview widget.
    - parent: The parent Treeview item (column).
    - columns: The nested columns to add under the parent column.
    """
    for col in columns:
        if col[1] == 'RECORD':
            col_id = tree.insert(parent, "end", values=(col[0], col[1], col[3]))
            add_nested_columns(tree, col_id, col[2])
        else:
            tree.insert(parent, "end", values=(col[0], col[1], col[2]))

def save_schema():
    """
    Saves the current schema to a JSON file.
    """
    file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, 'w') as f:
            json.dump(schema, f)
        messagebox.showinfo("Success", "Schema saved successfully")

# Function to load a schema from a JSON file and update the UI
def load_schema():
    """
    Loads a schema from a JSON file and updates the UI.
    """
    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, 'r') as f:
            loaded_schema = json.load(f)
            global schema
            schema = loaded_schema
            schema_display.config(state='normal')
            schema_display.delete("1.0", tk.END)
            schema_display.insert(tk.END, schema_to_text(schema))
            schema_display.config(state='disabled')
            populate_treeview()
        messagebox.showinfo("Success", "Schema loaded successfully")

# Function to open the query history window
def open_query_history():
    """
    Opens a new window displaying the query history.
    """
    history_window = tk.Toplevel(root)
    history_window.title("Query History")

    listbox = tk.Listbox(history_window, height=20, width=100)
    listbox.pack(fill=tk.BOTH, expand=True)

    for user_query, sql_query, explanation in query_history:
        listbox.insert(tk.END, f"Query: {user_query}\nSQL: {sql_query}\nExplanation: {explanation}\n")

    listbox.bind("<Double-1>", lambda event: on_history_select(event, listbox))

def on_history_select(event, listbox):
    """
    Handles the selection of a query from the query history list.

    Parameters:
    - event: The event object from the listbox.
    - listbox: The listbox widget containing the query history.
    """
    selection = listbox.curselection()
    if selection:
        index = selection[0]
        user_query, sql_query, explanation = query_history[index]
        user_input.delete(0, tk.END)
        user_input.insert(0, user_query)
        global latest_sql_query, latest_explanation, latest_result_list, showing_results
        latest_sql_query = sql_query
        latest_explanation = explanation
        latest_result_list = None

        display_query()
        toggle_view_button.config(state="disabled", text="Switch")
        showing_results = False

root = tk.Tk()
root.title("Natural Language to SQL Translator")

tk.Label(root, text="Host:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
host_entry = tk.Entry(root, width=50)
host_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

tk.Label(root, text="Port:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
port_entry = tk.Entry(root, width=50)
port_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

tk.Label(root, text="Username:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
user_entry = tk.Entry(root, width=50)
user_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

tk.Label(root, text="Password:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
password_entry = tk.Entry(root, show="*", width=50)
password_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

tk.Label(root, text="Database Name:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
dbname_entry = tk.Entry(root, width=50)
dbname_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

fetch_schema_button = tk.Button(root, text="Fetch Schema", command=fetch_postgres_schema)
fetch_schema_button.grid(row=5, column=1, padx=5, pady=5, sticky="e")

tk.Label(root, text="Database Schema:").grid(row=6, column=0, padx=5, pady=5, sticky="nw")
schema_tree = ttk.Treeview(root, height=10)
schema_tree.grid(row=6, column=1, padx=5, pady=5, sticky="nsew")

# Create the hidden scrolledtext widget to retain the existing logic
schema_display = scrolledtext.ScrolledText(root, height=10, width=70, state="disabled")
schema_display.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")
schema_display.grid_remove()  # Hide the widget

add_schema_button = tk.Button(root, text="Add Schema", command=on_schema_entry)
add_schema_button.grid(row=7, column=0, padx=5, pady=5, sticky="w")

add_schema_button_JSON = tk.Button(root, text="Add Schema as JSON", command=add_json_schema_as_text)
add_schema_button_JSON.grid(row=7, column=1, padx=5, pady=5, sticky="e")

small_button = tk.Button(root, text="...")
small_button.grid(row=7, column=2, padx=5, pady=5, sticky="e")
small_button.bind("<Button-1>", show_context_menu)

context_menu = Menu(root, tearoff=0)
context_menu.add_command(label="Show Tables", command=show_tables)
context_menu.add_command(label="Save Schema", command=save_schema)
context_menu.add_command(label="Load Schema", command=load_schema)

tk.Label(root, text="Enter your question:").grid(row=8, column=0, padx=5, pady=5, sticky="w")
user_input = tk.Entry(root, width=70)
user_input.grid(row=8, column=1, padx=5, pady=5, sticky="ew")

submit_button = tk.Button(root, text="Submit", command=on_submit)
submit_button.grid(row=9, column=1, padx=5, pady=5, sticky="e")

feedback_button = tk.Button(root, text="Provide Feedback", command=on_feedback)
feedback_button.grid(row=9, column=0, padx=5, pady=5, sticky="w")

tk.Label(root, text="Results:").grid(row=10, column=0, padx=5, pady=5, sticky="nw")
result_output = scrolledtext.ScrolledText(root, height=15, width=70, state="disabled")
result_output.grid(row=10, column=1, padx=5, pady=5, sticky="nsew")

export_results_button = tk.Button(root, text="Export Results", state="disabled")
export_results_button.grid(row=11, column=0, padx=5, pady=5, sticky="w")

execute_button = tk.Button(root, text="Execute on Database", command=on_execute)
execute_button.grid(row=11, column=1, padx=5, pady=5, sticky="e")

toggle_view_button = tk.Button(root, text="Switch", command=toggle_view, state="disabled")
toggle_view_button.grid(row=12, column=1, padx=5, pady=5, sticky="e")

query_history_button = tk.Button(root, text="Query History", command=open_query_history)
query_history_button.grid(row=12, column=0, padx=5, pady=5, sticky="w")

root.mainloop()
