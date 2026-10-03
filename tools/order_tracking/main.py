import sys
import json
import os
import datetime

# Attempt to load required spreadsheet libraries
try:
    import gspread
    from google.oauth2.service_account import Credentials
    import pandas as pd
except ImportError:
    print(json.dumps({"error": "Missing dependencies. Please run: pip install gspread google-auth pandas openpyxl"}))
    sys.exit(0)

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No arguments provided."}))
        return

    try:
        args = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON arguments."}))
        return

    action = args.get("action")
    read_filters = args.get("read_filters", {})
    new_order = args.get("new_order", {})
    update_data = args.get("update_data", {})

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(config_path):
        print(json.dumps({"error": "config.json not found."}))
        return

    with open(config_path, "r") as f:
        config = json.load(f)

    sheet_id = config.get("Cloud_File_Path", {}).get("Google_Drive_File_Path", "")
    local_path = config.get("Local_File_Path", {}).get("File_Path", "")

    if not sheet_id and not local_path:
        print(json.dumps({"error": "Neither Google Sheet ID nor Local Excel path is configured."}))
        return

    # Attempt to connect to Google Sheets
    credentials_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "credentials", "google_credentials.json"))

    df = None
    client = None
    worksheet = None
    used_cloud = False

    if sheet_id and os.path.exists(credentials_path):
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
            client = gspread.authorize(creds)

            # Open the sheet
            sheet = client.open_by_key(sheet_id)
            worksheet = sheet.sheet1
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            used_cloud = True
        except Exception as e:
            # Cloud failed, fall back
            used_cloud = False

    # Fallback to local
    if not used_cloud:
        if local_path and os.path.exists(local_path):
            try:
                df = pd.read_excel(local_path)
            except Exception as e:
                print(json.dumps({"error": f"Failed to read local Excel file: {str(e)}"}))
                return
        else:
            print(json.dumps({"error": "Google Sheets failed and local Excel file not found."}))
            return

    # Normalize DataFrame
    if df is None or df.empty:
        # Create empty DF based on schema
        columns = list(config.get("schema", {}).keys())
        df = pd.DataFrame(columns=columns)

    if action == "read":
        # Apply filters
        result_df = df.copy()
        for k, v in read_filters.items():
            if k in result_df.columns:
                if isinstance(v, bool):
                    # handle string booleans if necessary
                    result_df = result_df[result_df[k].astype(str).str.lower() == str(v).lower()]
                else:
                    result_df = result_df[result_df[k] == v]

        records = result_df.to_dict(orient="records")
        print(json.dumps({
            "status": "success",
            "source": "google_sheets" if used_cloud else "local_excel",
            "results": records
        }))

    elif action == "add":
        new_row = pd.DataFrame([new_order])
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df, worksheet, local_path, used_cloud, config)
        print(json.dumps({"status": "success", "message": "Order added successfully."}))

    elif action == "update":
        identifier = update_data.get("Order_Number") or update_data.get("Item")
        if not identifier:
            print(json.dumps({"error": "Must provide 'Order_Number' or 'Item' in update_data to identify row."}))
            return

        # Find row and update
        mask = (df["Order_Number"] == identifier) | (df["Item"] == identifier)
        if not mask.any():
            print(json.dumps({"error": f"Order {identifier} not found."}))
            return

        for k, v in update_data.items():
            if k in df.columns:
                df.loc[mask, k] = v

        save_data(df, worksheet, local_path, used_cloud, config)
        print(json.dumps({"status": "success", "message": f"Order {identifier} updated successfully."}))

    else:
        print(json.dumps({"error": f"Unknown action: {action}"}))


def save_data(df, worksheet, local_path, used_cloud, config):
    # Convert nans to empty strings
    df = df.fillna("")

    # Save to local always (as backup)
    if local_path:
        try:
            df.to_excel(local_path, index=False)
        except:
            pass

    if used_cloud and worksheet:
        # Update Google Sheet
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())


if __name__ == "__main__":
    main()
