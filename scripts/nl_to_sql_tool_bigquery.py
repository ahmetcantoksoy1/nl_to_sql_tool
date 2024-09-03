import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox, ttk, filedialog, Menu
from google.cloud import bigquery
import json
import re
import csv
import os
import openai
from openai import OpenAI

# Initialize OpenAI client with API key
client = OpenAI(api_key="your_openai_api_key")

# Set Google application credentials environment variable for BigQuery
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/path/to/your/credentials.json'

# Global variables to store dataset name and project ID
global_dataset_name = ""
global_project_id = ""

# Function to execute the SQL query on BigQuery and return the results
def execute_query(sql_query):
    """
    Executes a SQL query on Google BigQuery using the provided dataset name and project ID.

    Parameters:
    - sql_query: The SQL query to execute.

    Returns:
    - A list of dictionaries containing the query results, or None if an error occurs.
    """
    global global_dataset_name, global_project_id
    
    client = bigquery.Client(project=global_project_id)
    sql_query = sql_query.replace("{dataset_name}", global_dataset_name).replace("{project_id}", global_project_id)
    print(f"Executing query: {sql_query}")  # Debug print
    
    try:
        query_job = client.query(sql_query)
        results = query_job.result()
        result_list = []

        for row in results:
            result_list.append(dict(row))  # Convert each row to a dictionary

        return result_list
    except Exception as e:
        # Handle errors and display appropriate messages
        error_message = str(e)
        if "invalidQuery" in error_message:
            messagebox.showerror("Query Error", "There was an error with the SQL query: Please check the syntax and try again.")
        elif "notFound" in error_message:
            messagebox.showerror("Not Found", "The specified dataset or table was not found: Please check the names and try again.")
        else:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        return None

# Function to handle the execution of the latest SQL query
def on_execute():
    """
    Executes the latest SQL query using the provided dataset name and project ID, 
    and displays the results in the UI.
    """
    global global_dataset_name, global_project_id
    global_dataset_name = dataset_entry.get().strip()
    global_project_id = project_entry.get().strip()

    if not global_dataset_name or not global_project_id:
        messagebox.showerror("Error", "Please provide both Dataset Name and Project ID.")
        return

    global latest_sql_query, latest_result_list, showing_results  # Access the global variables
    result_list = execute_query(latest_sql_query)
    
    if result_list:
        latest_result_list = result_list  # Store the result for toggling
        display_results(result_list)

        # Enable the export results button and bind the context menu
        export_results_button.config(state="normal")
        export_results_button.bind("<Button-1>", lambda event: show_export_menu(event, result_list))

        # Enable the toggle view button and set the initial state
        toggle_view_button.config(state="normal", text="Switch")
        showing_results = True  # Set to True initially after execution, so it toggles to query first

# Function to display the query results in the UI
def display_results(result_list):
    """
    Displays the query results in the text area.

    Parameters:
    - result_list: The list of dictionaries containing the query results.
    """
    if result_list:
        result_output.config(state="normal")
        result_output.delete("1.0", tk.END)
        
        columns = result_list[0].keys()  # Extract column names from the first row
        result_output.insert(tk.END, "\t".join(columns) + "\n")
        
        for row in result_list:
            row_values = [str(row[column]) for column in columns]
            result_output.insert(tk.END, "\t".join(row_values) + "\n")
        
        result_output.config(state="disabled")

# Function to export query results as a CSV file
def export_results_as_csv(result_list):
    """
    Exports the query results as a CSV file.

    Parameters:
    - result_list: The list of dictionaries containing the query results.
    """
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

# Function to export query results as a JSON file
def export_results_as_json(result_list):
    """
    Exports the query results as a JSON file.

    Parameters:
    - result_list: The list of dictionaries containing the query results.
    """
    if not result_output.get("1.0", tk.END).strip():
        messagebox.showwarning("No Results", "There are no results to export")
        return
    
    file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, 'w') as f:
            json.dump(result_list, f, indent=4)  # Export the list of dictionaries as JSON with indentation
        
        messagebox.showinfo("Success", "Results exported as JSON successfully")

# Function to show the export options (CSV/JSON) as a context menu
def show_export_menu(event, result_list):
    """
    Displays a context menu with options to export the query results as CSV or JSON.

    Parameters:
    - event: The event object containing details about the context menu event.
    - result_list: The list of dictionaries containing the query results.
    """
    export_menu = Menu(root, tearoff=0)
    export_menu.add_command(label="Export as CSV", command=lambda: export_results_as_csv(result_list))
    export_menu.add_command(label="Export as JSON", command=lambda: export_results_as_json(result_list))
    export_menu.post(event.x_root, event.y_root)

