import { db } from './index.ts';
import { guildConfigs, activityLogs } from './schema.ts';
import { eq, desc } from 'drizzle-orm';

export async function getGuildConfigsByUserId(userId: number) {
  try {
    return await db
      .select()
      .from(guildConfigs)
      .where(eq(guildConfigs.userId, userId))
      .orderBy(desc(guildConfigs.createdAt));
  } catch (error) {
    console.error("Database query failed:", error);
    throw new Error("Database query failed while fetching guild configurations.", { cause: error });
  }
}

export async function upsertGuildConfig(
  userId: number,
  data: {
    guildId: string;
    name: string;
    prefix?: string;
    modLogChannel?: string;
    serverLogChannel?: string;
    welcomeChannel?: string;
    ticketCategory?: string;
    automodEnabled?: boolean;
    xpRate?: string;
  }
) {
  try {
    const existing = await db
      .select()
      .from(guildConfigs)
      .where(eq(guildConfigs.guildId, data.guildId));

    if (existing.length > 0) {
      const updated = await db
        .update(guildConfigs)
        .set({
          name: data.name,
          prefix: data.prefix ?? existing[0].prefix,
          modLogChannel: data.modLogChannel ?? existing[0].modLogChannel,
          serverLogChannel: data.serverLogChannel ?? existing[0].serverLogChannel,
          welcomeChannel: data.welcomeChannel ?? existing[0].welcomeChannel,
          ticketCategory: data.ticketCategory ?? existing[0].ticketCategory,
          automodEnabled: data.automodEnabled ?? existing[0].automodEnabled,
          xpRate: data.xpRate ?? existing[0].xpRate,
        })
        .where(eq(guildConfigs.guildId, data.guildId))
        .returning();
      return updated[0];
    } else {
      const created = await db
        .insert(guildConfigs)
        .values({
          userId,
          guildId: data.guildId,
          name: data.name,
          prefix: data.prefix ?? '/',
          modLogChannel: data.modLogChannel ?? null,
          serverLogChannel: data.serverLogChannel ?? null,
          welcomeChannel: data.welcomeChannel ?? null,
          ticketCategory: data.ticketCategory ?? null,
          automodEnabled: data.automodEnabled ?? true,
          xpRate: data.xpRate ?? '1.0',
        })
        .returning();
      return created[0];
    }
  } catch (error) {
    console.error("Failed to upsert guild configuration:", error);
    throw new Error("Database query failed while updating guild configuration.", { cause: error });
  }
}

export async function logActivity(userId: number, action: string, details: string, guildId?: string) {
  try {
    const result = await db
      .insert(activityLogs)
      .values({
        userId,
        action,
        details,
        guildId: guildId ?? null,
      })
      .returning();
    return result[0];
  } catch (error) {
    console.error("Failed to log activity:", error);
    throw new Error("Database query failed while logging activity.", { cause: error });
  }
}

export async function getActivityLogs(userId: number, limit = 20) {
  try {
    return await db
      .select()
      .from(activityLogs)
      .where(eq(activityLogs.userId, userId))
      .orderBy(desc(activityLogs.createdAt))
      .limit(limit);
  } catch (error) {
    console.error("Failed to fetch activity logs:", error);
    throw new Error("Database query failed while fetching activity logs.", { cause: error });
  }
}
