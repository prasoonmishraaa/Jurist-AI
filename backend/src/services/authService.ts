import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { User, IUser } from '../models/User';
import { env } from '../config/env';
import { getDBStatus } from '../config/db';

// In-memory fallback user store when MongoDB is disconnected
const memoryUsers: Map<string, any> = new Map();

export class AuthService {
  public static async register(name: string, email: string, password: string, role: 'user' | 'admin' = 'user') {
    const normalizedEmail = email.toLowerCase().trim();
    const dbStatus = getDBStatus();

    const passwordHash = await bcrypt.hash(password, 10);

    if (dbStatus.isConnected) {
      const existingUser = await User.findOne({ email: normalizedEmail });
      if (existingUser) {
        throw new Error('A user with this email address already exists.');
      }

      const user = await User.create({
        name,
        email: normalizedEmail,
        passwordHash,
        role
      });

      const token = this.generateToken(user._id.toString(), user.email, user.role, user.name);

      return {
        user: {
          id: user._id.toString(),
          name: user.name,
          email: user.email,
          role: user.role,
          createdAt: user.createdAt
        },
        token
      };
    } else {
      // Memory store fallback
      if (memoryUsers.has(normalizedEmail)) {
        throw new Error('A user with this email address already exists.');
      }

      const mockId = 'mem_' + Date.now();
      const mockUser = {
        _id: mockId,
        id: mockId,
        name,
        email: normalizedEmail,
        passwordHash,
        role,
        createdAt: new Date(),
        updatedAt: new Date()
      };
      memoryUsers.set(normalizedEmail, mockUser);

      const token = this.generateToken(mockId, normalizedEmail, role, name);

      return {
        user: {
          id: mockId,
          name,
          email: normalizedEmail,
          role,
          createdAt: mockUser.createdAt
        },
        token
      };
    }
  }

  public static async login(email: string, password: string) {
    const normalizedEmail = email.toLowerCase().trim();
    const dbStatus = getDBStatus();

    let user: any;

    if (dbStatus.isConnected) {
      user = await User.findOne({ email: normalizedEmail }).select('+passwordHash');
    } else {
      user = memoryUsers.get(normalizedEmail);
    }

    if (!user) {
      throw new Error('Invalid email or password.');
    }

    const isMatch = await bcrypt.compare(password, user.passwordHash);
    if (!isMatch) {
      throw new Error('Invalid email or password.');
    }

    const userId = user._id ? user._id.toString() : user.id;
    const token = this.generateToken(userId, user.email, user.role, user.name);

    return {
      user: {
        id: userId,
        name: user.name,
        email: user.email,
        role: user.role,
        createdAt: user.createdAt
      },
      token
    };
  }

  public static async getUserById(userId: string) {
    const dbStatus = getDBStatus();

    if (dbStatus.isConnected) {
      const user = await User.findById(userId);
      if (!user) throw new Error('User not found.');
      return {
        id: user._id.toString(),
        name: user.name,
        email: user.email,
        role: user.role,
        createdAt: user.createdAt
      };
    } else {
      for (const u of memoryUsers.values()) {
        if (u.id === userId || u._id === userId) {
          return {
            id: u.id,
            name: u.name,
            email: u.email,
            role: u.role,
            createdAt: u.createdAt
          };
        }
      }
      throw new Error('User not found.');
    }
  }

  public static async updateProfile(userId: string, name?: string) {
    const dbStatus = getDBStatus();
    if (dbStatus.isConnected) {
      const user = await User.findByIdAndUpdate(userId, { ...(name && { name }) }, { new: true });
      if (!user) throw new Error('User not found.');
      return {
        id: user._id.toString(),
        name: user.name,
        email: user.email,
        role: user.role
      };
    } else {
      for (const u of memoryUsers.values()) {
        if (u.id === userId || u._id === userId) {
          if (name) u.name = name;
          return { id: u.id, name: u.name, email: u.email, role: u.role };
        }
      }
      throw new Error('User not found.');
    }
  }

  public static async updatePassword(userId: string, currentPass: string, newPass: string) {
    const dbStatus = getDBStatus();
    let user: any;

    if (dbStatus.isConnected) {
      user = await User.findById(userId).select('+passwordHash');
    } else {
      for (const u of memoryUsers.values()) {
        if (u.id === userId || u._id === userId) {
          user = u;
          break;
        }
      }
    }

    if (!user) throw new Error('User not found.');

    const isMatch = await bcrypt.compare(currentPass, user.passwordHash);
    if (!isMatch) throw new Error('Current password is incorrect.');

    const newHash = await bcrypt.hash(newPass, 10);

    if (dbStatus.isConnected) {
      user.passwordHash = newHash;
      await user.save();
    } else {
      user.passwordHash = newHash;
    }

    return true;
  }

  public static generateToken(id: string, email: string, role: string, name: string): string {
    if (!env.JWT_SECRET) {
      throw new Error('Authentication service misconfigured: JWT_SECRET is required in production.');
    }
    return jwt.sign({ id, email, role, name }, env.JWT_SECRET, {
      expiresIn: env.JWT_EXPIRES_IN as any
    });
  }
}
