import { app } from '../backend/src/app';
import { connectDB } from '../backend/src/config/db';
import type { IncomingMessage, ServerResponse } from 'http';

export default async function handler(req: IncomingMessage, res: ServerResponse) {
  await connectDB().catch(() => {});
  return (app as any)(req, res);
}
