import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, XCircle, AlertCircle, Download } from 'lucide-react';

const PDFReconciliationInterface = () => {
  const [pdfFile, setPdfFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [excelFiles, setExcelFiles] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [selectedRows, setSelectedRows] = useState(new Set());
  const [selectedDocument, setSelectedDocument] = useState(null);

  // Dados de exemplo
  const exampleDocuments = [
    {
      id: '92311',
      tipo: 'EMEI',
      lugar: 'XXXX',
      codigoCODAE: '123232',
      mes: 'Janeiro',
      ano: '2025',
      cep: '01454-010',
      diretoria: 'São Mateus',
      prestador: 'Comercial Milano Brasil LTDA',
      paginas: 2,
      excel: null,
      status: null
    },
    {
      id: '95687',
      tipo: 'EMEI',
      lugar: 'XXXX',
      codigoCODAE: '123232',
      mes: 'Dezembro',
      ano: '2025',
      cep: '01454-010',
      diretoria: 'São Mateus',
      prestador: 'Comercial Milano Brasil LTDA',
      paginas: 2,
      excel: null,
      status: null
    },
    {
      id: '97836',
      tipo: 'EMEI',
      lugar: 'XXXX',
      codigoCODAE: '123232',
      mes: 'Julho',
      ano: '2025',
      cep: '01454-010',
      diretoria: 'São Mateus',
      prestador: 'Comercial Milano Brasil LTDA',
      paginas: 1,
      excel: null,
      status: null
    }
  ];

  const handlePdfUpload = (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      setPdfFile(file);
    }
  };

  const handleExcelUpload = (e) => {
    const files = Array.from(e.target.files);
    setExcelFiles(files);
    
    // Simular matching de arquivos Excel com IDs
    const updatedDocs = documents.map(doc => {
      const matchedExcel = files.find(f => f.name.replace('.xlsx', '') === doc.id);
      return {
        ...doc,
        excel: matchedExcel ? matchedExcel.name : doc.excel
      };
    });
    setDocuments(updatedDocs);
  };

  const processPDF = () => {
    setIsProcessing(true);
    setProcessingProgress(0);
    
    // Simular processamento com progress bar
    const interval = setInterval(() => {
      setProcessingProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsProcessing(false);
          setDocuments(exampleDocuments);
          return 100;
        }
        return prev + 2;
      });
    }, 300);
  };

  const toggleRowSelection = (id) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedRows(newSelected);
  };

  const selectAllValid = () => {
    const validIds = documents
      .filter(doc => doc.paginas === 2 && doc.excel)
      .map(doc => doc.id);
    setSelectedRows(new Set(validIds));
  };

  const processSelected = () => {
    const updatedDocs = documents.map(doc => {
      if (selectedRows.has(doc.id)) {
        return { ...doc, status: 'processado' };
      }
      return doc;
    });
    setDocuments(updatedDocs);
    setSelectedRows(new Set());
  };

  const getStatusBadge = (status) => {
    if (!status) return <span className="text-gray-400 text-sm">Pendente</span>;
    if (status === 'processado') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 rounded text-sm">
          <CheckCircle size={14} />
          Processado
        </span>
      );
    }
    return null;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          Sistema de Reconciliação de Documentos
        </h1>

        {/* Seção 1: Upload do PDF Combinado */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <FileText className="text-blue-600" />
            1. Upload do PDF Combinado
          </h2>
          
          <div className="space-y-4">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors">
              <input
                type="file"
                accept=".pdf"
                onChange={handlePdfUpload}
                className="hidden"
                id="pdf-upload"
                disabled={isProcessing}
              />
              <label
                htmlFor="pdf-upload"
                className="cursor-pointer flex flex-col items-center gap-3"
              >
                <Upload className="text-gray-400" size={48} />
                <div>
                  <p className="text-lg font-medium text-gray-700">
                    {pdfFile ? pdfFile.name : 'Clique para selecionar o PDF combinado'}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    Arquivo PDF contendo todos os documentos
                  </p>
                </div>
              </label>
            </div>

            <button
              onClick={processPDF}
              disabled={!pdfFile || isProcessing}
              className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {isProcessing ? 'Processando...' : 'Processar PDF'}
            </button>

            {isProcessing && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Processando documentos...</span>
                  <span>{processingProgress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-blue-600 h-full transition-all duration-300 rounded-full"
                    style={{ width: `${processingProgress}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 text-center">
                  Dividindo PDF, executando OCR e extraindo campos (10-20 minutos)
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Seção 2: Upload de Arquivos Excel */}
        {documents.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Upload className="text-green-600" />
              2. Upload dos Arquivos Excel
            </h2>
            
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-green-400 transition-colors">
              <input
                type="file"
                accept=".xlsx,.xls"
                multiple
                onChange={handleExcelUpload}
                className="hidden"
                id="excel-upload"
              />
              <label
                htmlFor="excel-upload"
                className="cursor-pointer flex flex-col items-center gap-3"
              >
                <Upload className="text-gray-400" size={40} />
                <div>
                  <p className="text-lg font-medium text-gray-700">
                    {excelFiles.length > 0 
                      ? `${excelFiles.length} arquivo(s) Excel selecionado(s)` 
                      : 'Clique para selecionar arquivos Excel'}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    Selecione múltiplos arquivos (30-50 arquivos)
                  </p>
                </div>
              </label>
            </div>

            {excelFiles.length > 0 && (
              <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm font-medium text-green-800 mb-2">
                  Arquivos correspondidos:
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-sm text-green-700">
                      ✓ Correspondidos: {documents.filter(d => d.excel).length}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-orange-700">
                      ⚠ Faltando: {documents.filter(d => !d.excel).length}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Seção 3: Tabela de Documentos Processados */}
        {documents.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <FileText className="text-purple-600" />
                3. Documentos Processados ({documents.length})
              </h2>
              
              <div className="flex gap-3">
                <button
                  onClick={selectAllValid}
                  className="px-4 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-colors text-sm font-medium"
                >
                  Selecionar Válidos
                </button>
                <button
                  onClick={processSelected}
                  disabled={selectedRows.size === 0}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                >
                  Processar Selecionados ({selectedRows.size})
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-100 border-b-2 border-gray-200">
                  <tr>
                    <th className="p-3 text-left">
                      <input
                        type="checkbox"
                        className="w-4 h-4"
                        onChange={(e) => {
                          if (e.target.checked) {
                            selectAllValid();
                          } else {
                            setSelectedRows(new Set());
                          }
                        }}
                      />
                    </th>
                    <th className="p-3 text-left font-semibold text-gray-700">ID</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Tipo</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Lugar</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Código CODAE</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Mês</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Ano</th>
                    <th className="p-3 text-left font-semibold text-gray-700">CEP</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Diretoria</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Prestador</th>
                    <th className="p-3 text-center font-semibold text-gray-700">Páginas</th>
                    <th className="p-3 text-center font-semibold text-gray-700">Excel</th>
                    <th className="p-3 text-center font-semibold text-gray-700">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc, idx) => {
                    const isValid = doc.paginas === 2 && doc.excel;
                    const isSelected = selectedRows.has(doc.id);
                    const isHighlighted = excelFiles.length > 0 && doc.excel;
                    
                    return (
                      <tr
                        key={doc.id}
                        className={`border-b hover:bg-gray-50 transition-colors cursor-pointer ${
                          isHighlighted ? 'bg-green-50' : ''
                        } ${doc.status === 'processado' ? 'bg-blue-50' : ''}`}
                        onClick={() => {
                          if (doc.status === 'processado') {
                            setSelectedDocument(doc);
                          }
                        }}
                      >
                        <td className="p-3" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleRowSelection(doc.id)}
                            disabled={!isValid}
                            className="w-4 h-4 disabled:opacity-30"
                          />
                        </td>
                        <td className="p-3 font-medium text-gray-900">{doc.id}</td>
                        <td className="p-3 text-gray-700">{doc.tipo}</td>
                        <td className="p-3 text-gray-700">{doc.lugar}</td>
                        <td className="p-3 text-gray-700">{doc.codigoCODAE}</td>
                        <td className="p-3 text-gray-700">{doc.mes}</td>
                        <td className="p-3 text-gray-700">{doc.ano}</td>
                        <td className="p-3 text-gray-700">{doc.cep}</td>
                        <td className="p-3 text-gray-700">{doc.diretoria}</td>
                        <td className="p-3 text-gray-700 text-xs">{doc.prestador}</td>
                        <td className="p-3 text-center">
                          <span
                            className={`inline-flex items-center justify-center w-8 h-8 rounded-full font-semibold ${
                              doc.paginas === 2
                                ? 'bg-green-100 text-green-700'
                                : 'bg-red-100 text-red-700'
                            }`}
                          >
                            {doc.paginas}
                          </span>
                        </td>
                        <td className="p-3 text-center">
                          {doc.excel ? (
                            <CheckCircle className="inline text-green-600" size={20} />
                          ) : (
                            <span className="text-xs text-gray-400">Não enviado</span>
                          )}
                        </td>
                        <td className="p-3 text-center">
                          {getStatusBadge(doc.status)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="mt-4 flex items-center gap-4 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-green-100 border-2 border-green-500"></div>
                <span>Páginas válidas (2)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-red-100 border-2 border-red-500"></div>
                <span>Páginas inválidas</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle size={16} className="text-green-600" />
                <span>Excel correspondido</span>
              </div>
            </div>
          </div>
        )}

        {/* Seção 4: Detalhes da Reconciliação */}
        {selectedDocument && selectedDocument.status === 'processado' && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <AlertCircle className="text-blue-600" />
                4. Resultado da Reconciliação - ID: {selectedDocument.id}
              </h2>
              <button
                onClick={() => setSelectedDocument(null)}
                className="text-gray-500 hover:text-gray-700 text-sm"
              >
                Fechar
              </button>
            </div>

            {/* Placeholder para o componente de reconciliação detalhada */}
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
              <AlertCircle className="mx-auto text-gray-400 mb-4" size={64} />
              <p className="text-lg font-medium text-gray-700 mb-2">
                Componente de Análise de Reconciliação
              </p>
              <p className="text-sm text-gray-500">
                O frontend detalhado da reconciliação será exibido aqui
              </p>
              <div className="mt-6 grid grid-cols-3 gap-4 max-w-2xl mx-auto">
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-2xl font-bold text-green-700">95%</p>
                  <p className="text-xs text-green-600 mt-1">Taxa de Correspondência</p>
                </div>
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-2xl font-bold text-blue-700">12</p>
                  <p className="text-xs text-blue-600 mt-1">Campos Verificados</p>
                </div>
                <div className="bg-orange-50 p-4 rounded-lg">
                  <p className="text-2xl font-bold text-orange-700">2</p>
                  <p className="text-xs text-orange-600 mt-1">Discrepâncias</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PDFReconciliationInterface;
