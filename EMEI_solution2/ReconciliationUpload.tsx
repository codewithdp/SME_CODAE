/**
 * ReconciliationUpload Component
 * Main upload page for Excel and PDF files
 */

import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { Upload, FileSpreadsheet, FileText, AlertCircle, CheckCircle } from 'lucide-react';

// API client
import { uploadReconciliationFiles } from '../api/reconciliationApi';

// Types
interface UploadedFile {
  file: File;
  preview?: string;
}

interface ValidationResult {
  isValid: boolean;
  message: string;
}

const ReconciliationUpload: React.FC = () => {
  const navigate = useNavigate();
  
  // State
  const [excelFile, setExcelFile] = useState<UploadedFile | null>(null);
  const [pdfFile, setPdfFile] = useState<UploadedFile | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<ValidationResult>({ isValid: false, message: '' });

  // Excel dropzone
  const onDropExcel = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setExcelFile({ file });
      validateFiles({ file }, pdfFile?.file);
      setError(null);
    }
  }, [pdfFile]);

  const {
    getRootProps: getExcelRootProps,
    getInputProps: getExcelInputProps,
    isDragActive: isExcelDragActive
  } = useDropzone({
    onDrop: onDropExcel,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel.sheet.macroEnabled.12': ['.xlsm'],
      'application/vnd.ms-excel': ['.xls']
    },
    multiple: false,
    maxSize: 50 * 1024 * 1024 // 50MB
  });

  // PDF dropzone
  const onDropPdf = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setPdfFile({ file });
      validateFiles(excelFile?.file, { file });
      setError(null);
    }
  }, [excelFile]);

  const {
    getRootProps: getPdfRootProps,
    getInputProps: getPdfInputProps,
    isDragActive: isPdfDragActive
  } = useDropzone({
    onDrop: onDropPdf,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: false,
    maxSize: 50 * 1024 * 1024 // 50MB
  });

  // Validation logic
  const validateFiles = (excel: UploadedFile | File | undefined, pdf: UploadedFile | File | undefined) => {
    if (!excel || !pdf) {
      setValidation({
        isValid: false,
        message: 'Please upload both Excel and PDF files'
      });
      return;
    }

    // Extract EMEI code from filenames
    const excelFilename = 'file' in excel ? excel.file.name : excel.name;
    const pdfFilename = 'file' in pdf ? pdf.file.name : pdf.name;
    
    // Simple validation: check if filenames contain similar IDs
    // In real implementation, this would be more sophisticated
    const excelMatch = excelFilename.match(/\d{6}/);
    const pdfMatch = pdfFilename.match(/\d{6}/);

    if (excelMatch && pdfMatch) {
      if (excelMatch[0] === pdfMatch[0]) {
        setValidation({
          isValid: true,
          message: `✓ Files match - EMEI: ${excelMatch[0]}`
        });
      } else {
        setValidation({
          isValid: false,
          message: `⚠ Warning: File IDs don't match (Excel: ${excelMatch[0]}, PDF: ${pdfMatch[0]})`
        });
      }
    } else {
      setValidation({
        isValid: true,
        message: '⚠ Could not verify file IDs from filenames'
      });
    }
  };

  // Handle upload
  const handleUpload = async () => {
    if (!excelFile || !pdfFile) {
      setError('Please select both files');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const result = await uploadReconciliationFiles(excelFile.file, pdfFile.file);
      
      // Navigate to processing page
      navigate(`/reconciliation/${result.reconciliation_id}/processing`);
    } catch (err: any) {
      setError(err.message || 'Failed to upload files. Please try again.');
      console.error('Upload error:', err);
    } finally {
      setIsUploading(false);
    }
  };

  // Remove file
  const removeExcelFile = () => {
    setExcelFile(null);
    validateFiles(undefined, pdfFile?.file);
  };

  const removePdfFile = () => {
    setPdfFile(null);
    validateFiles(excelFile?.file, undefined);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Excel-PDF Reconciliation
          </h1>
          <p className="text-gray-600">
            Upload your Excel and PDF files to start the reconciliation process
          </p>
        </div>

        {/* Upload Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Excel Upload */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center mb-4">
              <FileSpreadsheet className="w-6 h-6 text-green-600 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">Excel File</h2>
            </div>

            {!excelFile ? (
              <div
                {...getExcelRootProps()}
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                  transition-colors duration-200
                  ${isExcelDragActive 
                    ? 'border-green-500 bg-green-50' 
                    : 'border-gray-300 hover:border-green-400 hover:bg-gray-50'
                  }
                `}
              >
                <input {...getExcelInputProps()} />
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                {isExcelDragActive ? (
                  <p className="text-green-600 font-medium">Drop Excel file here</p>
                ) : (
                  <>
                    <p className="text-gray-600 mb-2">
                      Drag & drop Excel file here, or click to select
                    </p>
                    <p className="text-sm text-gray-500">
                      Supports: .xlsx, .xlsm, .xls (max 50MB)
                    </p>
                  </>
                )}
              </div>
            ) : (
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    <FileSpreadsheet className="w-5 h-5 text-green-600 mt-0.5" />
                    <div>
                      <p className="font-medium text-gray-900">{excelFile.file.name}</p>
                      <p className="text-sm text-gray-500">
                        {(excelFile.file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={removeExcelFile}
                    className="text-red-600 hover:text-red-700 text-sm font-medium"
                  >
                    Remove
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* PDF Upload */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center mb-4">
              <FileText className="w-6 h-6 text-red-600 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">PDF File</h2>
            </div>

            {!pdfFile ? (
              <div
                {...getPdfRootProps()}
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                  transition-colors duration-200
                  ${isPdfDragActive 
                    ? 'border-red-500 bg-red-50' 
                    : 'border-gray-300 hover:border-red-400 hover:bg-gray-50'
                  }
                `}
              >
                <input {...getPdfInputProps()} />
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                {isPdfDragActive ? (
                  <p className="text-red-600 font-medium">Drop PDF file here</p>
                ) : (
                  <>
                    <p className="text-gray-600 mb-2">
                      Drag & drop PDF file here, or click to select
                    </p>
                    <p className="text-sm text-gray-500">
                      Supports: .pdf (max 50MB)
                    </p>
                  </>
                )}
              </div>
            ) : (
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    <FileText className="w-5 h-5 text-red-600 mt-0.5" />
                    <div>
                      <p className="font-medium text-gray-900">{pdfFile.file.name}</p>
                      <p className="text-sm text-gray-500">
                        {(pdfFile.file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={removePdfFile}
                    className="text-red-600 hover:text-red-700 text-sm font-medium"
                  >
                    Remove
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Validation Message */}
        {(excelFile || pdfFile) && (
          <div className={`
            mb-6 p-4 rounded-lg flex items-start space-x-3
            ${validation.isValid 
              ? 'bg-green-50 border border-green-200' 
              : 'bg-yellow-50 border border-yellow-200'
            }
          `}>
            {validation.isValid ? (
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
            ) : (
              <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
            )}
            <p className={`text-sm ${validation.isValid ? 'text-green-800' : 'text-yellow-800'}`}>
              {validation.message}
            </p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-center space-x-4">
          <button
            onClick={() => {
              setExcelFile(null);
              setPdfFile(null);
              setValidation({ isValid: false, message: '' });
              setError(null);
            }}
            className="px-6 py-3 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors"
            disabled={isUploading}
          >
            Clear All
          </button>
          
          <button
            onClick={handleUpload}
            disabled={!excelFile || !pdfFile || isUploading}
            className={`
              px-8 py-3 rounded-lg font-medium transition-colors
              ${excelFile && pdfFile && !isUploading
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }
            `}
          >
            {isUploading ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Uploading...
              </span>
            ) : (
              'Start Reconciliation'
            )}
          </button>
        </div>

        {/* Info Section */}
        <div className="mt-12 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">
            How it works
          </h3>
          <ol className="space-y-2 text-sm text-blue-800">
            <li className="flex items-start">
              <span className="font-bold mr-2">1.</span>
              <span>Upload your Excel file (EMEI sheet) and corresponding PDF document</span>
            </li>
            <li className="flex items-start">
              <span className="font-bold mr-2">2.</span>
              <span>The system will automatically extract data from both files</span>
            </li>
            <li className="flex items-start">
              <span className="font-bold mr-2">3.</span>
              <span>All three sections will be compared: enrollment numbers, frequency data, and daily attendance</span>
            </li>
            <li className="flex items-start">
              <span className="font-bold mr-2">4.</span>
              <span>You'll receive a detailed report showing any mismatches with cell-level details</span>
            </li>
          </ol>
        </div>
      </div>
    </div>
  );
};

export default ReconciliationUpload;
