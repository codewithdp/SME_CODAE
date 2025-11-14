import { useState, useRef } from 'react';
import {
  Upload,
  FileSpreadsheet,
  FileText,
  CheckCircle2,
  Download,
  TrendingUp,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Loader2,
  X,
  AlertCircle,
} from 'lucide-react';
import { reconciliationApi } from './api/reconciliation';
import { ReconciliationStatus, ReconciliationResult } from './types';

interface FileInfo {
  file: File;
  name: string;
  size: number;
}

function App() {
  const [excelFile, setExcelFile] = useState<FileInfo | null>(null);
  const [pdfFile, setPdfFile] = useState<FileInfo | null>(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [result, setResult] = useState<ReconciliationResult | null>(null);
  const [reconciliationId, setReconciliationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const excelInputRef = useRef<HTMLInputElement>(null);
  const pdfInputRef = useRef<HTMLInputElement>(null);

  const handleExcelFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setExcelFile({
        file,
        name: file.name,
        size: file.size,
      });
    }
  };

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

  const handleProcess = async () => {
    if (!excelFile || !pdfFile) return;

    try {
      setProcessing(true);
      setError(null);
      setProgress(0);
      setCurrentStep('Enviando arquivos...');

      // Upload files
      const uploadResponse = await reconciliationApi.uploadFiles(
        excelFile.file,
        pdfFile.file
      );

      setReconciliationId(uploadResponse.reconciliation_id);
      setCurrentStep('Processando reconciliação...');

      // Poll for status
      await reconciliationApi.pollStatus(
        uploadResponse.reconciliation_id,
        (status: ReconciliationStatus) => {
          setProgress(status.progress_percentage);
          setCurrentStep(status.current_step);

          if (status.status === 'completed' && status.result) {
            setResult(status.result);
            setProcessing(false);
          }
        }
      );
    } catch (err) {
      console.error('Erro ao processar:', err);
      setError(
        err instanceof Error
          ? err.message
          : 'Erro ao processar os arquivos. Tente novamente.'
      );
      setProcessing(false);
    }
  };

  const handleDownloadReport = async () => {
    if (!reconciliationId) return;

    try {
      const blob = await reconciliationApi.downloadReport(reconciliationId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reconciliacao_${reconciliationId}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Erro ao baixar relatório:', err);
      setError('Erro ao baixar o relatório. Tente novamente.');
    }
  };

  const handleReset = () => {
    setExcelFile(null);
    setPdfFile(null);
    setProcessing(false);
    setProgress(0);
    setCurrentStep('');
    setResult(null);
    setReconciliationId(null);
    setError(null);
    setExpandedSections(new Set());
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
    if (!result?.mismatches) return {};

    const grouped: Record<string, typeof result.mismatches> = {};
    result.mismatches.forEach((mismatch) => {
      if (!grouped[mismatch.section]) {
        grouped[mismatch.section] = [];
      }
      grouped[mismatch.section].push(mismatch);
    });
    return grouped;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Sistema de Reconciliação EMEI
              </h1>
              <p className="text-gray-600 mt-1">
                Secretaria Municipal de Educação - SME
              </p>
            </div>
            {result && (
              <button
                onClick={handleReset}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                Nova Reconciliação
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Upload Section */}
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Upload de Arquivos
            </h2>
            <p className="text-gray-600">
              Selecione a planilha Excel EMEI e o documento PDF correspondente.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Excel Upload */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <FileSpreadsheet className="w-5 h-5 mr-2 text-green-600" />
                Arquivo Excel
              </h3>
              <input
                ref={excelInputRef}
                type="file"
                accept=".xlsx,.xlsm,.xls"
                onChange={handleExcelFileChange}
                className="hidden"
                disabled={processing}
              />
              <div
                onClick={() => !processing && excelInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  processing ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
                } ${
                  excelFile
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
                }`}
              >
                {excelFile ? (
                  <div className="space-y-3">
                    <CheckCircle2 className="w-12 h-12 mx-auto text-green-600" />
                    <div>
                      <p className="font-medium text-gray-900">
                        {excelFile.name}
                      </p>
                      <p className="text-sm text-gray-500">
                        {(excelFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                    {!processing && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setExcelFile(null);
                        }}
                        className="text-sm text-red-600 hover:text-red-700 font-medium"
                      >
                        Remover
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3">
                    <FileSpreadsheet className="w-12 h-12 mx-auto text-gray-400" />
                    <div>
                      <p className="text-gray-700 font-medium">
                        Clique para selecionar arquivo Excel
                      </p>
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
                Arquivo PDF
              </h3>
              <input
                ref={pdfInputRef}
                type="file"
                accept=".pdf"
                onChange={handlePdfFileChange}
                className="hidden"
                disabled={processing}
              />
              <div
                onClick={() => !processing && pdfInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  processing ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
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
                    {!processing && (
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
            </div>
          </div>

          {/* Process Button */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-semibold text-gray-900">
                  {processing
                    ? 'Processando...'
                    : result
                    ? 'Processamento Concluído'
                    : 'Pronto para processar?'}
                </h4>
                <p className="text-sm text-gray-600 mt-1">
                  {processing
                    ? currentStep
                    : result
                    ? 'Role para baixo para ver os resultados detalhados'
                    : 'Ambos os arquivos selecionados. Clique para iniciar a reconciliação.'}
                </p>
              </div>
              <button
                onClick={handleProcess}
                disabled={!excelFile || !pdfFile || processing}
                className="px-8 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {processing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Processando...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    <span>Processar Arquivos</span>
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
                <p className="text-sm text-gray-600 mt-2 text-center">
                  {progress}% completo
                </p>
              </div>
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

        {/* Results Section */}
        {result && (
          <>
            {/* Summary Cards */}
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Resultados da Reconciliação
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                {/* Total Cells */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Total de Células
                      </p>
                      <p className="text-3xl font-bold text-gray-900 mt-2">
                        {result.total_cells_compared}
                      </p>
                    </div>
                    <div className="bg-blue-100 rounded-full p-3">
                      <TrendingUp className="w-8 h-8 text-blue-600" />
                    </div>
                  </div>
                </div>

                {/* Match Percentage */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Taxa de Correspondência
                      </p>
                      <p className="text-3xl font-bold text-green-600 mt-2">
                        {result.match_percentage.toFixed(2)}%
                      </p>
                    </div>
                    <div className="bg-green-100 rounded-full p-3">
                      <CheckCircle2 className="w-8 h-8 text-green-600" />
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
                        {result.mismatching_cells}
                      </p>
                    </div>
                    <div className="bg-orange-100 rounded-full p-3">
                      <AlertTriangle className="w-8 h-8 text-orange-600" />
                    </div>
                  </div>
                </div>
              </div>

              {/* Download Button */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-gray-900">
                    Relatório Detalhado
                  </h4>
                  <p className="text-sm text-gray-600 mt-1">
                    Baixe o relatório completo em formato Excel com todas as divergências
                  </p>
                </div>
                <button
                  onClick={handleDownloadReport}
                  className="px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 flex items-center space-x-2"
                >
                  <Download className="w-5 h-5" />
                  <span>Baixar Relatório</span>
                </button>
              </div>
            </div>

            {/* Mismatches Detail */}
            {result.mismatching_cells > 0 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-6">
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
                                      Valor Excel
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                      Valor PDF
                                    </th>
                                  </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                  {mismatches.map((mismatch, idx) => (
                                    <tr key={idx} className="hover:bg-gray-50">
                                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {mismatch.field}
                                      </td>
                                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                        {mismatch.day_or_period || '-'}
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
          </>
        )}
      </main>
    </div>
  );
}

export default App;
