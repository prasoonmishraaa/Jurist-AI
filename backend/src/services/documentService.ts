import pdfParse from 'pdf-parse';
import mammoth from 'mammoth';
import path from 'path';
import { logger } from '../utils/logger';
import { mlClient } from '../integrations/mlClient';

export interface ExtractedPage {
  pageNumber: number;
  text: string;
  extractionMethod: 'native' | 'ocr';
  scriptType?: string;
  handwrittenDetected?: boolean;
  uncertainTokens?: string[];
  status: string;
  confidence: number | null;
  warnings: string[];
}

export interface DocumentExtractionResult {
  success: boolean;
  text: string;
  extractedText: string;
  filename: string;
  documentType: string;
  pageCount: number;
  pages: ExtractedPage[];
  extractionMethod: 'native' | 'ocr' | 'hybrid' | 'none';
  scriptType?: string;
  handwrittenDetected?: boolean;
  overallStatus: 'SUCCESS' | 'SUCCESS_WITH_WARNINGS' | 'SCANNED_UNPROCESSED' | 'LOW_CONFIDENCE_OCR' | 'FAILED' | 'DELEGATE_TO_BACKEND';
  warnings: string[];
}

export class DocumentService {
  public static async extractDocument(
    buffer: Buffer,
    fileName: string,
    mimeType: string
  ): Promise<DocumentExtractionResult> {
    if (!buffer || buffer.length === 0) {
      throw new Error(`Uploaded file '${fileName}' is empty.`);
    }

    const ext = path.extname(fileName || '').toLowerCase();

    // 1. DOCX Handling via Mammoth
    if (
      ext === '.docx' &&
      (mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
        mimeType === 'application/zip' ||
        mimeType === 'application/octet-stream')
    ) {
      try {
        const result = await mammoth.extractRawText({ buffer });
        const extracted = result.value ? result.value.trim() : '';
        if (extracted.length < 20) {
          throw new Error('The uploaded DOCX document contains insufficient readable text.');
        }
        return {
          success: true,
          text: extracted,
          extractedText: extracted,
          filename: fileName,
          documentType: 'docx',
          pageCount: 1,
          pages: [
            {
              pageNumber: 1,
              text: extracted,
              extractionMethod: 'native',
              status: 'SUCCESS',
              confidence: 1.0,
              warnings: []
            }
          ],
          extractionMethod: 'native',
          overallStatus: 'SUCCESS',
          warnings: []
        };
      } catch (err: any) {
        logger.warn(`DOCX text extraction failed for '${path.basename(fileName)}': ${err.message}`);
        throw new Error(`Failed to extract text from '${path.basename(fileName)}': ${err.message}`);
      }
    }

    // 2. TXT Handling
    if (ext === '.txt' && (mimeType === 'text/plain' || mimeType === 'text/markdown')) {
      const extracted = buffer.toString('utf-8').trim();
      if (extracted.length < 20) {
        throw new Error('The uploaded TXT document is empty or too short for legal analysis.');
      }
      return {
        success: true,
        text: extracted,
        extractedText: extracted,
        filename: fileName,
        documentType: 'txt',
        pageCount: 1,
        pages: [
          {
            pageNumber: 1,
            text: extracted,
            extractionMethod: 'native',
            status: 'SUCCESS',
            confidence: 1.0,
            warnings: []
          }
        ],
        extractionMethod: 'native',
        overallStatus: 'SUCCESS',
        warnings: []
      };
    }

    // 3. Legacy .doc rejection
    if (ext === '.doc') {
      throw new Error(
        'Legacy binary .doc files are not supported. Please convert to .docx or searchable .pdf and re-upload.'
      );
    }

    // 4. PDF and Image Files (.pdf, .png, .jpg, .jpeg) -> Route to Python ML service
    if (
      ext === '.pdf' ||
      ext === '.png' ||
      ext === '.jpg' ||
      ext === '.jpeg'
    ) {
      try {
        const pyResult = await mlClient.extractDocument(buffer, fileName, mimeType);
        if (pyResult && pyResult.success) {
          const rawText = pyResult.extractedText || '';
          return {
            success: true,
            text: rawText,
            extractedText: rawText,
            filename: fileName,
            documentType: pyResult.documentType || ext.replace('.', ''),
            pageCount: pyResult.pageCount || (pyResult.pages ? pyResult.pages.length : 1),
            pages: pyResult.pages || [],
            extractionMethod: pyResult.extractionMethod || 'native',
            scriptType: pyResult.scriptType || (pyResult.handwrittenDetected ? 'handwritten' : 'printed'),
            handwrittenDetected: Boolean(pyResult.handwrittenDetected),
            overallStatus: pyResult.overallStatus || 'SUCCESS',
            warnings: pyResult.warnings || []
          };
        } else if (pyResult && !pyResult.success) {
          const errorMsg = pyResult.warnings?.join('; ') || 'Document extraction failed in ML service.';
          throw new Error(errorMsg);
        }
      } catch (err: any) {
        logger.warn(`Python ML document extraction failed for '${path.basename(fileName)}': ${err.message}`);

        // Fallback for PDFs: try local Node pdf-parse
        if (ext === '.pdf') {
          logger.info(`Attempting local pdf-parse fallback for '${path.basename(fileName)}'...`);
          try {
            const data = await pdfParse(buffer);
            const extracted = data.text ? data.text.trim() : '';
            if (extracted.length < 20) {
              throw new Error(
                'No readable text layer was found in the PDF (it may be a scanned/image-only PDF). The Python OCR microservice is currently unreachable to process scanned pages. Please upload a text-searchable PDF, DOCX, or plain text file.'
              );
            }
            return {
              success: true,
              text: extracted,
              extractedText: extracted,
              filename: fileName,
              documentType: 'pdf',
              pageCount: data.numpages || 1,
              pages: [
                {
                  pageNumber: 1,
                  text: extracted,
                  extractionMethod: 'native',
                  status: 'SUCCESS',
                  confidence: 1.0,
                  warnings: ['Extracted via local fallback engine (Python service unreachable).']
                }
              ],
              extractionMethod: 'native',
              overallStatus: 'SUCCESS',
              warnings: ['Processed via local Node fallback engine; Python OCR microservice unavailable.']
            };
          } catch (fallbackErr: any) {
            throw new Error(`Failed to extract text from '${path.basename(fileName)}': ${fallbackErr.message}`);
          }
        }

        // For images, OCR cannot be performed locally without Python service
        if (ext === '.png' || ext === '.jpg' || ext === '.jpeg') {
          throw new Error(
            `Optical character recognition for images requires the Python OCR service, which is currently unavailable (${err.message}). Please ensure the ML service is running or upload a text-searchable PDF, DOCX, or TXT file.`
          );
        }

        throw new Error(`Failed to extract text from '${path.basename(fileName)}': ${err.message}`);
      }
    }

    throw new Error(
      `Unsupported document format '${ext}' (${mimeType}). Supported formats: .pdf, .docx, .txt, .png, .jpg, .jpeg.`
    );
  }

  public static async extractTextFromBuffer(
    buffer: Buffer,
    fileName: string,
    mimeType: string
  ): Promise<string> {
    const result = await DocumentService.extractDocument(buffer, fileName, mimeType);
    return result.text;
  }
}
