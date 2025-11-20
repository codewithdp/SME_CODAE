import React, { useState, useRef } from 'react';
import {
  Upload,
  FileText,
  CheckCircle2,
  Loader2,
  X,
  AlertCircle,
  FileSpreadsheet,
  ChevronRight,
  Package,
  Eye,
  XCircle,
  TrendingUp,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { bulkApi } from './api/bulkApi';
import { BulkUploadStatus, BulkDocument } from './types';
import { PDFViewer } from './PDFViewer';

interface FileInfo {
  file: File;
  name: string;
  size: number;
}

function BulkUpload() {
  // Step 1: PDF Upload
  const [pdfFile, setPdfFile] = useState<FileInfo | null>(null);
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  // Step 2: Processing Status
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [processingComplete, setProcessingComplete] = useState(false);

  // Step 3: Documents List
  const [documents, setDocuments] = useState<BulkDocument[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(false);

  // Step 4: Excel Upload
  const [excelFiles, setExcelFiles] = useState<File[]>([]);
  const [uploadingExcel, setUploadingExcel] = useState(false);
  const [excelUploadComplete, setExcelUploadComplete] = useState(false);

  // Step 5: Batch Reconciliation
  const [reconciling, setReconciling] = useState(false);
  const [reconciliationComplete, setReconciliationComplete] = useState(false);

  // Details Modal
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedReconciliation, setSelectedReconciliation] = useState<any | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  // Image Zoom Modal
  const [zoomedImage, setZoomedImage] = useState<string | null>(null);

  // Error handling
  const [error, setError] = useState<string | null>(null);

  // Selection state
  const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set());

  const pdfInputRef = useRef<HTMLInputElement>(null);
  const excelInputRef = useRef<HTMLInputElement>(null);

  // Load upload data on mount if we have a saved uploadId
  React.useEffect(() => {
    const loadSavedUpload = async () => {
      const savedId = localStorage.getItem('bulkUploadId');
      if (savedId && !uploadId) {
        // Only load if we don't already have an uploadId
        try {
          const status = await bulkApi.getStatus(savedId);
          if (status.status === 'completed' || status.status === 'processing') {
            // Set the uploadId to trigger showing the documents
            setUploadId(savedId);

            if (status.status === 'completed') {
              setProcessingComplete(true);
            } else {
              setProcessing(true);
            }

            const docs = await bulkApi.getDocuments(savedId);
            setDocuments(docs);

            // Check if Excel files have been uploaded
            const hasExcel = docs.some(d => d.excel_matched);
            if (hasExcel) {
              setExcelUploadComplete(true);
            }

            // Check reconciliation status
            const hasReconciliation = docs.some((d) => d.status === 'completed');
            const isReconciling = docs.some((d) => d.status === 'reconciling');

            if (hasReconciliation) {
              setReconciliationComplete(true);
            } else if (isReconciling) {
              setReconciling(true);
              // Start polling for reconciliation status
              const pollInterval = setInterval(async () => {
                try {
                  const updatedDocs = await bulkApi.getDocuments(savedId);
                  setDocuments(updatedDocs);

                  const stillProcessing = updatedDocs.some(
                    (d) => d.status === 'reconciling' || d.reconciliation_status === 'processing'
                  );

                  if (!stillProcessing) {
                    clearInterval(pollInterval);
                    setReconciling(false);
                    setReconciliationComplete(true);
                  }
                } catch (err) {
                  console.error('Erro ao verificar status:', err);
                  clearInterval(pollInterval);
                  setReconciling(false);
                }
              }, 3000);
            }
          }
        } catch (err) {
          console.error('Error loading saved upload:', err);
          // Clear invalid saved ID
          localStorage.removeItem('bulkUploadId');
        }
      }
    };

    loadSavedUpload();
  }, []); // Only run once on mount

  // Save uploadId to localStorage whenever it changes
  React.useEffect(() => {
    if (uploadId) {
      localStorage.setItem('bulkUploadId', uploadId);
    }
  }, [uploadId]);

  const handlePdfFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setPdfFile({
        file,
        name: file.name,
        size: file.size,
      });
    }
  };

  const handleExcelFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setExcelFiles(files);
  };

  const handleUploadPdf = async () => {
    if (!pdfFile) return;

    try {
      setUploading(true);
      setError(null);

      const response = await bulkApi.uploadPdf(pdfFile.file);
      setUploadId(response.id);
      setProcessing(true);

      // Start polling for status
      await bulkApi.pollStatus(
        response.id,
        (status: BulkUploadStatus) => {
          setProgress(status.progress_percentage);
          setCurrentStep(status.current_step || 'Processando...');

          if (status.status === 'completed') {
            setProcessing(false);
            setProcessingComplete(true);
            loadDocuments(response.id);
          }
        }
      );
    } catch (err) {
      console.error('Erro ao fazer upload do PDF:', err);
      setError(
        err instanceof Error
          ? err.message
          : 'Erro ao processar o PDF. Tente novamente.'
      );
      setProcessing(false);
    } finally {
      setUploading(false);
    }
  };

  const loadDocuments = async (id: string) => {
    try {
      setLoadingDocuments(true);
      const docs = await bulkApi.getDocuments(id);
      setDocuments(docs);
    } catch (err) {
      console.error('Erro ao carregar documentos:', err);
      setError('Erro ao carregar documentos extraídos.');
    } finally {
      setLoadingDocuments(false);
    }
  };

  const handleUploadExcel = async () => {
    if (!uploadId || excelFiles.length === 0) return;

    try {
      setUploadingExcel(true);
      setError(null);

      await bulkApi.uploadExcelFiles(uploadId, excelFiles);
      setExcelUploadComplete(true);

      // Reload documents to show matching status
      await loadDocuments(uploadId);
    } catch (err) {
      console.error('Erro ao fazer upload dos arquivos Excel:', err);
      setError('Erro ao fazer upload dos arquivos Excel. Tente novamente.');
    } finally {
      setUploadingExcel(false);
    }
  };

  const handleStartReconciliation = async () => {
    if (!uploadId) return;

    try {
      setReconciling(true);
      setError(null);

      // Start batch reconciliation (all ready documents)
      const response = await bulkApi.startReconciliation(uploadId);
      console.log(
        `Reconciliação iniciada para ${response.document_count} documentos`
      );

      // Poll for document status updates
      const pollInterval = setInterval(async () => {
        try {
          const docs = await bulkApi.getDocuments(uploadId);
          setDocuments(docs);

          // Check if all documents are completed or failed
          const stillProcessing = docs.some(
            (d) => d.status === 'reconciling' || d.reconciliation_status === 'processing'
          );

          if (!stillProcessing) {
            clearInterval(pollInterval);
            setReconciling(false);
            setReconciliationComplete(true);
          }
        } catch (err) {
          console.error('Erro ao verificar status da reconciliação:', err);
          clearInterval(pollInterval);
          setReconciling(false);
          setError('Erro ao verificar status da reconciliação.');
        }
      }, 3000); // Poll every 3 seconds
    } catch (err) {
      console.error('Erro ao iniciar reconciliação:', err);
      setError('Erro ao iniciar reconciliação. Tente novamente.');
      setReconciling(false);
    }
  };

  const handleReset = () => {
    setPdfFile(null);
    setUploadId(null);
    setUploading(false);
    setProcessing(false);
    setProgress(0);
    setCurrentStep('');
    setProcessingComplete(false);
    setDocuments([]);
    setLoadingDocuments(false);
    setExcelFiles([]);
    setUploadingExcel(false);
    setExcelUploadComplete(false);
    setReconciling(false);
    setReconciliationComplete(false);
    setError(null);
    localStorage.removeItem('bulkUploadId');
  };

  const handleViewDetails = async (reconciliationId: string) => {
    if (!uploadId) return;

    try {
      setLoadingDetails(true);
      setExpandedSections(new Set()); // Reset expanded sections
      const details = await bulkApi.getReconciliationDetails(uploadId, reconciliationId);
      setSelectedReconciliation(details);
      setShowDetailsModal(true);
    } catch (err) {
      console.error('Erro ao carregar detalhes:', err);
      setError('Erro ao carregar detalhes da reconciliação.');
    } finally {
      setLoadingDetails(false);
    }
  };

  const toggleSection = (sectionKey: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionKey)) {
      newExpanded.delete(sectionKey);
    } else {
      newExpanded.add(sectionKey);
    }
    setExpandedSections(newExpanded);
  };

  const groupMismatchesBySection = () => {
    if (!selectedReconciliation?.result_data?.mismatches) return {};

    const grouped: Record<string, any[]> = {};
    selectedReconciliation.result_data.mismatches.forEach((mismatch: any) => {
      const section = mismatch.section || 'Mismatches';
      if (!grouped[section]) {
        grouped[section] = [];
      }
      grouped[section].push(mismatch);
    });
    return grouped;
  };

  const readyDocuments = documents.filter((d) => d.status === 'ready');
  const extractedDocuments = documents.filter((d) => d.status === 'extracted');
  const matchedCount = documents.filter((d) => d.excel_matched).length;

  // Selection handlers
  const handleSelectAll = () => {
    if (selectedDocuments.size === documents.length) {
      // Unselect all
      setSelectedDocuments(new Set());
    } else {
      // Select all (use document_id, not id)
      setSelectedDocuments(new Set(documents.map(d => d.document_id)));
    }
  };

  const handleSelectDocument = (docId: string) => {
    const newSelected = new Set(selectedDocuments);
    if (newSelected.has(docId)) {
      newSelected.delete(docId);
    } else {
      newSelected.add(docId);
    }
    setSelectedDocuments(newSelected);
  };

  const handleSelectValid = () => {
    const validDocIds = documents
      .filter(d => d.excel_matched)
      .map(d => d.document_id);  // Use document_id, not id
    setSelectedDocuments(new Set(validDocIds));
  };

  const handleProcessSelected = async () => {
    if (!uploadId || selectedDocuments.size === 0) return;

    try {
      setReconciling(true);
      setError(null);

      // Convert selected document IDs to array
      const documentIds = Array.from(selectedDocuments);

      // Start reconciliation for selected documents only
      const response = await bulkApi.startReconciliation(uploadId, documentIds);
      console.log(
        `Reconciliação iniciada para ${response.document_count} documento(s) selecionado(s)`
      );

      // Poll for document status updates
      const pollInterval = setInterval(async () => {
        try {
          const docs = await bulkApi.getDocuments(uploadId);
          setDocuments(docs);

          // Check if all selected documents are completed or failed
          const selectedDocs = docs.filter((d) => documentIds.includes(d.document_id));
          const stillProcessing = selectedDocs.some(
            (d) => d.status === 'reconciling' || d.reconciliation_status === 'processing'
          );

          if (!stillProcessing) {
            clearInterval(pollInterval);
            setReconciling(false);
            setReconciliationComplete(true);

            // Clear selection after processing
            setSelectedDocuments(new Set());
          }
        } catch (err) {
          console.error('Erro ao verificar status da reconciliação:', err);
          clearInterval(pollInterval);
          setReconciling(false);
          setError('Erro ao verificar status da reconciliação.');
        }
      }, 3000); // Poll every 3 seconds
    } catch (err) {
      console.error('Erro ao iniciar reconciliação dos selecionados:', err);
      setError('Erro ao iniciar reconciliação dos documentos selecionados. Tente novamente.');
      setReconciling(false);
    }
  };

  // Count stats
  const validPagesCount = documents.filter(d => d.page_count === 2).length;
  const invalidPagesCount = documents.filter(d => d.page_count !== 2).length;
  const excelMatchedCount = documents.filter(d => d.excel_matched).length;

  return (
    <div className="space-y-8">
      {/* Progress Steps */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-8">
            {/* Step 1 */}
            <div className="flex items-center space-x-2">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full ${
                  uploadId ? 'bg-green-600' : 'bg-blue-600'
                }`}
              >
                {uploadId ? (
                  <CheckCircle2 className="w-5 h-5 text-white" />
                ) : (
                  <span className="text-white font-semibold">1</span>
                )}
              </div>
              <span className="font-medium text-gray-900">Upload PDF</span>
            </div>

            <ChevronRight className="w-5 h-5 text-gray-400" />

            {/* Step 2 */}
            <div className="flex items-center space-x-2">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full ${
                  processingComplete
                    ? 'bg-green-600'
                    : uploadId
                    ? 'bg-blue-600'
                    : 'bg-gray-300'
                }`}
              >
                {processing ? (
                  <Loader2 className="w-5 h-5 text-white animate-spin" />
                ) : processingComplete ? (
                  <CheckCircle2 className="w-5 h-5 text-white" />
                ) : (
                  <span className="text-white font-semibold">2</span>
                )}
              </div>
              <span className="font-medium text-gray-900">Processar</span>
            </div>

            <ChevronRight className="w-5 h-5 text-gray-400" />

            {/* Step 3 */}
            <div className="flex items-center space-x-2">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full ${
                  excelUploadComplete
                    ? 'bg-green-600'
                    : processingComplete
                    ? 'bg-blue-600'
                    : 'bg-gray-300'
                }`}
              >
                {excelUploadComplete ? (
                  <CheckCircle2 className="w-5 h-5 text-white" />
                ) : (
                  <span className="text-white font-semibold">3</span>
                )}
              </div>
              <span className="font-medium text-gray-900">Upload Excel</span>
            </div>

            <ChevronRight className="w-5 h-5 text-gray-400" />

            {/* Step 4 */}
            <div className="flex items-center space-x-2">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-300">
                <span className="text-white font-semibold">4</span>
              </div>
              <span className="font-medium text-gray-900">Reconciliar</span>
            </div>
          </div>

          {processingComplete && (
            <button
              onClick={handleReset}
              className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg font-medium"
            >
              Nova Carga
            </button>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-semibold text-red-900">Erro</h4>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-red-600 hover:text-red-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Step 1: PDF Upload */}
      {!uploadId && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            1. Upload do PDF Combinado
          </h2>
          <p className="text-gray-600 mb-6">
            Selecione um arquivo PDF contendo múltiplos documentos EMEI (2 páginas
            cada).
          </p>

          <input
            ref={pdfInputRef}
            type="file"
            accept=".pdf"
            onChange={handlePdfFileChange}
            className="hidden"
            disabled={uploading}
          />

          <div
            onClick={() => !uploading && pdfInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              uploading ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
            } ${
              pdfFile
                ? 'border-green-500 bg-green-50'
                : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
            }`}
          >
            {pdfFile ? (
              <div className="space-y-3">
                <CheckCircle2 className="w-12 h-12 mx-auto text-green-600" />
                <div>
                  <p className="font-medium text-gray-900">{pdfFile.name}</p>
                  <p className="text-sm text-gray-500">
                    {(pdfFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                {!uploading && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setPdfFile(null);
                    }}
                    className="text-sm text-red-600 hover:text-red-700 font-medium"
                  >
                    Remover
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <FileText className="w-12 h-12 mx-auto text-gray-400" />
                <div>
                  <p className="text-gray-700 font-medium">
                    Clique para selecionar arquivo PDF
                  </p>
                  <p className="text-sm text-gray-500">.pdf</p>
                </div>
              </div>
            )}
          </div>

          {pdfFile && (
            <div className="mt-6 flex justify-end">
              <button
                onClick={handleUploadPdf}
                disabled={uploading}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Enviando...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    <span>Fazer Upload e Processar</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Step 2: Processing Status */}
      {uploadId && processing && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            2. Processando PDF
          </h2>
          <p className="text-gray-600 mb-6">
            Extraindo e separando documentos usando o modelo Azure Document
            Intelligence...
          </p>

          <div className="space-y-4">
            <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
              <div
                className="bg-blue-600 h-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">{currentStep}</span>
              <span className="font-semibold text-gray-900">{progress}%</span>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Documents List */}
      {processingComplete && !loadingDocuments && documents.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-gray-900 flex items-center">
                <Package className="w-5 h-5 mr-2 text-blue-600" />
                {!excelUploadComplete ? '2' : '✓'}. Documentos Extraídos
              </h2>
              <p className="text-gray-600 mt-1">
                {documents.length} documentos encontrados
              </p>
            </div>
            <div className="text-sm text-gray-600">
              <span className="font-semibold text-green-600">{matchedCount}</span>{' '}
              com Excel / <span className="font-semibold">{documents.length}</span>{' '}
              total
            </div>
          </div>

          {/* Bulk Action Buttons */}
          <div className="flex items-center space-x-3 mb-4">
            <button
              onClick={handleSelectValid}
              className="px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors text-sm"
            >
              Selecionar Válidos
            </button>
            <button
              onClick={handleProcessSelected}
              disabled={selectedDocuments.size === 0}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm"
            >
              Processar Selecionados ({selectedDocuments.size})
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={selectedDocuments.size === documents.length && documents.length > 0}
                      onChange={handleSelectAll}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Tipo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Lugar
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Diretoria
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Páginas
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Excel
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  {(reconciling || reconciliationComplete) && (
                    <>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                        Match %
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                        Divergências
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                        Ações
                      </th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-center">
                      <input
                        type="checkbox"
                        checked={selectedDocuments.has(doc.document_id)}
                        onChange={() => handleSelectDocument(doc.document_id)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                      />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                      {doc.document_id}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {doc.tipo || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                      {doc.lugar || '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {doc.diretoria || '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                          doc.page_count === 2
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {doc.page_count}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      {doc.excel_matched ? (
                        <CheckCircle2 className="w-5 h-5 text-green-600 mx-auto" />
                      ) : (
                        <X className="w-5 h-5 text-gray-400 mx-auto" />
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                          doc.status === 'reconciling'
                            ? 'bg-yellow-100 text-yellow-800'
                            : doc.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : doc.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : doc.status === 'ready'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {doc.status === 'reconciling'
                          ? 'Reconciliando...'
                          : doc.status === 'completed'
                          ? 'Completo'
                          : doc.status === 'failed'
                          ? 'Falhou'
                          : doc.status === 'ready'
                          ? 'Pronto'
                          : 'Extraído'}
                      </span>
                    </td>
                    {(reconciling || reconciliationComplete) && (
                      <>
                        <td className="px-4 py-3 whitespace-nowrap text-center">
                          {doc.reconciliation_match_percentage !== null &&
                          doc.reconciliation_match_percentage !== undefined ? (
                            <span
                              className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                                doc.reconciliation_match_percentage >= 90
                                  ? 'bg-green-100 text-green-800'
                                  : doc.reconciliation_match_percentage >= 70
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {doc.reconciliation_match_percentage.toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-gray-400 text-xs">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-center">
                          {doc.reconciliation_total_mismatches !== null &&
                          doc.reconciliation_total_mismatches !== undefined ? (
                            <span className="text-sm font-medium text-gray-900">
                              {doc.reconciliation_total_mismatches}
                            </span>
                          ) : (
                            <span className="text-gray-400 text-xs">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-center">
                          {doc.reconciliation_id && doc.status === 'completed' ? (
                            <button
                              onClick={() => handleViewDetails(doc.reconciliation_id!)}
                              disabled={loadingDetails}
                              className="inline-flex items-center px-3 py-1 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors disabled:opacity-50"
                            >
                              <Eye className="w-4 h-4 mr-1" />
                              Ver Detalhes
                            </button>
                          ) : (
                            <span className="text-gray-400 text-xs">-</span>
                          )}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Legend */}
          <div className="mt-4 flex items-center space-x-6 text-sm">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span className="text-gray-700">Páginas válidas ({validPagesCount})</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              <span className="text-gray-700">Páginas inválidas ({invalidPagesCount})</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-gray-700">Excel correspondido ({excelMatchedCount})</span>
            </div>
          </div>
        </div>
      )}

      {/* Step 4: Excel Upload */}
      {processingComplete && !excelUploadComplete && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            3. Upload de Arquivos Excel
          </h2>
          <p className="text-gray-600 mb-6">
            Selecione os arquivos Excel correspondentes aos documentos extraídos.
            Os arquivos devem ter o mesmo nome do ID do documento (ex: 019382.xlsm).
          </p>

          {extractedDocuments.length > 0 && (
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-900">
                <strong>Arquivos necessários:</strong>{' '}
                {extractedDocuments.map((d) => d.document_id).join('.xlsm, ')}.xlsm
              </p>
            </div>
          )}

          <input
            ref={excelInputRef}
            type="file"
            accept=".xlsx,.xlsm,.xls"
            multiple
            onChange={handleExcelFilesChange}
            className="hidden"
            disabled={uploadingExcel}
          />

          <div
            onClick={() => !uploadingExcel && excelInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              uploadingExcel ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
            } ${
              excelFiles.length > 0
                ? 'border-green-500 bg-green-50'
                : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
            }`}
          >
            {excelFiles.length > 0 ? (
              <div className="space-y-3">
                <CheckCircle2 className="w-12 h-12 mx-auto text-green-600" />
                <div>
                  <p className="font-medium text-gray-900">
                    {excelFiles.length} arquivo(s) selecionado(s)
                  </p>
                  <div className="mt-2 text-sm text-gray-600 space-y-1">
                    {excelFiles.map((file, idx) => (
                      <div key={idx}>{file.name}</div>
                    ))}
                  </div>
                </div>
                {!uploadingExcel && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setExcelFiles([]);
                    }}
                    className="text-sm text-red-600 hover:text-red-700 font-medium"
                  >
                    Remover Todos
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <FileSpreadsheet className="w-12 h-12 mx-auto text-gray-400" />
                <div>
                  <p className="text-gray-700 font-medium">
                    Clique para selecionar arquivos Excel
                  </p>
                  <p className="text-sm text-gray-500">
                    .xlsx, .xlsm, .xls (múltiplos arquivos)
                  </p>
                </div>
              </div>
            )}
          </div>

          {excelFiles.length > 0 && (
            <div className="mt-6 flex justify-end">
              <button
                onClick={handleUploadExcel}
                disabled={uploadingExcel}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {uploadingExcel ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Fazendo Upload...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    <span>Fazer Upload de Excel</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Step 5: Ready for Reconciliation */}
      {excelUploadComplete && readyDocuments.length > 0 && !reconciling && !reconciliationComplete && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex items-center space-x-3">
            <CheckCircle2 className="w-6 h-6 text-green-600" />
            <div className="flex-1">
              <h3 className="font-semibold text-green-900">Pronto para Reconciliar!</h3>
              <p className="text-sm text-green-700 mt-1">
                {readyDocuments.length} documento(s) com PDF e Excel prontos para
                reconciliação em lote.
              </p>
            </div>
            <button
              className="px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              onClick={handleStartReconciliation}
              disabled={reconciling}
            >
              {reconciling ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Reconciliando...</span>
                </>
              ) : (
                <span>Iniciar Reconciliação</span>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 6: Reconciliation In Progress */}
      {reconciling && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <div className="flex items-center space-x-3">
            <Loader2 className="w-6 h-6 text-yellow-600 animate-spin" />
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-900">Reconciliação em Andamento</h3>
              <p className="text-sm text-yellow-700 mt-1">
                Processando documentos... A tabela será atualizada automaticamente.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Step 7: Reconciliation Complete */}
      {reconciliationComplete && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-center space-x-3">
            <CheckCircle2 className="w-6 h-6 text-blue-600" />
            <div className="flex-1">
              <h3 className="font-semibold text-blue-900">Reconciliação Concluída!</h3>
              <p className="text-sm text-blue-700 mt-1">
                {documents.filter((d) => d.status === 'completed').length} documento(s) reconciliados com sucesso.
                Verifique a tabela acima para ver os resultados.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Reconciliation Details Modal */}
      {showDetailsModal && selectedReconciliation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="bg-gray-50 border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  Detalhes da Reconciliação
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Documento: {selectedReconciliation.document_id}
                </p>
              </div>
              <button
                onClick={() => {
                  setShowDetailsModal(false);
                  setSelectedReconciliation(null);
                }}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <XCircle className="w-6 h-6" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
              {/* Summary Cards - matching SingleReconciliation format */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                {/* Match Percentage */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Taxa de Correspondência
                      </p>
                      <p className={`text-3xl font-bold mt-2 ${
                        selectedReconciliation.overall_match_percentage >= 90
                          ? 'text-green-600'
                          : selectedReconciliation.overall_match_percentage >= 70
                          ? 'text-yellow-600'
                          : 'text-red-600'
                      }`}>
                        {selectedReconciliation.overall_match_percentage?.toFixed(2)}%
                      </p>
                    </div>
                    <div className="bg-green-100 rounded-full p-3">
                      <CheckCircle2 className="w-8 h-8 text-green-600" />
                    </div>
                  </div>
                </div>

                {/* Cells Compared */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Células Comparadas
                      </p>
                      <p className="text-3xl font-bold text-blue-600 mt-2">
                        {selectedReconciliation.overall_cells_compared || 0}
                      </p>
                    </div>
                    <div className="bg-blue-100 rounded-full p-3">
                      <FileSpreadsheet className="w-8 h-8 text-blue-600" />
                    </div>
                  </div>
                </div>

                {/* Mismatches */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Divergências
                      </p>
                      <p className="text-3xl font-bold text-orange-600 mt-2">
                        {selectedReconciliation.total_mismatches || 0}
                      </p>
                    </div>
                    <div className="bg-orange-100 rounded-full p-3">
                      <AlertTriangle className="w-8 h-8 text-orange-600" />
                    </div>
                  </div>
                </div>

                {/* ID Match & PDF Confidence */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <div>
                    <p className="text-sm font-medium text-gray-600 mb-3">
                      Status
                    </p>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">ID Match:</span>
                        <span className={`text-sm font-semibold ${
                          selectedReconciliation.id_match ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {selectedReconciliation.id_match ? 'Sim' : 'Não'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">PDF OK:</span>
                        <span className={`text-sm font-semibold ${
                          selectedReconciliation.pdf_confidence_ok ? 'text-green-600' : 'text-yellow-600'
                        }`}>
                          {selectedReconciliation.pdf_confidence_ok ? 'Sim' : 'Baixa'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Files Section - more compact */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex items-center space-x-2">
                    <FileSpreadsheet className="w-5 h-5 text-green-600 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <span className="text-xs text-gray-500 block">Excel:</span>
                      <span className="text-sm font-medium text-gray-900 truncate block">
                        {selectedReconciliation.excel_filename}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <FileText className="w-5 h-5 text-red-600 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <span className="text-xs text-gray-500 block">PDF:</span>
                      <span className="text-sm font-medium text-gray-900 truncate block">
                        {selectedReconciliation.pdf_filename}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Mismatches Detail - Collapsible Sections */}
              {selectedReconciliation.total_mismatches > 0 && (
                <div>
                  <h2 className="text-xl font-bold text-gray-900 mb-4">
                    Detalhes das Divergências
                  </h2>

                  <div className="space-y-4">
                    {Object.entries(groupMismatchesBySection()).map(
                      ([section, mismatches]) => (
                        <div
                          key={section}
                          className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
                        >
                          <button
                            onClick={() => toggleSection(section)}
                            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                          >
                            <div className="flex items-center space-x-3">
                              <AlertTriangle className="w-5 h-5 text-orange-600" />
                              <div className="text-left">
                                <h3 className="font-semibold text-gray-900">
                                  {section}
                                </h3>
                                <p className="text-sm text-gray-600">
                                  {mismatches.length}{' '}
                                  {mismatches.length === 1
                                    ? 'divergência'
                                    : 'divergências'}
                                </p>
                              </div>
                            </div>
                            {expandedSections.has(section) ? (
                              <ChevronUp className="w-5 h-5 text-gray-400" />
                            ) : (
                              <ChevronDown className="w-5 h-5 text-gray-400" />
                            )}
                          </button>

                          {expandedSections.has(section) && (
                            <div className="border-t border-gray-200">
                              <div className="overflow-x-auto">
                                <table className="w-full">
                                  <thead className="bg-gray-50">
                                    <tr>
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Campo
                                      </th>
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Dia/Período
                                      </th>
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Coluna Excel
                                      </th>
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Célula Excel
                                      </th>
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Valor Excel
                                      </th>
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Valor PDF
                                      </th>
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Imagem PDF
                                      </th>
                                    </tr>
                                  </thead>
                                  <tbody className="bg-white divide-y divide-gray-200">
                                    {mismatches.map((mismatch: any, idx: number) => (
                                      <tr key={idx} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                          {mismatch.field}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                          {mismatch.row_label || mismatch.row_identifier || mismatch.day_or_period || '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                          {mismatch.column_name || '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                          {mismatch.excel_cell || mismatch.excel_cell_ref ? (
                                            <span className="px-2 py-1 bg-green-100 text-green-800 rounded font-semibold">
                                              {mismatch.excel_cell || mismatch.excel_cell_ref}
                                            </span>
                                          ) : (
                                            <span className="text-gray-400">-</span>
                                          )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                                            {mismatch.excel_value ?? 'N/A'}
                                          </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                          <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded">
                                            {mismatch.pdf_value ?? 'N/A'}
                                          </span>
                                        </td>
                                        <td className="px-6 py-4 text-sm">
                                          {mismatch.pdf_image_base64 ? (
                                            <img
                                              src={mismatch.pdf_image_base64}
                                              alt="PDF Cell"
                                              className="max-w-xs max-h-32 border border-gray-300 rounded hover:opacity-80 transition-opacity cursor-pointer"
                                              title="Clique para ampliar"
                                              onClick={() => setZoomedImage(mismatch.pdf_image_base64)}
                                            />
                                          ) : (
                                            <span className="text-gray-400 text-xs">Sem imagem</span>
                                          )}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}

              {/* No Mismatches */}
              {selectedReconciliation.total_mismatches === 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-8 text-center">
                  <CheckCircle2 className="w-16 h-16 text-green-600 mx-auto mb-3" />
                  <h3 className="text-lg font-semibold text-green-900">100% de Match!</h3>
                  <p className="text-sm text-green-700 mt-2">
                    Não foram encontradas divergências entre o Excel e o PDF.
                  </p>
                </div>
              )}

              {/* PDF Viewer Section */}
              {selectedReconciliation && uploadId && (
                <div className="mt-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Visualizador PDF</h3>
                  <PDFViewer
                    uploadId={uploadId}
                    documentId={selectedReconciliation.document_id}
                  />
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end">
              <button
                onClick={() => {
                  setShowDetailsModal(false);
                  setSelectedReconciliation(null);
                }}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Image Zoom Modal */}
      {zoomedImage && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
          onClick={() => setZoomedImage(null)}
        >
          <div className="relative max-w-7xl max-h-screen p-4">
            <button
              onClick={() => setZoomedImage(null)}
              className="absolute top-2 right-2 bg-white rounded-full p-2 hover:bg-gray-100 transition-colors"
            >
              <X className="w-6 h-6 text-gray-700" />
            </button>
            <img
              src={zoomedImage}
              alt="Zoomed PDF Cell"
              className="max-w-full max-h-screen object-contain"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default BulkUpload;