# Function to populate the schema Treeview with tables and columns
def populate_treeview():
    """
    Populates the Treeview widget with the current schema structure.
    """
    for item in schema_tree.get_children():
        schema_tree.delete(item)
    for table, columns in schema.items():
        table_id = schema_tree.insert('', 'end', text=table)
        add_columns_to_treeview(table_id, columns)

# Helper function to add columns to the Treeview under a specific table
def add_columns_to_treeview(parent, columns):
    """
    Adds columns to a specific table in the Treeview.

    Parameters:
    - parent: The parent Treeview item (table).
    - columns: The columns to add under the table.
    """
    for col in columns:
        if col[1] == 'RECORD':
            col_id = schema_tree.insert(parent, 'end', text=f"{col[0]} (RECORD) MODE({col[3]})")
            add_columns_to_treeview(col_id, col[2])
        else:
            schema_tree.insert(parent, 'end', text=f"{col[0]} ({col[1]}) MODE({col[2]})")

# Function to display the schema tables in a separate window
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

# Helper function to add nested columns to the Treeview
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

# Function to save the current schema to a JSON file
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

def fetch_schema():
    """
    Fetches the schema of all tables in the specified dataset from Google BigQuery
    and updates the UI with the fetched schema.
    """
    global global_dataset_name, global_project_id, schema
    global_dataset_name = dataset_entry.get().strip()
    global_project_id = project_entry.get().strip()

    if not global_dataset_name or not global_project_id:
        messagebox.showerror("Error", "Please provide both Dataset Name and Project ID.")
        return

    client = bigquery.Client(project=global_project_id)
    dataset_ref = client.dataset(global_dataset_name)
    schema = {}

    try:
        tables = client.list_tables(dataset_ref)
        for table in tables:
            table_ref = dataset_ref.table(table.table_id)
            table_obj = client.get_table(table_ref)
            schema[table.table_id] = [
                (field.name, field.field_type, field.mode, []) if field.field_type != 'RECORD' else
                (field.name, field.field_type, field.mode, [(subfield.name, subfield.field_type, subfield.mode) for subfield in field.fields])
                for field in table_obj.schema
            ]
        
        # Update the UI with the fetched schema
        schema_display.config(state='normal')
        schema_display.delete("1.0", tk.END)
        schema_display.insert(tk.END, schema_to_text(schema))
        schema_display.config(state='disabled')
        populate_treeview()

        messagebox.showinfo("Success", "Schema fetched successfully")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while fetching the schema: {e}")

# Function to handle the submission of a user query
def on_submit():
    """
    Handles the submission of a user query, translates it to SQL, and displays the result.
    """
    global latest_sql_query, latest_explanation  # Store the query and explanation for toggling
    user_query = user_input.get()
    database_schema = schema_to_text(schema)
    if not database_schema:
        messagebox.showerror("Error", "Please enter the database schema.")
        return
    sql_query, explanation = translate_to_sql(user_query, database_schema)
    latest_sql_query = sql_query
    latest_explanation = explanation
    display_query()

    # Disable the toggle button initially until results are available
    toggle_view_button.config(state="disabled", text="Switch")

# Function to display the generated SQL query and its explanation
def display_query():
    """
    Displays the generated SQL query and its explanation in the text area.
    """
    result_output.config(state="normal")
    result_output.delete("1.0", tk.END)
    result_output.insert(tk.END, f"SQL Query:\n{latest_sql_query}\n\nExplanation:\n{latest_explanation}")
    result_output.config(state="disabled")

# Function to display the results of the latest query
def display_results_view():
    """
    Displays the results of the latest SQL query in the text area.
    """
    if latest_result_list:
        display_results(latest_result_list)

# Function to toggle between displaying the query or the results
def toggle_view():
    """
    Toggles between displaying the SQL query and its explanation, and displaying the query results.
    """
    global showing_results
    if showing_results:
        display_query()
    else:
        display_results_view()
    showing_results = not showing_results

# Function to handle feedback submission for query refinement
def on_feedback():
    """
    Handles the submission of feedback to refine the generated SQL query.
    """
    feedback = simpledialog.askstring("Feedback", "Please provide feedback to refine the query:")
    if feedback:
        user_query = user_input.get()
        database_schema = schema_to_text(schema)
        sql_query, explanation = translate_to_sql(user_query, database_schema, feedback)
        latest_sql_query = sql_query
        latest_explanation = explanation
        display_query()

        # Disable the toggle button until results are available
        toggle_view_button.config(state="disabled", text="Switch")

