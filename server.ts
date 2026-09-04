import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { createServer as createViteServer } from 'vite';
import { requireAuth, AuthRequest } from './src/middleware/auth.ts';
import { getOrCreateUser, getUserByUid } from './src/db/users.ts';
import {
  getGuildConfigsByUserId,
  upsertGuildConfig,
  logActivity,
  getActivityLogs,
} from './src/db/guilds.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // Health check endpoint
  app.get('/api/health', (req, res) => {
    res.json({
      status: 'ok',
      service: 'AllInOneDiscordBot API & Web App',
      cloudSql: 'connected',
    });
  });

  // Synchronize authenticated user profile to Cloud SQL (PostgreSQL)
  app.post('/api/auth/sync', requireAuth, async (req: AuthRequest, res) => {
    try {
      const { uid, email, name, picture } = req.user!;
      const user = await getOrCreateUser(uid, email || `${uid}@discordbot.app`, name, picture);
      res.json({ success: true, user });
    } catch (error: any) {
      console.error('Error syncing user:', error);
      res.status(500).json({ error: error.message || 'Failed to sync user' });
    }
  });

  // Get current user profile
  app.get('/api/auth/me', requireAuth, async (req: AuthRequest, res) => {
    try {
      const user = await getUserByUid(req.user!.uid);
      if (!user) {
        return res.status(404).json({ error: 'User not registered in database' });
      }
      res.json({ user });
    } catch (error: any) {
      console.error('Error fetching user profile:', error);
      res.status(500).json({ error: error.message || 'Failed to fetch user' });
    }
  });

  // Get user's guild configurations
  app.get('/api/guilds', requireAuth, async (req: AuthRequest, res) => {
    try {
      const user = await getUserByUid(req.user!.uid);
      if (!user) {
        return res.status(404).json({ error: 'User not found in database' });
      }
      const guilds = await getGuildConfigsByUserId(user.id);
      res.json({ guilds });
    } catch (error: any) {
      console.error('Failed to fetch guild configs:', error);
      res.status(500).json({ error: error.message || 'Failed to fetch guild configs' });
    }
  });

  // Save or update a guild configuration
  app.post('/api/guilds', requireAuth, async (req: AuthRequest, res) => {
    try {
      const user = await getUserByUid(req.user!.uid);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      const {
        guildId,
        name,
        prefix,
        modLogChannel,
        serverLogChannel,
        welcomeChannel,
        ticketCategory,
        automodEnabled,
        xpRate,
      } = req.body;

      if (!guildId || !name) {
        return res.status(400).json({ error: 'guildId and name are required' });
      }

      const config = await upsertGuildConfig(user.id, {
        guildId,
        name,
        prefix,
        modLogChannel,
        serverLogChannel,
        welcomeChannel,
        ticketCategory,
        automodEnabled,
        xpRate,
      });

      await logActivity(
        user.id,
        'CONFIG_UPDATE',
        `Updated settings for guild ${name} (${guildId})`,
        guildId
      );

      res.json({ success: true, config });
    } catch (error: any) {
      console.error('Failed to upsert guild config:', error);
      res.status(500).json({ error: error.message || 'Failed to update guild config' });
    }
  });

  // Get recent activity logs
  app.get('/api/logs', requireAuth, async (req: AuthRequest, res) => {
    try {
      const user = await getUserByUid(req.user!.uid);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }
      const logs = await getActivityLogs(user.id, 25);
      res.json({ logs });
    } catch (error: any) {
      console.error('Failed to fetch activity logs:', error);
      res.status(500).json({ error: error.message || 'Failed to fetch logs' });
    }
  });

  // Vite middleware for development vs static build in production
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('Failed to start server:', err);
});
