"""
PDF Cell Image Extractor
Extracts images of specific cells from PDF documents using bounding box coordinates
"""
import fitz  # PyMuPDF
import base64
import io
from typing import Optional, List
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class PDFCellImageExtractor:
    """Extract and encode cell images from PDF documents"""

    def __init__(self, zoom_factor: float = 2.0):
        """
        Initialize the extractor

        Args:
            zoom_factor: Zoom level for PDF rendering (higher = better quality, larger file)
        """
        self.zoom_factor = zoom_factor

    def extract_cell_image(
        self,
        pdf_path: str,
        page_number: int,
        bounding_box: List[float],
        padding: int = 5
    ) -> Optional[str]:
        """
        Extract a cell image from PDF and convert to base64 data URI

        Args:
            pdf_path: Path to the PDF file
            page_number: Page number (0-indexed)
            bounding_box: List of [x1, y1, x2, y2, ...] coordinates from Azure DI polygon
            padding: Pixels to pad around the bounding box

        Returns:
            Base64 encoded data URI string (e.g., "data:image/png;base64,...") or None if extraction fails
        """
        try:
            # Open PDF
            doc = fitz.open(pdf_path)

            if page_number >= len(doc):
                logger.warning(f"Page {page_number} not found in PDF (total pages: {len(doc)})")
                return None

            page = doc[page_number]

            # Convert Azure DI polygon to fitz.Rect
            # Azure DI gives us a list of coordinates: [x1, y1, x2, y2, x3, y3, x4, y4, ...]
            # We need to find min/max x and y to create a rectangle
            if not bounding_box or len(bounding_box) < 4:
                logger.warning("Invalid bounding box coordinates")
                return None

            # Extract x and y coordinates separately
            x_coords = [bounding_box[i] for i in range(0, len(bounding_box), 2)]
            y_coords = [bounding_box[i] for i in range(1, len(bounding_box), 2)]

            # Create rectangle from min/max coordinates
            x0, y0 = min(x_coords), min(y_coords)
            x1, y1 = max(x_coords), max(y_coords)

            # Get page dimensions to convert from Azure DI coordinates (inches) to PDF points
            # Azure DI uses inches, PyMuPDF uses points (1 inch = 72 points)
            page_rect = page.rect
            page_width_pts = page_rect.width
            page_height_pts = page_rect.height

            # Convert from inches to points (Azure DI coordinate system)
            # Note: This assumes Azure DI coordinates are in inches
            # If they're already in points, remove the * 72
            x0_pts = x0 * 72
            y0_pts = y0 * 72
            x1_pts = x1 * 72
            y1_pts = y1 * 72

            # Add padding (in points)
            x0_pts = max(0, x0_pts - padding)
            y0_pts = max(0, y0_pts - padding)
            x1_pts = min(page_width_pts, x1_pts + padding)
            y1_pts = min(page_height_pts, y1_pts + padding)

            # Create clip rectangle
            clip_rect = fitz.Rect(x0_pts, y0_pts, x1_pts, y1_pts)

            # Render page to image with zoom
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            pix = page.get_pixmap(matrix=mat, clip=clip_rect)

            # Convert pixmap to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            # Convert to base64 data URI
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            data_uri = f"data:image/png;base64,{img_base64}"

            doc.close()

            logger.debug(f"Extracted cell image: {img.width}x{img.height}px, {len(data_uri)} chars")
            return data_uri

        except Exception as e:
            logger.error(f"Failed to extract cell image: {e}", exc_info=True)
            return None

    def extract_cell_image_from_azure_cell(
        self,
        pdf_path: str,
        cell: any,  # Azure DI DocumentTableCell object
        page_number: int = 0
    ) -> Optional[str]:
        """
        Extract cell image directly from Azure Document Intelligence cell object

        Args:
            pdf_path: Path to the PDF file
            cell: Azure DI DocumentTableCell object with bounding_regions
            page_number: Page number (defaults to 0 for single-page documents)

        Returns:
            Base64 encoded data URI string or None
        """
        try:
            if not hasattr(cell, 'bounding_regions') or not cell.bounding_regions:
                logger.warning("Cell has no bounding regions")
                return None

            # Get the first bounding region (cells usually have only one)
            bounding_region = cell.bounding_regions[0]

            # Use page number from bounding region if available
            if hasattr(bounding_region, 'page_number'):
                page_number = bounding_region.page_number - 1  # Azure uses 1-indexed pages

            # Get polygon coordinates
            if not hasattr(bounding_region, 'polygon') or not bounding_region.polygon:
                logger.warning("Bounding region has no polygon")
                return None

            polygon = bounding_region.polygon

            # Azure DI Polygon is already a flat list of coordinates [x1, y1, x2, y2, ...]
            # No conversion needed - pass directly
            if not isinstance(polygon, list) or len(polygon) < 4:
                logger.warning(f"Invalid polygon format: {polygon}")
                return None

            return self.extract_cell_image(pdf_path, page_number, polygon)

        except Exception as e:
            logger.error(f"Failed to extract cell image from Azure cell: {e}", exc_info=True)
            return None
