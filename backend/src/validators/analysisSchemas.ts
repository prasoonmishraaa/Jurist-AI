import { z } from 'zod';

export const createAnalysisSchema = z.object({
  body: z
    .object({
      caseId: z.string().optional(),
      caseTitle: z.string().min(3).max(300).optional(),
      description: z.string().optional(),
      court: z.string().max(150).optional(),
      category: z.string().max(100).optional(),
      text: z.string().optional()
    })
});

export const updateAnalysisSchema = z.object({
  body: z
    .object({
      caseTitle: z.string().min(3).max(300).optional(),
      researchNotes: z.string().max(30000).optional(),
      editedDrafts: z.record(z.string().max(60000)).optional()
    })
    .refine(
      data =>
        typeof data.researchNotes === 'string' ||
        typeof data.caseTitle === 'string' ||
        (data.editedDrafts && Object.keys(data.editedDrafts).length > 0),
      { message: 'Provide researchNotes, editedDrafts, or caseTitle to update.' }
    )
});
