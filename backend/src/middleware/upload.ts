import multer from 'multer';
import path from 'path';
import { Request } from 'express';
import { env } from '../config/env';

const storage = multer.memoryStorage();

const EXTENSION_MIME_ALLOWLIST: Record<string, string[]> = {
  '.pdf': ['application/pdf', 'application/x-pdf'],
  '.docx': [
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/zip',
    'application/octet-stream'
  ],
  '.txt': ['text/plain', 'text/markdown'],
  '.png': ['image/png'],
  '.jpg': ['image/jpeg', 'image/pjpeg'],
  '.jpeg': ['image/jpeg', 'image/pjpeg']
};

const fileFilter = (_req: Request, file: Express.Multer.File, cb: multer.FileFilterCallback) => {
  const ext = path.extname(file.originalname || '').toLowerCase();
  const allowedMimes = EXTENSION_MIME_ALLOWLIST[ext];

  if (!allowedMimes) {
    return cb(
      new Error(
        `Unsupported file type '${ext || 'unknown'}'. Accepted formats: PDF (.pdf), Word (.docx), plain text (.txt), and image files (.png, .jpg, .jpeg).`
      )
    );
  }

  if (!allowedMimes.includes(file.mimetype)) {
    return cb(
      new Error(
        `File MIME type '${file.mimetype}' does not match extension '${ext}'. Please upload a genuine PDF, DOCX, TXT, or image file.`
      )
    );
  }

  return cb(null, true);
};

export const uploadMiddleware = multer({
  storage,
  limits: {
    fileSize: env.MAX_FILE_SIZE_MB * 1024 * 1024
  },
  fileFilter
});
