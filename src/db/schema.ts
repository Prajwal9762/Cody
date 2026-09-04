import { relations } from 'drizzle-orm';
import { integer, pgTable, serial, text, timestamp, boolean } from 'drizzle-orm/pg-core';

// Define the 'users' table linking to Firebase Auth UID
export const users = pgTable('users', {
  id: serial('id').primaryKey(),
  uid: text('uid').notNull().unique(), // Firebase Auth UID
  email: text('email').notNull(),
  displayName: text('display_name'),
  photoUrl: text('photo_url'),
  createdAt: timestamp('created_at').defaultNow(),
});

// Define 'guild_configs' table for bot server configurations
export const guildConfigs = pgTable('guild_configs', {
  id: serial('id').primaryKey(),
  userId: integer('user_id')
    .references(() => users.id)
    .notNull(),
  guildId: text('guild_id').notNull(),
  name: text('name').notNull(),
  prefix: text('prefix').default('/'),
  modLogChannel: text('mod_log_channel'),
  serverLogChannel: text('server_log_channel'),
  welcomeChannel: text('welcome_channel'),
  ticketCategory: text('ticket_category'),
  automodEnabled: boolean('automod_enabled').default(true),
  xpRate: text('xp_rate').default('1.0'),
  createdAt: timestamp('created_at').defaultNow(),
});

// Define 'activity_logs' table
export const activityLogs = pgTable('activity_logs', {
  id: serial('id').primaryKey(),
  userId: integer('user_id')
    .references(() => users.id)
    .notNull(),
  guildId: text('guild_id'),
  action: text('action').notNull(),
  details: text('details').notNull(),
  createdAt: timestamp('created_at').defaultNow(),
});

// Relationships
export const usersRelations = relations(users, ({ many }) => ({
  guildConfigs: many(guildConfigs),
  activityLogs: many(activityLogs),
}));

export const guildConfigsRelations = relations(guildConfigs, ({ one }) => ({
  owner: one(users, {
    fields: [guildConfigs.userId],
    references: [users.id],
  }),
}));

export const activityLogsRelations = relations(activityLogs, ({ one }) => ({
  user: one(users, {
    fields: [activityLogs.userId],
    references: [users.id],
  }),
}));
