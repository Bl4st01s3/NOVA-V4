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

    # Extract Sync Settings
    sync_settings = config.get("Sync_Settings", {})
    sync_mode = sync_settings.get("Sync_Mode", "Both")
    sync_priority = sync_settings.get("Sync_Priority", "Cloud First")

    cloud_config = config.get("Cloud_Connection", {})
    cloud_service = cloud_config.get("Service", "Google Drive")
    sheet_id = cloud_config.get("File_ID_or_Path", "")
    credentials_filename = cloud_config.get("Credentials_File", "google_credentials.json")

    local_config = config.get("Local_Connection", {})
    local_path = local_config.get("File_Path", "")

    if not sheet_id and not local_path:
        print(json.dumps({"error": "Neither Cloud File ID nor Local Excel path is configured."}))
        return

    credentials_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "credentials", credentials_filename))

    df = None
    worksheet = None
    used_cloud = False

    def try_cloud():
        nonlocal df, worksheet, used_cloud
        if sheet_id and cloud_service == "Google Drive" and os.path.exists(credentials_path):
            try:
                scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
                client = gspread.authorize(creds)
                sheet = client.open_by_key(sheet_id)
                worksheet = sheet.sheet1
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)
                used_cloud = True
                return True
            except Exception as e:
                return False
        return False

    def try_local():
        nonlocal df
        if local_path and os.path.exists(local_path):
            try:
                df = pd.read_excel(local_path)
                return True
            except Exception as e:
                return False
        return False

    # Execution Logic based on Sync Mode & Priority
    if sync_mode == "Cloud Only":
        success = try_cloud()
        if not success:
            print(json.dumps({"error": "Cloud connection failed and Sync_Mode is 'Cloud Only'."}))
            return

    elif sync_mode == "Local Only":
        success = try_local()
        if not success:
            print(json.dumps({"error": "Local read failed and Sync_Mode is 'Local Only'."}))
            return

    else: # "Both"
        if sync_priority == "Cloud First":
            if not try_cloud():
                if not try_local():
                    print(json.dumps({"error": "Both Cloud and Local reads failed."}))
                    return
        elif sync_priority == "Local First":
            if not try_local():
                if not try_cloud():
                    print(json.dumps({"error": "Both Local and Cloud reads failed."}))
                    return

    # Normalize DataFrame
    if df is None or df.empty:
        columns = list(config.get("schema", {}).keys())
        df = pd.DataFrame(columns=columns)

    if action == "read":
        # Apply filters
        result_df = df.copy()
        for k, v in read_filters.items():
            if k in result_df.columns:
                if isinstance(v, bool):
                    result_df = result_df[result_df[k].astype(str).str.lower() == str(v).lower()]
                else:
                    result_df = result_df[result_df[k] == v]

        records = result_df.to_dict(orient="records")

        # Deduplicate Delivery Windows for the LLM
        for record in records:
            start_date = record.get("Delivery Window Start")
            end_date = record.get("Delivery Window End")

            # If both dates exist and are identical, combine them into a single field
            if start_date and end_date and str(start_date).strip() == str(end_date).strip():
                record["Delivery Date"] = start_date
                del record["Delivery Window Start"]
                del record["Delivery Window End"]

        print(json.dumps({
            "status": "success",
            "source": "google_sheets" if used_cloud else "local_excel",
            "results": records
        }))

    elif action == "add":
        new_row = pd.DataFrame([new_order])
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df, worksheet, local_path, used_cloud, sync_mode)
        print(json.dumps({"status": "success", "message": "Order added successfully."}))

    elif action == "update":
        identifier = update_data.get("Order_Number") or update_data.get("Item")
        if not identifier:
            print(json.dumps({"error": "Must provide 'Order_Number' or 'Item' in update_data to identify row."}))
            return

        mask = (df["Order_Number"] == identifier) | (df["Item"] == identifier)
        if not mask.any():
            print(json.dumps({"error": f"Order {identifier} not found."}))
            return

        for k, v in update_data.items():
            if k in df.columns:
                df.loc[mask, k] = v

        save_data(df, worksheet, local_path, used_cloud, sync_mode)
        print(json.dumps({"status": "success", "message": f"Order {identifier} updated successfully."}))

    else:
        print(json.dumps({"error": f"Unknown action: {action}"}))


def save_data(df, worksheet, local_path, used_cloud, sync_mode):
    df = df.fillna("")

    # Write to local if mode allows
    if sync_mode in ["Both", "Local Only"] and local_path:
        try:
            df.to_excel(local_path, index=False)
        except:
            pass

    # Write to cloud if mode allows and connection was established
    if sync_mode in ["Both", "Cloud Only"] and used_cloud and worksheet:
        try:
            worksheet.clear()
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        except:
            pass


if __name__ == "__main__":
    main()
