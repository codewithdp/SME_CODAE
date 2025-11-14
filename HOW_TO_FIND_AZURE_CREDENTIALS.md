# How to Find Azure Credentials

This guide helps you locate the necessary Azure credentials for the SME/CODAE reconciliation system.

---

## 🔵 Azure Blob Storage Connection String

### **Method 1: Azure Portal (Recommended)**

1. **Go to Azure Portal:**
   - Navigate to: https://portal.azure.com
   - Sign in with your Azure account

2. **Find Your Storage Account:**
   - In the search bar at the top, type "Storage accounts"
   - Click on "Storage accounts" from the results
   - Select your storage account from the list

3. **Get Connection String:**
   - In the left sidebar, under "Security + networking", click **"Access keys"**
   - You'll see two keys: `key1` and `key2`
   - Click **"Show"** next to "Connection string" under either key
   - Click the **copy icon** to copy the entire connection string

   **The connection string looks like this:**
   ```
   DefaultEndpointsProtocol=https;
   AccountName=yourstorageaccount;
   AccountKey=abc123...xyz==;
   EndpointSuffix=core.windows.net
   ```

4. **Add to Your .env File:**
   ```bash
   AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
   ```

---

### **Method 2: Using Azure CLI**

If you have Azure CLI installed:

```bash
# Login to Azure
az login

# List your storage accounts
az storage account list --output table

# Get connection string for a specific account
az storage account show-connection-string \
  --name YOUR_STORAGE_ACCOUNT_NAME \
  --resource-group YOUR_RESOURCE_GROUP_NAME
```

Example output:
```json
{
  "connectionString": "DefaultEndpointsProtocol=https;AccountName=..."
}
```

---

## 🔵 Azure Document Intelligence Credentials

You already have these in your `.env`, but here's how to verify them:

### **Find Endpoint and Key**

1. **Go to Azure Portal:**
   - Navigate to: https://portal.azure.com

2. **Find Your Document Intelligence Resource:**
   - Search for "Document Intelligence" or "Form Recognizer"
   - Click on your resource

3. **Get Credentials:**
   - In the left sidebar, click **"Keys and Endpoint"**
   - Copy:
     - **Endpoint:** `https://YOUR_RESOURCE_NAME.cognitiveservices.azure.com/`
     - **Key 1** or **Key 2:** Use either key

4. **Verify in .env:**
   ```bash
   AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://sme-recon.cognitiveservices.azure.com/
   AZURE_DOCUMENT_INTELLIGENCE_KEY=DIL9O38jii419QZgMasd...
   ```

---

## 🔵 Custom Model Information

### **Find Your Custom Model ID**

You mentioned your model is called **`Header_extraction`**, but to verify:

1. **Go to Document Intelligence Studio:**
   - Navigate to: https://documentintelligence.ai.azure.com/studio
   - Sign in with your Azure account

2. **View Your Models:**
   - Click on **"Custom models"** in the left sidebar
   - Find your model in the list
   - Click on it to see details

3. **Get Model ID:**
   - The Model ID will be displayed at the top
   - It should be: **`Header_extraction`**

4. **Add to .env:**
   ```bash
   CUSTOM_MODEL_ID=Header_extraction
   ```

---

## 📋 Complete .env File Template

Here's what your complete `.env` file should look like:

```bash
# ============================================================================
# DATABASE
# ============================================================================
DATABASE_URL=postgresql://writetodennis@localhost:5432/SME_recon

# ============================================================================
# AZURE DOCUMENT INTELLIGENCE (EXISTING)
# ============================================================================
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://sme-recon.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=DIL9O38jii419QZgMasd...
MIN_PDF_CONFIDENCE=0.75
MAX_FILE_SIZE_MB=50

# ============================================================================
# AZURE BLOB STORAGE (NEW - FOR BULK UPLOAD)
# ============================================================================
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=YOUR_ACCOUNT;AccountKey=YOUR_KEY;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER_NAME=bulk-uploads

# ============================================================================
# CUSTOM MODEL (NEW - FOR BULK UPLOAD)
# ============================================================================
CUSTOM_MODEL_ID=Header_extraction
```

---

## 🧪 Testing Your Credentials

### **Test Azure Blob Storage Connection**

Create a test script: `backend/test_blob_storage.py`

```python
import os
from dotenv import load_dotenv
from app.blob_storage_service import BlobStorageService

load_dotenv()

# Test connection
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
print(f"Connection string found: {connection_string[:50]}...")

try:
    blob_service = BlobStorageService(connection_string)
    print("✅ Successfully connected to Azure Blob Storage!")

    # List containers
    containers = blob_service.blob_service_client.list_containers()
    print("\nAvailable containers:")
    for container in containers:
        print(f"  - {container.name}")

except Exception as e:
    print(f"❌ Error connecting to blob storage: {e}")
```

Run it:
```bash
cd backend
source venv/bin/activate
python test_blob_storage.py
```

---

### **Test Custom Model**

Create: `backend/test_custom_model.py`

```python
import os
from dotenv import load_dotenv
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
model_id = os.getenv("CUSTOM_MODEL_ID", "Header_extraction")

print(f"Endpoint: {endpoint}")
print(f"Model ID: {model_id}")

try:
    client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))
    print("✅ Successfully connected to Azure Document Intelligence!")

    # Test with a sample PDF (use one of your 2-page PDFs)
    with open("../EMEI_test1.pdf", "rb") as f:
        poller = client.begin_analyze_document(
            model_id=model_id,
            analyze_request=f.read(),
            content_type="application/pdf"
        )
        result = poller.result()

    print(f"\n✅ Custom model '{model_id}' is working!")
    print(f"Documents found: {len(result.documents)}")

    if result.documents:
        doc = result.documents[0]
        print(f"\nExtracted fields:")
        for field_name, field_value in doc.fields.items():
            print(f"  - {field_name}: {field_value.content if hasattr(field_value, 'content') else field_value.value}")

except Exception as e:
    print(f"❌ Error: {e}")
```

Run it:
```bash
python test_custom_model.py
```

---

## 🔒 Security Notes

**IMPORTANT:**
1. **Never commit `.env` to Git** - It contains secrets!
2. **Keep your keys secure** - Don't share them
3. **Rotate keys periodically** - Azure allows you to regenerate keys
4. **Use Key1 or Key2** - You can rotate one while the other is in use

**Already Protected:**
- ✅ `.env` is in `.gitignore`
- ✅ `.env.example` template provided (no secrets)

---

## ❓ Troubleshooting

### **"Connection string not found" Error**
- Check that `.env` file is in `backend/` directory
- Verify no extra spaces around the `=` sign
- Make sure the connection string is all on one line

### **"Access Denied" Error**
- Verify your Azure account has access to the storage account
- Check that the access key is correct (try Key2 if Key1 doesn't work)
- Ensure your IP isn't blocked by storage account firewall

### **"Model not found" Error**
- Verify the model ID is exactly: `Header_extraction`
- Check that the model is in the same region as your endpoint
- Ensure the model is trained and deployed

---

## 📞 Need Help?

If you're stuck:
1. Check Azure Portal status: https://status.azure.com
2. Verify your subscription is active
3. Ensure you have proper IAM roles:
   - **Storage Blob Data Contributor** (for blob storage)
   - **Cognitive Services User** (for Document Intelligence)

---

**Once you have the connection string, add it to `.env` and we can proceed with Phase 2!**
