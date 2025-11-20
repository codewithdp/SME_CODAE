import React, { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Configure PDF.js worker - use CDN for reliability
if (typeof window !== 'undefined' && 'Worker' in window) {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
}

interface PDFViewerProps {
  uploadId: string;
  documentId: string;
}

export const PDFViewer: React.FC<PDFViewerProps> = ({ uploadId, documentId }) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Pan state
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [startPanPos, setStartPanPos] = useState({ x: 0, y: 0 });

  // Box zoom state
  const [boxZoomMode, setBoxZoomMode] = useState<boolean>(false);
  const [isSelecting, setIsSelecting] = useState<boolean>(false);
  const [selectionBox, setSelectionBox] = useState<{
    startX: number;
    startY: number;
    endX: number;
    endY: number
  } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);
  const pdfUrl = `/api/v1/bulk/${uploadId}/pdf/${documentId}`;

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
    setError(null);
  };

  const onDocumentLoadError = (error: any) => {
    console.error('Error loading PDF:', error);
    setError(`Failed to load PDF: ${error.message || 'Unknown error'}`);
    setLoading(false);
  };

  // Zoom controls
  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.25, 3.0));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.25, 0.5));
  };

  const handleResetZoom = () => {
    setScale(1.0);
    setPanOffset({ x: 0, y: 0 });
    setBoxZoomMode(false);
  };

  // Page navigation
  const goToPrevPage = () => {
    setPageNumber(prev => Math.max(prev - 1, 1));
  };

  const goToNextPage = () => {
    setPageNumber(prev => Math.min(prev + 1, numPages));
  };

  // Mouse handlers (for both pan and box zoom)
  const handleMouseDown = (e: React.MouseEvent) => {
    if (boxZoomMode) {
      // Box zoom mode: start selection
      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      setIsSelecting(true);
      setSelectionBox({
        startX: x,
        startY: y,
        endX: x,
        endY: y
      });
    } else {
      // Pan mode
      setIsPanning(true);
      setStartPanPos({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (boxZoomMode && isSelecting && selectionBox) {
      // Update selection box
      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      setSelectionBox({
        ...selectionBox,
        endX: x,
        endY: y
      });
    } else if (isPanning) {
      // Pan the view
      setPanOffset({
        x: e.clientX - startPanPos.x,
        y: e.clientY - startPanPos.y
      });
    }
  };

  const handleMouseUp = (e: React.MouseEvent) => {
    if (boxZoomMode && isSelecting && selectionBox) {
      // Apply box zoom
      const rect = e.currentTarget.getBoundingClientRect();
      const boxWidth = Math.abs(selectionBox.endX - selectionBox.startX);
      const boxHeight = Math.abs(selectionBox.endY - selectionBox.startY);

      // Only zoom if the box is big enough (not just a click)
      if (boxWidth > 20 && boxHeight > 20) {
        const containerWidth = rect.width;
        const containerHeight = rect.height;

        // Calculate new scale based on selection box
        const scaleX = containerWidth / boxWidth;
        const scaleY = containerHeight / boxHeight;
        const newScale = Math.min(scaleX, scaleY, 3.0); // Max 3.0x zoom

        setScale(newScale);

        // Calculate pan offset to center the selected area
        const boxCenterX = (selectionBox.startX + selectionBox.endX) / 2;
        const boxCenterY = (selectionBox.startY + selectionBox.endY) / 2;
        const containerCenterX = containerWidth / 2;
        const containerCenterY = containerHeight / 2;

        setPanOffset({
          x: (containerCenterX - boxCenterX) * newScale,
          y: (containerCenterY - boxCenterY) * newScale
        });
      }

      setIsSelecting(false);
      setSelectionBox(null);
    } else {
      setIsPanning(false);
    }
  };

  const handleMouseLeave = () => {
    setIsPanning(false);
    setIsSelecting(false);
    setSelectionBox(null);
  };


  return (
    <div style={{
      width: '100%',
      border: '1px solid #ddd',
      borderRadius: '8px',
      backgroundColor: '#f5f5f5'
    }}>
      {/* Controls Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px 16px',
        backgroundColor: '#fff',
        borderBottom: '1px solid #ddd',
        borderTopLeftRadius: '8px',
        borderTopRightRadius: '8px',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        {/* Page Navigation */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={goToPrevPage}
            disabled={pageNumber <= 1}
            style={{
              padding: '6px 12px',
              backgroundColor: pageNumber <= 1 ? '#e0e0e0' : '#007bff',
              color: pageNumber <= 1 ? '#888' : '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: pageNumber <= 1 ? 'not-allowed' : 'pointer',
              fontSize: '14px'
            }}
          >
            ← Anterior
          </button>
          <span style={{ fontSize: '14px', color: '#333', minWidth: '100px', textAlign: 'center' }}>
            Página {pageNumber} de {numPages || '?'}
          </span>
          <button
            onClick={goToNextPage}
            disabled={pageNumber >= numPages}
            style={{
              padding: '6px 12px',
              backgroundColor: pageNumber >= numPages ? '#e0e0e0' : '#007bff',
              color: pageNumber >= numPages ? '#888' : '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: pageNumber >= numPages ? 'not-allowed' : 'pointer',
              fontSize: '14px'
            }}
          >
            Próxima →
          </button>
        </div>

        {/* Zoom Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setBoxZoomMode(!boxZoomMode)}
            style={{
              padding: '6px 12px',
              backgroundColor: boxZoomMode ? '#ff6b6b' : '#17a2b8',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: boxZoomMode ? 'bold' : 'normal'
            }}
            title={boxZoomMode ? 'Clique para desativar Zoom de Seleção' : 'Clique para ativar Zoom de Seleção'}
          >
            {boxZoomMode ? '🔍 Seleção ON' : '🔍 Zoom Seleção'}
          </button>
          <button
            onClick={handleZoomOut}
            disabled={scale <= 0.5}
            style={{
              padding: '6px 12px',
              backgroundColor: scale <= 0.5 ? '#e0e0e0' : '#28a745',
              color: scale <= 0.5 ? '#888' : '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: scale <= 0.5 ? 'not-allowed' : 'pointer',
              fontSize: '14px'
            }}
          >
            -
          </button>
          <span style={{ fontSize: '14px', color: '#333', minWidth: '60px', textAlign: 'center' }}>
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            disabled={scale >= 3.0}
            style={{
              padding: '6px 12px',
              backgroundColor: scale >= 3.0 ? '#e0e0e0' : '#28a745',
              color: scale >= 3.0 ? '#888' : '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: scale >= 3.0 ? 'not-allowed' : 'pointer',
              fontSize: '14px'
            }}
          >
            +
          </button>
          <button
            onClick={handleResetZoom}
            style={{
              padding: '6px 12px',
              backgroundColor: '#6c757d',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Redefinir
          </button>
        </div>
      </div>

      {/* PDF Display Area */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        style={{
          width: '100%',
          height: '600px',
          overflow: 'auto',
          backgroundColor: '#e0e0e0',
          cursor: boxZoomMode
            ? (isSelecting ? 'crosshair' : 'crosshair')
            : (isPanning ? 'grabbing' : 'grab'),
          position: 'relative',
          borderBottomLeftRadius: '8px',
          borderBottomRightRadius: '8px'
        }}
      >
        {error && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
            fontSize: '16px',
            color: '#d32f2f',
            padding: '20px',
            textAlign: 'center',
            gap: '10px'
          }}>
            <div style={{ fontSize: '48px' }}>⚠️</div>
            <div style={{ fontWeight: 'bold' }}>Erro ao Carregar PDF</div>
            <div style={{ fontSize: '14px', color: '#666' }}>{error}</div>
            <div style={{ fontSize: '12px', color: '#999', marginTop: '10px' }}>
              Abra o Console (F12) para mais detalhes
            </div>
          </div>
        )}

        {!error && (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            padding: '20px',
            transform: `translate(${panOffset.x}px, ${panOffset.y}px)`,
            transformOrigin: 'top left'
          }}>
            <Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center',
                  height: '400px',
                  fontSize: '16px',
                  color: '#666',
                  gap: '10px'
                }}>
                  <div style={{
                    border: '4px solid #f3f3f3',
                    borderTop: '4px solid #3498db',
                    borderRadius: '50%',
                    width: '40px',
                    height: '40px',
                    animation: 'spin 1s linear infinite'
                  }}></div>
                  <div>Carregando PDF...</div>
                </div>
              }
            >
              <Page
                pageNumber={pageNumber}
                scale={scale}
                renderTextLayer={true}
                renderAnnotationLayer={true}
              />
            </Document>
          </div>
        )}

        {/* Selection Box Overlay */}
        {isSelecting && selectionBox && (
          <div
            style={{
              position: 'absolute',
              left: Math.min(selectionBox.startX, selectionBox.endX),
              top: Math.min(selectionBox.startY, selectionBox.endY),
              width: Math.abs(selectionBox.endX - selectionBox.startX),
              height: Math.abs(selectionBox.endY - selectionBox.startY),
              border: '2px dashed #007bff',
              backgroundColor: 'rgba(0, 123, 255, 0.1)',
              pointerEvents: 'none',
              zIndex: 1000
            }}
          />
        )}
      </div>

      {/* Helper Text */}
      <div style={{
        padding: '8px 16px',
        backgroundColor: '#fff',
        borderTop: '1px solid #ddd',
        fontSize: '12px',
        color: '#666',
        textAlign: 'center'
      }}>
        {boxZoomMode
          ? '🔍 Modo Zoom de Seleção: Clique e arraste para selecionar uma área para ampliar'
          : 'Clique e arraste para mover o PDF | Use os botões de zoom para ampliar/reduzir'
        }
      </div>
    </div>
  );
};
