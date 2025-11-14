-- ============================================================================
-- BULK UPLOAD SCHEMA
-- Tables for managing bulk PDF processing and batch reconciliation
-- ============================================================================

-- Table 1: Bulk Upload Sessions
-- Tracks each combined PDF upload
CREATE TABLE IF NOT EXISTS bulk_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Upload metadata
    original_filename VARCHAR(255) NOT NULL,
    upload_timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),

    -- Processing status
    status VARCHAR(20) NOT NULL DEFAULT 'processing',
    -- Status values: 'processing', 'completed', 'failed', 'partial'

    -- Statistics
    total_pages INTEGER,
    total_documents INTEGER,
    documents_with_2_pages INTEGER,
    documents_with_excel INTEGER,
    documents_reconciled INTEGER,

    -- Azure Blob Storage
    blob_container VARCHAR(100) DEFAULT 'bulk-uploads',
    blob_path VARCHAR(500), -- Path to original uploaded PDF

    -- Processing metadata
    processing_started_at TIMESTAMP WITHOUT TIME ZONE,
    processing_completed_at TIMESTAMP WITHOUT TIME ZONE,
    error_message TEXT,

    -- Retention
    retention_until TIMESTAMP WITHOUT TIME ZONE, -- 6 months from upload

    -- Optional user tracking (for future auth)
    user_id VARCHAR(100),

    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Table 2: Individual Documents (extracted from bulk PDF)
-- Each row represents one document extracted from the combined PDF
CREATE TABLE IF NOT EXISTS bulk_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to parent upload
    bulk_upload_id UUID NOT NULL REFERENCES bulk_uploads(id) ON DELETE CASCADE,

    -- Document identification (extracted from PDF header via custom model)
    document_id VARCHAR(50) NOT NULL, -- The EMEI ID (e.g., "92311")

    -- Extracted metadata fields (from Azure DI custom model "Header_extraction")
    tipo VARCHAR(50),
    lugar VARCHAR(255),
    codigo_codae VARCHAR(50),
    mes VARCHAR(20),
    ano VARCHAR(10),
    cep VARCHAR(20),
    diretoria VARCHAR(255),
    prestador VARCHAR(255),

    -- PDF information
    page_count INTEGER NOT NULL,
    page_numbers TEXT, -- JSON array of original page numbers [1, 2]
    pdf_blob_path VARCHAR(500), -- Path to split PDF in blob storage

    -- Excel matching
    excel_filename VARCHAR(255),
    excel_blob_path VARCHAR(500),
    excel_matched BOOLEAN DEFAULT FALSE,
    excel_uploaded_at TIMESTAMP WITHOUT TIME ZONE,

    -- Reconciliation
    reconciliation_id UUID REFERENCES reconciliations(id),
    reconciliation_status VARCHAR(20), -- 'pending', 'processing', 'completed', 'failed'
    reconciliation_match_percentage DOUBLE PRECISION,
    reconciliation_total_mismatches INTEGER,

    -- Processing status
    status VARCHAR(20) DEFAULT 'extracted',
    -- Status values: 'extracted', 'ready', 'reconciling', 'completed', 'failed'

    error_message TEXT,

    -- Confidence scores (from Azure DI)
    extraction_confidence DOUBLE PRECISION,

    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),

    -- Ensure document_id is unique within a bulk upload
    CONSTRAINT unique_document_per_upload UNIQUE (bulk_upload_id, document_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bulk_uploads_status ON bulk_uploads(status);
CREATE INDEX IF NOT EXISTS idx_bulk_uploads_created_at ON bulk_uploads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bulk_documents_bulk_upload_id ON bulk_documents(bulk_upload_id);
CREATE INDEX IF NOT EXISTS idx_bulk_documents_document_id ON bulk_documents(document_id);
CREATE INDEX IF NOT EXISTS idx_bulk_documents_status ON bulk_documents(status);
CREATE INDEX IF NOT EXISTS idx_bulk_documents_excel_matched ON bulk_documents(excel_matched);
CREATE INDEX IF NOT EXISTS idx_bulk_documents_reconciliation_id ON bulk_documents(reconciliation_id);

-- View: Summary of bulk uploads with statistics
CREATE OR REPLACE VIEW bulk_upload_summary AS
SELECT
    bu.id,
    bu.original_filename,
    bu.upload_timestamp,
    bu.status,
    bu.total_documents,
    COUNT(bd.id) as extracted_documents,
    COUNT(CASE WHEN bd.page_count = 2 THEN 1 END) as valid_page_count,
    COUNT(CASE WHEN bd.excel_matched = TRUE THEN 1 END) as matched_excel,
    COUNT(CASE WHEN bd.reconciliation_status = 'completed' THEN 1 END) as reconciled,
    bu.processing_completed_at,
    bu.error_message
FROM bulk_uploads bu
LEFT JOIN bulk_documents bd ON bu.id = bd.bulk_upload_id
GROUP BY bu.id
ORDER BY bu.upload_timestamp DESC;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_bulk_uploads_updated_at
    BEFORE UPDATE ON bulk_uploads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bulk_documents_updated_at
    BEFORE UPDATE ON bulk_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE bulk_uploads IS 'Tracks bulk PDF upload sessions';
COMMENT ON TABLE bulk_documents IS 'Individual documents extracted from bulk PDFs';
COMMENT ON COLUMN bulk_documents.document_id IS 'EMEI ID extracted from PDF header (e.g., 92311)';
COMMENT ON COLUMN bulk_documents.page_count IS 'Number of pages in this document (should be 2 for valid documents)';
COMMENT ON COLUMN bulk_documents.excel_matched IS 'Whether a matching Excel file was found and linked';