# Function to open the manual schema entry dialog
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

# Function to handle query selection from history
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

# Function to translate a natural language query into SQL using OpenAI's API
def translate_to_sql(user_query, database_schema, feedback=None):
    """
    Translates a natural language question into an SQL query using OpenAI.

    Parameters:
    - user_query: The natural language question from the user.
    - database_schema: The database schema to use for query generation.
    - feedback: Optional feedback to refine the query.

    Returns:
    - A tuple containing the SQL query and an explanation of the query.
    """
    global latest_sql_query  
    
    prompt = f"""
    You are an expert SQL query generator. Your role is to translate user natural language questions into SQL queries based on a given database schema provided by the user.
    When giving the answer to the user, follow these rules:

    - Use PostgreSQL syntax to write the SQL query.
    - Provide the answer as only SQL query in correct format that is ready to be executed using Google BigQuery.
    - Provide a brief explanation of the SQL query after the query itself. Write it in the following format: Explanation: [explanation itself]
    - If no table or column satisfies the user's natural language request, return a message indicating that it is not possible to create a query.
    - If feedback is provided, use it to refine the query.
    - If a column's type is RECORD, the details/fields of the nested structure are given inside the consecutive parenthesis block. For example, the following is a valid syntax for columns with RECORD structure: details RECORD(price FLOAT MODE(NULLABLE), quantity INTEGER MODE(REQUIRED)) MODE(NULLABLE)
    - If a column's type is RECORD and is REPEATED, use the UNNEST function to flatten the structure. Do not use JSON extraction syntax (->>).
    - Access nested fields directly using the dot notation. For example, use details.price to access the price field within the details record.
    - While providing the SQL query do not give it in comment block.
    - When generating queries do not forget to use aliases.

    The schema is provided in the following format:
    - Each table is listed with its columns inside parentheses.
    - Columns of type RECORD have their fields listed inside nested parentheses.
    - Each column has its mode (NULLABLE or REQUIRED) specified.

    Database Schema:
    {database_schema}

    Question:
    {user_query}

    Feedback:
    {feedback if feedback else "None"}

    SQL Query:
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert SQL query generator."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200,
        temperature=0.3,
        stop=["SQL Query:"]
    )
    full_response = response.choices[0].message.content.strip()

    sql_query = full_response.split("Explanation:")[0].strip()
    explanation = full_response.split("Explanation:")[1].strip() if "Explanation:" in full_response else "No explanation provided."
    
    # Clean up the extracted SQL query
    sql_query = sql_query.strip()

    if sql_query.lower().startswith("sql"):
        sql_query = sql_query[sql_query.lower().find("select"):].strip()

    dataset_name = "{dataset_name}"
    project_id = "{project_id}"
    
    table_names = re.findall(r'\b\w+\b', database_schema)
    
    for table_name in table_names:
        qualified_name = f"`{project_id}.{dataset_name}.{table_name}`"
        # Replace only standalone table names in the FROM clause and JOIN conditions
        sql_query = re.sub(fr'(?i)\bFROM\s+{table_name}\b', f'FROM {qualified_name}', sql_query)
        sql_query = re.sub(fr'(?i)\bJOIN\s+{table_name}\b', f'JOIN {qualified_name}', sql_query)
        sql_query = re.sub(fr'(?i)\bJOIN\s+\b{table_name}\b', f'JOIN {qualified_name}', sql_query)

    latest_sql_query = sql_query  # Update the global variable with the latest query
    update_query_history(user_query, sql_query, explanation)  # Update query history
    
    return sql_query, explanation

# Function to update the query history with a new entry
def update_query_history(user_query, sql_query, explanation):
    """
    Updates the query history with a new entry.

    Parameters:
    - user_query: The natural language question from the user.
    - sql_query: The SQL query generated from the user query.
    - explanation: An explanation of the SQL query.
    """
    query_history.append((user_query, sql_query, explanation))  # Store only the query and explanation in history

# Function to show the context menu
def show_context_menu(event):
    """
    Displays a context menu for additional actions.

    Parameters:
    - event: The event object triggering the context menu.
    """
    context_menu.post(event.x_root, event.y_root)

# Function to convert the schema dictionary into a text representation
def schema_to_text(schema):
    """
    Converts the internal schema dictionary into a text representation.

    Parameters:
    - schema: The schema dictionary to convert.

    Returns:
    - A string representing the schema in text format.
    """
    def columns_to_text(columns):
        column_texts = []
        for col in columns:
            if col[1] == 'RECORD':
                nested_text = columns_to_text(col[2])
                column_texts.append(f"{col[0]} RECORD({nested_text}) MODE({col[3]})")
            else:
                column_texts.append(f"{col[0]} {col[1]} MODE({col[2]})")
        return ', '.join(column_texts)

    schema_text = "Tables:\n"
    for table, columns in schema.items():
        schema_text += f"- {table} ({columns_to_text(columns)})\n"
    return schema_text

# Function to open the JSON schema entry dialog and add the schema to the program
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

# Dialog class for manual schema entry
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

# Initialize the global schema dictionary and other state variables
schema = {}
latest_result_list = []  # To store the results of the last executed query
query_history = []  # To store the history of queries, explanations, and results
showing_results = False  # Flag to track the current view state

# Initialize the main application window
root = tk.Tk()
root.title("Natural Language to SQL Translator")

# Add entry fields for Dataset Name and Project ID at the top of the window
tk.Label(root, text="Dataset Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
dataset_entry = tk.Entry(root, width=50)
dataset_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

tk.Label(root, text="Project ID:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
project_entry = tk.Entry(root, width=50)
project_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

# Move the rest of the UI elements down by two rows to accommodate the new fields
tk.Label(root, text="Database Schema:").grid(row=2, column=0, padx=5, pady=5, sticky="nw")
schema_tree = ttk.Treeview(root, height=10)
schema_tree.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")

# Create the hidden scrolledtext widget to retain the existing logic
schema_display = scrolledtext.ScrolledText(root, height=10, width=70, state="disabled")
schema_display.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")
schema_display.grid_remove()  # Hide the widget

# Button to add schema manually
add_schema_button = tk.Button(root, text="Add Schema", command=on_schema_entry)
add_schema_button.grid(row=3, column=0, padx=5, pady=5, sticky="w")

# Button to add schema as JSON
add_schema_button_JSON = tk.Button(root, text="Add Schema as JSON", command=add_json_schema_as_text)
add_schema_button_JSON.grid(row=3, column=1, padx=5, pady=5, sticky="e")

# Small button for additional actions through context menu
small_button = tk.Button(root, text="...")
small_button.grid(row=3, column=2, padx=5, pady=5, sticky="e")
small_button.bind("<Button-1>", show_context_menu)

# Context menu for additional actions
context_menu = Menu(root, tearoff=0)
context_menu.add_command(label="Show Tables", command=show_tables)
context_menu.add_command(label="Save Schema", command=save_schema)
context_menu.add_command(label="Load Schema", command=load_schema)
context_menu.add_command(label="Fetch Schema from BigQuery", command=fetch_schema)  # Added Fetch Schema option

tk.Label(root, text="Enter your question:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
user_input = tk.Entry(root, width=70)
user_input.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

# Button to submit user query
submit_button = tk.Button(root, text="Submit", command=on_submit)
submit_button.grid(row=5, column=1, padx=5, pady=5, sticky="e")

# Button to provide feedback on generated query
feedback_button = tk.Button(root, text="Provide Feedback", command=on_feedback)
feedback_button.grid(row=5, column=0, padx=5, pady=5, sticky="w")

tk.Label(root, text="Results:").grid(row=6, column=0, padx=5, pady=5, sticky="nw")
result_output = scrolledtext.ScrolledText(root, height=15, width=70, state="disabled")
result_output.grid(row=6, column=1, padx=5, pady=5, sticky="nsew")

# Button to export query results
export_results_button = tk.Button(root, text="Export Results", state="disabled")
export_results_button.grid(row=7, column=0, padx=5, pady=5, sticky="w")

# Button to execute the latest SQL query
execute_button = tk.Button(root, text="Execute on Database", command=on_execute)
execute_button.grid(row=7, column=1, padx=5, pady=5, sticky="e")

# Button to toggle between query and result views
toggle_view_button = tk.Button(root, text="Switch", command=toggle_view, state="disabled")
toggle_view_button.grid(row=8, column=1, padx=5, pady=5, sticky="e")

# Button to open the query history window
query_history_button = tk.Button(root, text="Query History", command=open_query_history)
query_history_button.grid(row=8, column=0, padx=5, pady=5, sticky="w")

# Start the Tkinter event loop
root.mainloop()