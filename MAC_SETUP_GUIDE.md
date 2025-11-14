# Complete Setup Guide for Mac - Reconciliation System

This guide will get you from zero to running the reconciliation system on your Mac.

---

## 📋 Prerequisites

### 1. Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Required Tools

```bash
# Install Python 3.11
brew install python@3.11

# Install PostgreSQL
brew install postgresql@15

# Install Node.js (for frontend later)
brew install node

# Verify installations
python3.11 --version  # Should show Python 3.11.x
psql --version        # Should show PostgreSQL 15.x
node --version        # Should show v18 or higher
```

---

## 🚀 Quick Start - Native Development (Recommended for Learning)

This approach runs everything directly on your Mac - no Docker needed initially.

### Step 1: Setup Project Structure

```bash
# Create project directory
mkdir -p ~/projects/reconciliation-system
cd ~/projects/reconciliation-system

# Create directory structure
mkdir -p backend/app
mkdir -p frontend/src
mkdir -p samples  # For your test files
```

### Step 2: Setup Backend

```bash
cd ~/projects/reconciliation-system/backend

# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Your prompt should now show (venv)

# You should see (venv) in your terminal now
```

### Step 3: Copy Files

Place these files in your `backend/app/` directory:
- `excel_parser.py` (from outputs)
- `pdf_processor.py` (from outputs)
- `reconciliation_engine.py` (from outputs)
- `simplified_main_api.py` (from outputs) - **rename to `main.py`**

Place these files in your `backend/` directory:
- `requirements.txt` (from outputs)
- `.env.example` (from outputs)

```bash
# Your structure should look like:
# backend/
#   ├── venv/
#   ├── app/
#   │   ├── excel_parser.py
#   │   ├── pdf_processor.py
#   │   ├── reconciliation_engine.py
#   │   └── main.py
#   ├── requirements.txt
#   └── .env.example
```

### Step 4: Install Python Dependencies

```bash
cd ~/projects/reconciliation-system/backend

# Make sure venv is activated (you should see (venv) in prompt)
pip install --upgrade pip
pip install -r requirements.txt

# This will take 1-2 minutes
```

### Step 5: Setup PostgreSQL Database

```bash
# Start PostgreSQL
brew services start postgresql@15

# Create database
createdb reconciliation

# Test connection
psql reconciliation -c "SELECT 1"
# Should show: ?column? 
#                    1
```

### Step 6: Configure Environment Variables

```bash
cd ~/projects/reconciliation-system/backend

# Copy example to actual .env file
cp .env.example .env

# Edit .env file
nano .env  # or use your favorite editor (code .env, vim .env, etc.)
```

**Edit these values in .env:**

```bash
# Database (should work as-is for local development)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/reconciliation

# IMPORTANT: Add your Azure credentials here
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://YOUR-RESOURCE.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-actual-key-here

# These are fine as default for now
MIN_PDF_CONFIDENCE=0.75
MAX_FILE_SIZE_MB=50
```

**How to get Azure credentials:**
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Document Intelligence resource (or create one)
3. Click "Keys and Endpoint" in the left menu
4. Copy "KEY 1" and "Endpoint"

### Step 7: Initialize Database Tables

```bash
cd ~/projects/reconciliation-system/backend

# Make sure venv is activated
source venv/bin/activate

# Run this Python code to create tables
python3 << 'EOF'
from app.main import Base, engine
Base.metadata.create_all(bind=engine)
print("✅ Database tables created successfully!")
EOF
```

### Step 8: Test Your Setup

```bash
cd ~/projects/reconciliation-system/backend

# Make sure venv is activated
source venv/bin/activate

# Test Excel parser
python3 << 'EOF'
from app.excel_parser import ExcelParser

print("Testing Excel Parser...")
parser = ExcelParser()
print("✅ Excel Parser loaded successfully!")
EOF

# Test PDF processor (requires Azure credentials)
python3 << 'EOF'
from app.pdf_processor import PDFProcessor
import os

endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

if endpoint and key:
    processor = PDFProcessor(endpoint, key)
    print("✅ PDF Processor initialized successfully!")
else:
    print("⚠️  Azure credentials not configured")
EOF
```

### Step 9: Start the Backend Server

```bash
cd ~/projects/reconciliation-system/backend

# Make sure venv is activated
source venv/bin/activate

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 10: Test the API

Open a **new terminal window** (keep the server running in the first):

```bash
# Test health check
curl http://localhost:8000/health

# Should return something like:
# {"status":"healthy","timestamp":"2025-11-12T...","database":"healthy","azure_di_configured":true}

# Open API documentation in browser
open http://localhost:8000/docs
```

You should see the Swagger UI with all API endpoints!

---

## 🧪 Testing with Your Files

### Prepare Test Files

```bash
# Copy your test files to samples directory
cd ~/projects/reconciliation-system
mkdir -p samples

