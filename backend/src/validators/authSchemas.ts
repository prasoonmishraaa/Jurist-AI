import { z } from 'zod';

export const registerSchema = z.object({
  body: z.object({
    name: z.string().min(2, 'Name must be at least 2 characters long').max(100),
    email: z.string().email('Please provide a valid email address'),
    password: z.string().min(6, 'Password must be at least 6 characters long').max(100),
    role: z.enum(['user', 'admin']).optional()
  })
});

export const loginSchema = z.object({
  body: z.object({
    email: z.string().email('Please provide a valid email address'),
    password: z.string().min(1, 'Password is required')
  })
});

export const updateProfileSchema = z.object({
  body: z.object({
    name: z.string().min(2).max(100).optional()
  })
});

export const updatePasswordSchema = z.object({
  body: z.object({
    currentPassword: z.string().min(1, 'Current password is required'),
    newPassword: z.string().min(6, 'New password must be at least 6 characters long')
  })
});
