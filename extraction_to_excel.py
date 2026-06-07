import sqlite3
import pandas as pd
import os

def compile_database_to_excel(db_path="database.db", output_filename="compiled_josaa_analysis.xlsx"):
    print("🚀 Connecting to database and initiating compilation process...")
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Database file '{db_path}' not found!")
        return

    # Establish connection to the SQLite database
    conn = sqlite3.connect(db_path)
    
    # We will store each DataFrame in this dictionary with its intended sheet name
    sheets_dict = {}

    try:
        # ------------------------------------------------------------------
        # 1. SHEET: DATA - allotment
        # ------------------------------------------------------------------
        print("📦 Processing Sheet: DATA - allotment...")
        allotment_query = """
            SELECT cva.rank AS Rank, cva.rollno AS [Roll No], cva.insti_name AS [Institute Name], 
                   cva.branch AS Branch, rws.state AS State, rws.city AS City
            FROM crl_vs_alloted cva
            LEFT JOIN roll_with_state rws ON cva.rollno = rws.roll
        """
        df_allotment = pd.read_sql_query(allotment_query, conn)
        sheets_dict["DATA - allotment"] = df_allotment

        # ------------------------------------------------------------------
        # 2. SHEET: STAT - Statewise count
        # ------------------------------------------------------------------
        print("📦 Processing Sheet: STAT - Statewise count...")
        state_count_query = """
            SELECT state AS State, COUNT(*) AS [Total Qualified Students]
            FROM roll_with_state
            WHERE state IS NOT NULL AND state != ''
            GROUP BY state
            ORDER BY [Total Qualified Students] DESC
        """
        sheets_dict["STAT - Statewise count"] = pd.read_sql_query(state_count_query, conn)

        # ------------------------------------------------------------------
        # 3. SHEET: STAT - Statewise allotment
        # ------------------------------------------------------------------
        print("📦 Processing Sheet: STAT - Statewise allotment...")
        # Cross-tabulation matching where students from each home state migrated to
        state_allotment_query = """
            SELECT rws.state AS State, cva.insti_name AS [Allotted Institute], COUNT(*) AS [Student Count]
            FROM crl_vs_alloted cva
            JOIN roll_with_state rws ON cva.rollno = rws.roll
            WHERE rws.state IS NOT NULL AND cva.insti_name IS NOT NULL
            GROUP BY rws.state, cva.insti_name
        """
        df_raw_allot = pd.read_sql_query(state_allotment_query, conn)
        # Pivot the data into an easy-to-read Matrix (Rows = States, Columns = Institutes)
        df_pivot_allot = df_raw_allot.pivot(index='State', columns='Allotted Institute', values='Student Count').fillna(0).astype(int)
        df_pivot_allot['Total Allotted'] = df_pivot_allot.sum(axis=1)
        sheets_dict["STAT - Statewise allotment"] = df_pivot_allot.reset_index()

        # ------------------------------------------------------------------
        # 4. SHEET: STAT - Statewise allotment%
        # ------------------------------------------------------------------
        print("📦 Processing Sheet: STAT - Statewise allotment%...")
        # Calculates conversion percentages (Seats secured vs. overall qualified pool per state)
        if "DATA - allotment" in sheets_dict and "STAT - Statewise count" in sheets_dict:
            df_total_qualified = sheets_dict["STAT - Statewise count"]
            df_allotted_counts = df_allotment['State'].value_counts().reset_index()
            df_allotted_counts.columns = ['State', 'Total Seats Allotted']
            
            df_pct = pd.merge(df_total_qualified, df_allotted_counts, on='State', how='left').fillna(0)
            df_pct['Total Seats Allotted'] = df_pct['Total Seats Allotted'].astype(int)
            
            # Compute the conversion rate
            df_pct['Allotment Percentage (%)'] = (df_pct['Total Seats Allotted'] / df_pct['Total Qualified Students'] * 100).round(2)
            sheets_dict["STAT - Statewise allotment%"] = df_pct

        # ------------------------------------------------------------------
        # 5. SHEET: STAT - Institutewise statecount
        # ------------------------------------------------------------------
        print("📦 Processing Sheet: STAT - Institutewise statecount...")
        # Generates demographic breakdown inside each campus
        insti_state_query = """
            SELECT cva.insti_name AS Institute, rws.state AS State, COUNT(*) AS [Student Count]
            FROM crl_vs_alloted cva
            JOIN roll_with_state rws ON cva.rollno = rws.roll
            WHERE cva.insti_name IS NOT NULL AND rws.state IS NOT NULL
            GROUP BY cva.insti_name, rws.state
        """
        df_raw_insti = pd.read_sql_query(insti_state_query, conn)
        df_pivot_insti = df_raw_insti.pivot(index='Institute', columns='State', values='Student Count').fillna(0).astype(int)
        df_pivot_insti['Total Strength'] = df_pivot_insti.sum(axis=1)
        sheets_dict["STAT - Institutewise statecount"] = df_pivot_insti.reset_index()

        # ------------------------------------------------------------------
        # WRITING TO EXCEL WITH PROFESSIONAL LAYOUT FORMATTING
        # ------------------------------------------------------------------
        print(f"📖 Writing data to professional Excel format: '{output_filename}'...")
        with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
            for sheet_name, df in sheets_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Dynamic column width auto-fitting to keep layout professional
                worksheet = writer.sheets[sheet_name]
                for col in worksheet.columns:
                    max_len = max(len(str(cell.value or '')) for cell in col)
                    col_letter = col[0].column_letter
                    worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

        print(f"✨ Success! Your compiled spreadsheet is ready at: {output_filename}")

    except Exception as e:
        print(f"❌ An error occurred during processing: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # If your database file has a different name, change it here
    compile_database_to_excel(db_path="database.db", output_filename="compiled_josaa_analysis.xlsx")