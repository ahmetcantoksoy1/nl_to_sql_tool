# Natural Language to SQL Translator Tools

 This project translates natural language questions into SQL queries and executes them on a Google BigQuery or PostgreSQL database. 

## Directory Structure 
nl_to_sql_tool/ \
│ \
├── scripts/   \
│   ├── nl_to_sql_tool_bigquery.py     # Tool for BigQuery \
│   ├── nl_to_sql_tool_postgre.py      # Tool for Postgre\
│ \
├── requirements.txt                 # Python dependencies \
├── README.md                        # Project documentation \

## Python Setup

### 1. Download and Install Python

If you don't have Python 3.12.3 installed on your machine:

- **Windows**:
  - Download Python 3.12.3 from the [Python Downloads](https://www.python.org/downloads/) page.
  - Run the installer and check "Add Python to PATH" during installation.
  
- **macOS**:
  - Use Homebrew to install Python:
    ```bash
    brew install python@3.12
    ```
  - Alternatively, download and install from the [Python Downloads](https://www.python.org/downloads/) page.
  
- **Linux**:
  - Install using your package manager:
    ```bash
    sudo apt-get update
    sudo apt-get install python3.12
    ```

### 2. Verify Installation

Check the installed Python version:

```bash
python3 --version
```

## Setup 
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ahmetcantoksoy1/nl_to_sql_tool.git
   cd nl_to_sql_tool

2. **Install the required packages**: 
```bash 
pip install -r requirements.txt
```
3. **Set up your credentials**:

Before running the application, you need to manually set up your credentials within the code:

**Google BigQuery:** Open the nl_to_sql_tool_bigquery.py script and locate the following lines:
```
client = OpenAI(api_key="your_openai_api_key")
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/path/to/your/credentials.json'
```
Replace "your_openai_api_key" with your OpenAI API key, and update the path to your Google BigQuery credentials file.

**PostgreSQL:** If you are using the PostgreSQL version, you may need to adjust similar lines in nl_to_sql_tool_postgre.py, depending on how credentials are handled for PostgreSQL.

4. **Run the application**:
Run the application with the appropriate script:
```
	python scripts/nl_to_sql_tool_bigquery.py

                     or
                     
   python scripts/nl_to_sql_tool_postgre.py
```

## Usage

### 1. **Inputting Your Database Schema**

Before you can translate natural language queries into SQL, you need to input your database schema into the tool.

#### **Option 1: Manually Enter the Schema**

- Click on the "Add Schema" button in the GUI.
- A dialog box will appear, allowing you to manually input your schema by specifying table names, column names, types, and modes.
- For each table, enter the necessary details and add columns as needed. Columns of type `RECORD` can have nested structures, which you can specify in the dialog.
- Once you're done, the schema will be displayed and stored within the tool.

#### **Option 2: Add Schema as JSON**

- Click on the "Add Schema as JSON" button in the GUI.
- A dialog box will appear, allowing you to paste your schema in JSON format.
- This is particularly useful if you have exported your schema from Google BigQuery or another source.
- After pasting the JSON schema, the tool will parse and display it in the GUI.

#### **Option 3: Fetch Schema from Google BigQuery**

If you are working with Google BigQuery, you can automatically fetch your database schema:

- Ensure you have correctly set up your Google BigQuery credentials in the code (`nl_to_sql_tool_bigquery.py`).
- Enter the Dataset Name and Project ID in the respective fields at the top of the GUI.
- Click on the "Fetch Schema from BigQuery" option in the context menu (accessed by clicking the "..." button).
- The tool will retrieve the schema for all tables in the specified dataset and display it in the GUI.

### 2. **Asking Your Question**

Once your schema is loaded, you can start asking natural language questions:

- Type your question into the input field at the bottom of the GUI.
- Click the "Submit" button.
- The tool will generate an SQL query based on your question and the provided schema.
- The generated SQL query and a brief explanation will be displayed in the output area.

### 3. **Reviewing and Refining the SQL Query**

After the SQL query is generated, you have several options:

- **Review the Query**: The generated SQL query and its explanation will be displayed in the output area. Review this to ensure it meets your requirements.
  
- **Provide Feedback**: If the query isn't quite right, click on the "Provide Feedback" button. A dialog box will appear where you can enter your feedback. This feedback will be used to refine the SQL query.
  
- **Toggle View**: You can toggle between viewing the generated SQL query and the results of the executed query by clicking the "Switch" button. This allows you to easily compare the query with its results.


### 4. **Executing the SQL Query**

Once you're satisfied with the generated SQL query, you can execute it on your database:

- Click the "Execute on Database" button.
- The query will be executed on the connected Google BigQuery or PostgreSQL database.
- The results of the query will be displayed in the output area.


### 5. **Exporting Query Results**

If you need to save the results of your SQL query, you can export them:

- **Export as CSV**: Right-click on the output area and select "Export as CSV" from the context menu. You will be prompted to choose a location to save the file.
  
- **Export as JSON**: Similarly, right-click on the output area and select "Export as JSON". Choose a location to save the file.

### 6. **Viewing Query History**

The tool keeps track of all queries submitted during the session:

- Click on the "Query History" button to view a history of all the queries and their corresponding explanations.
- Double-click any entry in the history to reload the query into the input field, allowing you to modify or re-execute it.


### 7. **Additional Features**

- **Schema Display**: The tool provides a tree view of your database schema, making it easy to visualize the structure of your tables and columns.
  
- **Context Menu**: The "..." button in the GUI opens a context menu with additional options like "Show Tables", "Save Schema", "Load Schema", and "Fetch Schema from BigQuery".
  
- **Toggle Between Query and Results**: The "Switch" button allows you to toggle between the generated SQL query and its execution results, enabling you to easily switch between reviewing the query and its output.

