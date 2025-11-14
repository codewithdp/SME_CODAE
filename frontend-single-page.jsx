import React, { useState } from 'react';
import { Upload, FileSpreadsheet, FileText, CheckCircle2, AlertCircle, Download, TrendingUp, AlertTriangle, ChevronDown, ChevronUp, Loader2, X } from 'lucide-react';

// Sample reconciliation result data
const sampleResult = {
  reconciliation_id: "abc-123-def-456",
  excel_filename: "019382.xlsm",
  pdf_filename: "EMEI_test1.pdf",
  emei_id_excel: "019382",
  emei_id_pdf: "019382",
  id_match: true,
  pdf_confidence_ok: true,
  min_pdf_confidence: 0.85,
  excel_row_count: 63,
  pdf_row_count: 63,
  row_count_match: true,
  total_cells_compared: 315,
  total_mismatches: 14,
  overall_match_percentage: 95.6,
  status: 'success',
  processing_time_seconds: 87.3,
  timestamp: new Date().toISOString(),
  sections: [
    {
      section_name: "Enrollment Data",
      section_number: 1,
      match_percentage: 94.2,
      total_rows: 21,
      matching_rows: 17,
      mismatched_rows: 4,
      row_mismatches: [
        {
          row_index: 0,
          row_label: "INTEGRAL",
          cell_mismatches: [
            {
              column: "1º Ano",
              excel_value: 45,
              pdf_value: 44,
              excel_cell: "C10",
              pdf_cell: "Page 1, Row 10, Col C",
              match: false
            },
            {
              column: "2º Ano",
              excel_value: 38,
              pdf_value: 39,
              excel_cell: "D10",
              pdf_cell: "Page 1, Row 10, Col D",
              match: false
            }
          ]
        },
        {
          row_index: 1,
          row_label: "MATUTINO",
          cell_mismatches: [
            {
              column: "3º Ano",
              excel_value: 52,
              pdf_value: 51,
              excel_cell: "E11",
              pdf_cell: "Page 1, Row 11, Col E",
              match: false
            },
            {
              column: "4º Ano",
              excel_value: 41,
              pdf_value: 42,
              excel_cell: "F11",
              pdf_cell: "Page 1, Row 11, Col F",
              match: false
            }
          ]
        }
      ]
    },
    {
      section_name: "Frequency",
      section_number: 2,
      match_percentage: 100,
      total_rows: 21,
      matching_rows: 21,
      mismatched_rows: 0,
      row_mismatches: []
    },
    {
      section_name: "Daily Attendance",
      section_number: 3,
      match_percentage: 90.5,
      total_rows: 21,
      matching_rows: 19,
      mismatched_rows: 2,
      row_mismatches: [
        {
          row_index: 0,
          row_label: "Monday",
          cell_mismatches: [
            {
              column: "Present",
              excel_value: 285,
              pdf_value: 284,
              excel_cell: "C45",
              pdf_cell: "Page 2, Row 5, Col C",
              match: false
            }
          ]
        },
        {
          row_index: 1,
          row_label: "Friday",
          cell_mismatches: [
            {
              column: "Present",
              excel_value: 278,
              pdf_value: 277,
              excel_cell: "C49",
              pdf_cell: "Page 2, Row 9, Col C",
              match: false
            }
          ]
        }
      ]
    }
  ]
};

