import { useState } from 'react';
import { FileSpreadsheet, Package } from 'lucide-react';
import SingleReconciliation from './SingleReconciliation';
import BulkUpload from './BulkUpload';

type Mode = 'single' | 'bulk';

function App() {
  const [mode, setMode] = useState<Mode>('bulk'); // Start with bulk mode

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
                <h1 className="text-xl font-bold text-gray-900">
                  Sistema de Reconciliação EMEI
                </h1>
                <p className="text-xs text-gray-500">
                  Secretaria Municipal de Educação - SME
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Mode Tabs */}
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setMode('single')}
              className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors flex items-center space-x-2 ${
                mode === 'single'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
              }`}
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>Reconciliação Individual</span>
            </button>
            <button
              onClick={() => setMode('bulk')}
              className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors flex items-center space-x-2 ${
                mode === 'bulk'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
              }`}
            >
              <Package className="w-4 h-4" />
              <span>Carga em Lote</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {mode === 'single' ? <SingleReconciliation /> : <BulkUpload />}
      </main>
    </div>
  );
}

export default App;
