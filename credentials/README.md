# Google API Credentials

To use Google Sheets (like in the Order Tracker tool), you must generate a `google_credentials.json` file.

## Instructions:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new Project (or select an existing one).
3. Navigate to **APIs & Services > Library** and enable the **Google Sheets API**.
4. Navigate to **APIs & Services > Credentials**.
5. Click **Create Credentials > Service Account**.
6. Fill in the details and create the service account.
7. Click on the newly created service account, go to the **Keys** tab.
8. Click **Add Key > Create new key**, select **JSON**.
9. A JSON file will download. Place it in this `credentials/` folder. You may keep its original name or rename it to something recognizable (e.g. `google_credentials.json`).
10. **IMPORTANT:** Open the tool configuration UI in NOVA (e.g. for Order Tracker) and enter the exact filename of your credentials file in the `Credentials_File` field.
11. **IMPORTANT:** Open your Google Sheet in the browser and share it with the `client_email` address found inside your downloaded JSON file. Ensure it has "Editor" permissions.
