import { z } from 'zod';

export const createCaseSchema = z.object({
  body: z.object({
    title: z.string().min(3, 'Title must be at least 3 characters long').max(200),
    description: z.string().min(10, 'Case description must be at least 10 characters long'),
    court: z.string().min(2, 'Court specification is required').default('Supreme Court of India'),
    category: z.string().min(2, 'Legal category is required').default('General')
  })
});

export const updateCaseSchema = z.object({
  body: z.object({
    title: z.string().min(3).max(200).optional(),
    description: z.string().min(10).optional(),
    court: z.string().min(2).optional(),
    category: z.string().min(2).optional(),
    status: z.enum(['draft', 'analyzed', 'archived']).optional()
  })
});