function App() {
  const [excelFile, setExcelFile] = useState(null);
  const [pdfFile, setPdfFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [result, setResult] = useState(null);

  const simulateProcessing = () => {
    setProcessing(true);
    setProgress(0);
    setResult(null);
    
    const steps = [
      { percent: 10, text: 'Validating files...' },
      { percent: 25, text: 'Parsing Excel file...' },
      { percent: 50, text: 'Processing PDF with Azure Document Intelligence...' },
      { percent: 75, text: 'Comparing Excel and PDF data...' },
      { percent: 90, text: 'Generating reports...' },
      { percent: 100, text: 'Complete!' }
    ];

    let currentStepIndex = 0;
    
    const interval = setInterval(() => {
      setProgress(prev => {
        const newProgress = prev + 2;
        
        // Update step text
        const nextStep = steps.find(s => newProgress >= s.percent);
        if (nextStep && nextStep.text !== currentStep) {
          setCurrentStep(nextStep.text);
        }
        
        if (newProgress >= 100) {
          clearInterval(interval);
          setTimeout(() => {
            setProcessing(false);
            setResult(sampleResult);
          }, 500);
          return 100;
        }
        return newProgress;
      });
    }, 50);
  };

  const handleReset = () => {
    setExcelFile(null);
    setPdfFile(null);
    setResult(null);
    setProgress(0);
    setCurrentStep('');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-600 p-2 rounded-lg">
                <FileSpreadsheet className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">EMEI Reconciliation</h1>
                <p className="text-xs text-gray-500">Excel ↔ PDF Validator</p>
              </div>
            </div>
            {result && (
              <button 
                onClick={handleReset}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                New Reconciliation
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        
        {/* Upload Section - Always visible */}
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Upload Files</h2>
            <p className="text-gray-600">Select your Excel EMEI sheet and corresponding PDF document.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Excel Upload */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <FileSpreadsheet className="w-5 h-5 mr-2 text-green-600" />
                Excel File
              </h3>
              <div 
                onClick={() => !processing && setExcelFile({ name: '019382.xlsm', size: 2458624 })}
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  processing ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
                } ${
                  excelFile ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
                }`}
              >
                {excelFile ? (
                  <div className="space-y-3">
                    <CheckCircle2 className="w-12 h-12 mx-auto text-green-600" />
                    <div>
                      <p className="font-medium text-gray-900">{excelFile.name}</p>
                      <p className="text-sm text-gray-500">{(excelFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                    {!processing && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setExcelFile(null); }}
                        className="text-sm text-red-600 hover:text-red-700 font-medium"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3">
                    <FileSpreadsheet className="w-12 h-12 mx-auto text-gray-400" />
                    <div>
                      <p className="text-gray-700 font-medium">Click to select Excel file</p>
                      <p className="text-sm text-gray-500">.xlsx, .xlsm, .xls</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* PDF Upload */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <FileText className="w-5 h-5 mr-2 text-red-600" />
                PDF File
              </h3>
              <div 
                onClick={() => !processing && setPdfFile({ name: 'EMEI_test1.pdf', size: 1856432 })}
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  processing ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
                } ${
                  pdfFile ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
                }`}
              >
                {pdfFile ? (
                  <div className="space-y-3">
                    <CheckCircle2 className="w-12 h-12 mx-auto text-green-600" />
                    <div>
                      <p className="font-medium text-gray-900">{pdfFile.name}</p>
                      <p className="text-sm text-gray-500">{(pdfFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                    {!processing && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setPdfFile(null); }}
                        className="text-sm text-red-600 hover:text-red-700 font-medium"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3">
                    <FileText className="w-12 h-12 mx-auto text-gray-400" />
                    <div>
                      <p className="text-gray-700 font-medium">Click to select PDF file</p>
                      <p className="text-sm text-gray-500">.pdf</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Process Button */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-semibold text-gray-900">
                  {processing ? 'Processing...' : result ? 'Processing Complete' : 'Ready to process?'}
                </h4>
                <p className="text-sm text-gray-600 mt-1">
                  {processing ? currentStep : result ? 'Scroll down to see detailed results' : 'Both files selected. Click to start reconciliation.'}
                </p>
              </div>
              <button
                onClick={simulateProcessing}
                disabled={!excelFile || !pdfFile || processing}
                className="px-8 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {processing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    <span>Process Files</span>
                  </>
                )}
              </button>
            </div>

            {/* Progress Bar */}
            {processing && (
              <div className="mt-4">
                <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-blue-600 h-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-sm text-gray-600 mt-2 text-center">{progress}% complete</p>
              </div>
            )}
          </div>
        </div>

        {/* Results Section - Only shown after processing */}
        {result && (
          <div className="space-y-6 animate-fadeIn">
            {/* Divider */}
            <div className="border-t-2 border-gray-300 pt-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Results</h2>
              <p className="text-gray-600">Detailed reconciliation analysis and mismatches</p>
            </div>

            {/* Status Card */}
            <div className="bg-green-50 border border-green-200 rounded-lg shadow-sm p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4">
                  <CheckCircle2 className="w-8 h-8 text-green-600" />
                  <div>
                    <h3 className="text-xl font-bold text-gray-900 mb-1">Reconciliation Complete</h3>
                    <div className="space-y-1 text-sm text-gray-600">
                      <div className="flex items-center space-x-2">
                        <FileSpreadsheet className="w-4 h-4" />
                        <span className="font-medium">{result.excel_filename}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <FileText className="w-4 h-4" />
                        <span className="font-medium">{result.pdf_filename}</span>
                      </div>
                      <p className="text-xs">Processed in {result.processing_time_seconds.toFixed(2)}s</p>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-gray-900">{result.overall_match_percentage.toFixed(1)}%</div>
                  <p className="text-sm text-gray-600">Match Rate</p>
                </div>
              </div>
            </div>

            {/* Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <MetricCard
                label="Match Percentage"
                value={`${result.overall_match_percentage.toFixed(1)}%`}
                icon={TrendingUp}
                color="green"
                description={`${result.total_cells_compared - result.total_mismatches} of ${result.total_cells_compared} cells`}
              />
              <MetricCard
                label="Total Mismatches"
                value={result.total_mismatches}
                icon={AlertTriangle}
                color="red"
                description={`Across ${result.sections.length} sections`}
              />
              <MetricCard
                label="Sections"
                value={result.sections.length}
                icon={CheckCircle2}
                color="blue"
                description={`${result.sections.filter(s => s.match_percentage === 100).length} perfect matches`}
              />
              <MetricCard
                label="PDF Confidence"
                value="High"
                icon={CheckCircle2}
                color="green"
                description={`${(result.min_pdf_confidence * 100).toFixed(0)}% threshold`}
              />
            </div>

            {/* Detailed Mismatches */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold text-gray-900 flex items-center">
                  <AlertCircle className="w-6 h-6 mr-2 text-red-600" />
                  Detailed Mismatches ({result.total_mismatches})
                </h3>
                <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center space-x-2">
                  <Download className="w-4 h-4" />
                  <span>Download Report</span>
                </button>
              </div>

              {result.sections.map((section, idx) => (
                section.mismatched_rows > 0 && <MismatchSection key={idx} section={section} />
              ))}

              {result.total_mismatches === 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-12 text-center">
                  <CheckCircle2 className="w-16 h-16 text-green-600 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-green-900 mb-2">Perfect Match! 🎉</h3>
                  <p className="text-green-700">All cells match between Excel and PDF.</p>
                </div>
              )}
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-4 mt-12">
        <div className="max-w-7xl mx-auto px-6">
          <p className="text-center text-sm text-gray-500">
            EMEI Reconciliation System • Single Page Demo
          </p>
        </div>
      </footer>
    </div>
  );
}

function MetricCard({ label, value, icon: Icon, color, description }) {
  const colors = {
    green: 'bg-green-50 border-green-200 text-green-700',
    red: 'bg-red-50 border-red-200 text-red-700',
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
  };

  const iconColors = {
    green: 'text-green-600',
    red: 'text-red-600',
    blue: 'text-blue-600',
  };

  return (
    <div className={`rounded-lg shadow-sm border p-6 ${colors[color]}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium opacity-80 mb-1">{label}</p>
          <p className="text-3xl font-bold mb-1">{value}</p>
          <p className="text-xs opacity-70">{description}</p>
        </div>
        <Icon className={`w-8 h-8 ${iconColors[color]}`} />
      </div>
    </div>
  );
}

function MismatchSection({ section }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between hover:bg-gray-50 -m-6 p-6 rounded-lg transition-colors"
      >
        <div className="flex items-center space-x-4">
          <div className="p-2 rounded-lg bg-red-100">
            <AlertCircle className="w-5 h-5 text-red-600" />
          </div>
          <div className="text-left">
            <h4 className="text-lg font-semibold text-gray-900">
              Section {section.section_number}: {section.section_name}
            </h4>
            <p className="text-sm text-gray-600">
              {section.mismatched_rows} mismatched rows • {section.total_rows} total rows
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <div className="text-right">
            <div className="text-2xl font-bold text-red-600">{section.match_percentage.toFixed(1)}%</div>
            <p className="text-xs text-gray-600">Match</p>
          </div>
          {expanded ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
        </div>
      </button>

      {expanded && section.row_mismatches.length > 0 && (
        <div className="mt-6 space-y-4">
          {section.row_mismatches.map((row, idx) => (
            <div key={idx} className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                <h5 className="font-semibold text-gray-900">Row: {row.row_label}</h5>
                <p className="text-sm text-gray-600">{row.cell_mismatches.length} cell mismatches</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Column</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">
                        <div className="flex items-center">
                          <FileSpreadsheet className="w-4 h-4 mr-1 text-green-600" />
                          Excel
                        </div>
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">
                        <div className="flex items-center">
                          <FileText className="w-4 h-4 mr-1 text-red-600" />
                          PDF
                        </div>
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Location</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {row.cell_mismatches.map((cell, cellIdx) => (
                      <tr key={cellIdx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap font-medium text-gray-900">{cell.column}</td>
                        <td className="px-4 py-3">
                          <code className="px-2 py-1 bg-green-50 text-green-800 rounded text-sm font-mono border border-green-200">
                            {cell.excel_value}
                          </code>
                        </td>
                        <td className="px-4 py-3">
                          <code className="px-2 py-1 bg-red-50 text-red-800 rounded text-sm font-mono border border-red-200">
                            {cell.pdf_value}
                          </code>
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-xs space-y-1">
                            <div className="flex items-center text-green-700">
                              <FileSpreadsheet className="w-3 h-3 mr-1" />
                              <span className="font-mono font-semibold">{cell.excel_cell}</span>
                            </div>
                            <div className="flex items-center text-red-700">
                              <FileText className="w-3 h-3 mr-1" />
                              <span className="font-mono">{cell.pdf_cell}</span>
                            </div>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