# Copy your files (adjust paths as needed)
cp ~/Downloads/019382.xlsm samples/
cp ~/Downloads/EMEI_test1.pdf samples/
```

### Test via API

```bash
# Upload files for reconciliation
curl -X POST "http://localhost:8000/api/v1/reconciliation/upload" \
  -F "excel_file=@samples/019382.xlsm" \
  -F "pdf_file=@samples/EMEI_test1.pdf"

# You'll get a response like:
# {
#   "reconciliation_id": "abc-123-def-456",
#   "status": "processing",
#   "message": "Files uploaded successfully. Processing started in background."
# }

# Check status (replace with your actual ID)
curl "http://localhost:8000/api/v1/reconciliation/{your-id}/status"

# Keep checking until status is "completed"
# Processing takes 1-2 minutes
```

### Test via Browser UI (Coming Next)

Once you build the React frontend, you'll have a nice drag-and-drop interface!

---

## 🎨 Frontend Setup (Optional - Can Do Later)

```bash
cd ~/projects/reconciliation-system/frontend

# Initialize React app
npx create-react-app . --template typescript

# Install dependencies
npm install react-router-dom react-dropzone axios

# Copy the ReconciliationUpload.tsx component
# (from outputs) into src/components/

# Start frontend
npm start

# Opens http://localhost:3000
```

---

## 🐳 Docker Setup (When Ready to Deploy)

Once everything works natively, you can dockerize it:

```bash
cd ~/projects/reconciliation-system

# Copy docker files
# - docker-compose.yml
# - docker-compose.dev.yml  
# - Dockerfile.backend

# For development (just database in Docker)
docker-compose -f docker-compose.dev.yml up -d

# For full Docker setup
docker-compose up --build
```

---

## 📝 Daily Development Workflow

### Morning Routine

```bash
# 1. Start database (if not already running)
brew services start postgresql@15

# 2. Navigate to project
cd ~/projects/reconciliation-system/backend

# 3. Activate virtual environment
source venv/bin/activate

# 4. Start backend
uvicorn app.main:app --reload

# 5. In another terminal: start frontend (if you built it)
cd ~/projects/reconciliation-system/frontend
npm start
```

### Making Changes

```bash
# Backend changes:
# - Edit files in backend/app/
# - Server auto-reloads (thanks to --reload flag)
# - Check terminal for any errors

# Frontend changes:
# - Edit files in frontend/src/
# - Browser auto-reloads
# - Check browser console for errors
```

### Shutting Down

```bash
# Stop backend: Press Ctrl+C in terminal
# Stop frontend: Press Ctrl+C in terminal
# Stop database: brew services stop postgresql@15
```

---

## 🔧 Troubleshooting

### "Command not found: python3.11"

```bash
# Create an alias
echo 'alias python3.11=/usr/local/bin/python3' >> ~/.zshrc
source ~/.zshrc
```

### "Could not connect to database"

```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# If not running, start it
brew services start postgresql@15

# Test connection
psql -l
```

### "No module named 'app'"

```bash
# Make sure you're in the right directory
cd ~/projects/reconciliation-system/backend

# Make sure venv is activated (should see (venv) in prompt)
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "Azure Document Intelligence error"

```bash
# Check your .env file
cat .env | grep AZURE

# Make sure both values are set and correct
# Test by visiting the endpoint in your browser
# Should see: {"error": {...}} (not a connection error)
```

### Excel Parser Not Finding Cells

```bash
# The cell coordinates need adjustment for your specific Excel format
# Open excel_parser.py and look for lines like:
# emei_code=self._get_cell_value("B3", ...)

# You'll need to:
# 1. Open your Excel file
# 2. Note which cells contain which data
# 3. Update the cell references in excel_parser.py
```

---

## 📚 Next Steps

1. **Adjust Excel Parser** - Update cell coordinates for your specific format
2. **Test with Real Files** - Upload your actual 019382.xlsm and EMEI_test1.pdf
3. **Build Frontend** - Create the React UI for easier testing
4. **Generate Reports** - Implement Excel/PDF report generation
5. **Deploy** - Move to Docker and deploy to a server

---

## 🆘 Getting Help

If you get stuck:

1. **Check logs** - Look at terminal output for error messages
2. **Check API docs** - Visit http://localhost:8000/docs
3. **Test endpoints** - Use curl or Postman to test individual endpoints
4. **Database** - Use `psql reconciliation` to inspect database
5. **Python errors** - Read error messages carefully, they usually tell you what's wrong

---

## ✅ Success Checklist

- [ ] Python 3.11 installed and working
- [ ] PostgreSQL running locally
- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Database created (`createdb reconciliation`)
- [ ] Environment variables configured (`.env` file with Azure credentials)
- [ ] Database tables created
- [ ] Backend server starts without errors (`uvicorn app.main:app --reload`)
- [ ] Health check returns "healthy" (`curl http://localhost:8000/health`)
- [ ] Can upload test files via API
- [ ] Can check reconciliation status
- [ ] Results show in database

Once all checkboxes are ✅, you're ready to develop!

---

**Time to Complete Setup**: 30-60 minutes (first time)
**Time to Start Development** (after setup): 2 minutes (just start the server!)
