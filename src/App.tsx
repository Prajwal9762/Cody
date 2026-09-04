import React, { useState, useEffect } from 'react';
import {
  Database,
  Server,
  Shield,
  CheckCircle2,
  RefreshCw,
  Plus,
  Terminal,
  Settings,
  LogOut,
  LogIn,
  Activity,
  Layers,
  Globe,
  Radio,
  Sliders,
  AlertCircle
} from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext.tsx';

interface GuildConfig {
  id: number;
  guildId: string;
  name: string;
  prefix: string;
  modLogChannel: string | null;
  serverLogChannel: string | null;
  welcomeChannel: string | null;
  ticketCategory: string | null;
  automodEnabled: boolean;
  xpRate: string;
  createdAt: string;
}

interface ActivityLogItem {
  id: number;
  action: string;
  details: string;
  guildId: string | null;
  createdAt: string;
}

function Dashboard() {
  const { user, loading: authLoading, signInWithGoogle, signOut, fetchWithAuth } = useAuth();

  const [guilds, setGuilds] = useState<GuildConfig[]>([]);
  const [logs, setLogs] = useState<ActivityLogItem[]>([]);
  const [loadingData, setLoadingData] = useState(false);
  const [activeTab, setActiveTab] = useState<'configs' | 'logs' | 'database'>('configs');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Form state for creating / editing guild config
  const [formData, setFormData] = useState({
    guildId: '',
    name: '',
    prefix: '/',
    modLogChannel: 'mod-logs',
    serverLogChannel: 'server-logs',
    welcomeChannel: 'welcome',
    ticketCategory: 'Tickets',
    automodEnabled: true,
    xpRate: '1.0',
  });
  const [submitting, setSubmitting] = useState(false);

  // Load data when user logs in
  const loadDashboardData = async () => {
    if (!user) return;
    setLoadingData(true);
    setStatusMessage(null);
    try {
      const [guildsRes, logsRes] = await Promise.all([
        fetchWithAuth('/api/guilds'),
        fetchWithAuth('/api/logs'),
      ]);

      if (guildsRes.ok) {
        const guildsData = await guildsRes.json();
        setGuilds(guildsData.guilds || []);
      }
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setLogs(logsData.logs || []);
      }
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setStatusMessage('Error connecting to backend database API.');
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    if (user) {
      loadDashboardData();
    }
  }, [user]);

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.guildId.trim() || !formData.name.trim()) {
      setStatusMessage('Guild ID and Server Name are required.');
      return;
    }
    setSubmitting(true);
    setStatusMessage(null);
    try {
      const res = await fetchWithAuth('/api/guilds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      if (res.ok) {
        setStatusMessage(`Successfully saved settings for "${formData.name}" to Cloud SQL!`);
        setFormData({
          guildId: '',
          name: '',
          prefix: '/',
          modLogChannel: 'mod-logs',
          serverLogChannel: 'server-logs',
          welcomeChannel: 'welcome',
          ticketCategory: 'Tickets',
          automodEnabled: true,
          xpRate: '1.0',
        });
        await loadDashboardData();
      } else {
        setStatusMessage(data.error || 'Failed to save configuration.');
      }
    } catch (err: any) {
      console.error('Error saving config:', err);
      setStatusMessage('Failed to save to Cloud SQL.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div id="app-root" className="min-h-screen bg-neutral-900 text-neutral-100 flex flex-col font-sans">
      {/* Top Header */}
      <header id="header" className="border-b border-neutral-800 bg-neutral-950/80 backdrop-blur px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-950/70 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-semibold text-neutral-50 tracking-tight">Cloud SQL Integration</h1>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-700/50">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  asia-southeast1
                </span>
              </div>
              <p className="text-xs text-neutral-400">PostgreSQL (Drizzle ORM) &amp; Firebase Auth</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {authLoading ? (
              <div className="text-xs text-neutral-400 flex items-center gap-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Initializing...
              </div>
            ) : user ? (
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <div className="text-sm font-medium text-neutral-200">{user.displayName || user.email}</div>
                  <div className="text-xs text-neutral-400 font-mono">UID: {user.uid.slice(0, 8)}...</div>
                </div>
                {user.photoURL && (
                  <img
                    src={user.photoURL}
                    alt="User Avatar"
                    className="w-8 h-8 rounded-full border border-neutral-700"
                    referrerPolicy="no-referrer"
                  />
                )}
                <button
                  id="sign-out-btn"
                  onClick={signOut}
                  className="px-3 py-1.5 rounded-md border border-neutral-700 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-medium flex items-center gap-1.5 transition"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  Sign Out
                </button>
              </div>
            ) : (
              <button
                id="sign-in-btn"
                onClick={signInWithGoogle}
                className="px-4 py-2 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium flex items-center gap-2 shadow-sm transition"
              >
                <LogIn className="w-4 h-4" />
                Sign in with Google
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main id="main-content" className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Status Alert */}
        {statusMessage && (
          <div
            id="status-alert"
            className="p-4 rounded-lg bg-neutral-800/80 border border-neutral-700 flex items-center justify-between text-sm"
          >
            <div className="flex items-center gap-2.5 text-neutral-200">
              <AlertCircle className="w-4 h-4 text-emerald-400" />
              <span>{statusMessage}</span>
            </div>
            <button
              onClick={() => setStatusMessage(null)}
              className="text-xs text-neutral-400 hover:text-neutral-200"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Database Provisioning Banner */}
        <section id="cloud-sql-info-card" className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg bg-neutral-950 border border-neutral-800">
            <div className="text-xs font-medium text-neutral-400 mb-1 flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-emerald-400" />
              Region
            </div>
            <div className="text-base font-semibold text-neutral-100 font-mono">asia-southeast1</div>
            <div className="text-xs text-neutral-400 mt-1">Singapore Cloud Region</div>
          </div>

          <div className="p-4 rounded-lg bg-neutral-950 border border-neutral-800">
            <div className="text-xs font-medium text-neutral-400 mb-1 flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-emerald-400" />
              Engine
            </div>
            <div className="text-base font-semibold text-neutral-100">PostgreSQL (Cloud SQL)</div>
            <div className="text-xs text-neutral-400 mt-1">Developer Edition</div>
          </div>

          <div className="p-4 rounded-lg bg-neutral-950 border border-neutral-800">
            <div className="text-xs font-medium text-neutral-400 mb-1 flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-emerald-400" />
              Connection
            </div>
            <div className="text-base font-semibold text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              Active (Pooled)
            </div>
            <div className="text-xs text-neutral-400 mt-1">Drizzle ORM + pg.Pool</div>
          </div>

          <div className="p-4 rounded-lg bg-neutral-950 border border-neutral-800">
            <div className="text-xs font-medium text-neutral-400 mb-1 flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              Auth &amp; Security
            </div>
            <div className="text-base font-semibold text-neutral-100">Firebase Auth</div>
            <div className="text-xs text-neutral-400 mt-1">Verified with Firebase Admin</div>
          </div>
        </section>

        {/* Tab Navigation */}
        <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
          <div className="flex items-center gap-2">
            <button
              id="tab-configs-btn"
              onClick={() => setActiveTab('configs')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-2 ${
                activeTab === 'configs'
                  ? 'bg-neutral-800 text-neutral-100 border border-neutral-700'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              Guild Configurations ({guilds.length})
            </button>
            <button
              id="tab-logs-btn"
              onClick={() => setActiveTab('logs')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-2 ${
                activeTab === 'logs'
                  ? 'bg-neutral-800 text-neutral-100 border border-neutral-700'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              Database Activity Logs ({logs.length})
            </button>
            <button
              id="tab-database-btn"
              onClick={() => setActiveTab('database')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-2 ${
                activeTab === 'database'
                  ? 'bg-neutral-800 text-neutral-100 border border-neutral-700'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              Schema &amp; Architecture
            </button>
          </div>

          {user && (
            <button
              id="refresh-btn"
              onClick={loadDashboardData}
              disabled={loadingData}
              className="px-3 py-1.5 rounded-md border border-neutral-800 bg-neutral-900 hover:bg-neutral-800 text-xs text-neutral-300 flex items-center gap-1.5 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingData ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          )}
        </div>

        {/* Not Signed In Warning */}
        {!user && !authLoading && (
          <div
            id="auth-prompt"
            className="p-8 rounded-xl border border-neutral-800 bg-neutral-950/60 text-center max-w-lg mx-auto my-8 space-y-4"
          >
            <div className="w-12 h-12 rounded-full bg-emerald-950/80 border border-emerald-600/30 text-emerald-400 mx-auto flex items-center justify-center">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-neutral-100">Sign In to Manage Cloud SQL Data</h3>
              <p className="text-xs text-neutral-400 mt-1.5 leading-relaxed">
                Cloud SQL Developer Edition in <strong className="text-neutral-300">asia-southeast1</strong> is provisioned and ready. Sign in with Google to synchronize your user profile and persist bot guild configurations.
              </p>
            </div>
            <button
              id="prompt-signin-btn"
              onClick={signInWithGoogle}
              className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium inline-flex items-center gap-2 transition"
            >
              <LogIn className="w-4 h-4" />
              Sign in with Google
            </button>
          </div>
        )}

        {/* Tab 1: Guild Configurations */}
        {user && activeTab === 'configs' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Form */}
            <div className="lg:col-span-1 p-5 rounded-xl border border-neutral-800 bg-neutral-950 space-y-4">
              <div className="flex items-center gap-2">
                <Plus className="w-4 h-4 text-emerald-400" />
                <h2 className="text-sm font-semibold text-neutral-100">Add / Update Guild Setting</h2>
              </div>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Save bot preferences directly to Cloud SQL table <code className="text-emerald-400">guild_configs</code>.
              </p>

              <form onSubmit={handleSaveConfig} className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-neutral-300 mb-1">Guild ID</label>
                  <input
                    id="input-guild-id"
                    type="text"
                    placeholder="e.g. 123456789012345678"
                    value={formData.guildId}
                    onChange={(e) => setFormData({ ...formData, guildId: e.target.value })}
                    className="w-full px-3 py-2 text-xs rounded-md bg-neutral-900 border border-neutral-700 text-neutral-100 focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-neutral-300 mb-1">Server Name</label>
                  <input
                    id="input-guild-name"
                    type="text"
                    placeholder="e.g. Community HQ"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 text-xs rounded-md bg-neutral-900 border border-neutral-700 text-neutral-100 focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-medium text-neutral-300 mb-1">Command Prefix</label>
                    <input
                      id="input-prefix"
                      type="text"
                      placeholder="/"
                      value={formData.prefix}
                      onChange={(e) => setFormData({ ...formData, prefix: e.target.value })}
                      className="w-full px-3 py-2 text-xs rounded-md bg-neutral-900 border border-neutral-700 text-neutral-100 focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-neutral-300 mb-1">XP Multiplier</label>
                    <input
                      id="input-xp"
                      type="text"
                      placeholder="1.0"
                      value={formData.xpRate}
                      onChange={(e) => setFormData({ ...formData, xpRate: e.target.value })}
                      className="w-full px-3 py-2 text-xs rounded-md bg-neutral-900 border border-neutral-700 text-neutral-100 focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-neutral-300 mb-1">Mod Log Channel</label>
                  <input
                    id="input-mod-log"
                    type="text"
                    value={formData.modLogChannel}
                    onChange={(e) => setFormData({ ...formData, modLogChannel: e.target.value })}
                    className="w-full px-3 py-2 text-xs rounded-md bg-neutral-900 border border-neutral-700 text-neutral-100 focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-neutral-300 mb-1">Welcome Channel</label>
                  <input
                    id="input-welcome"
                    type="text"
                    value={formData.welcomeChannel}
                    onChange={(e) => setFormData({ ...formData, welcomeChannel: e.target.value })}
                    className="w-full px-3 py-2 text-xs rounded-md bg-neutral-900 border border-neutral-700 text-neutral-100 focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    id="input-automod"
                    type="checkbox"
                    checked={formData.automodEnabled}
                    onChange={(e) => setFormData({ ...formData, automodEnabled: e.target.checked })}
                    className="rounded border-neutral-700 text-emerald-500 focus:ring-emerald-500 bg-neutral-900"
                  />
                  <label htmlFor="input-automod" className="text-xs text-neutral-300 cursor-pointer">
                    Enable AutoMod Filtering
                  </label>
                </div>

                <button
                  id="submit-guild-btn"
                  type="submit"
                  disabled={submitting}
                  className="w-full py-2 px-4 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium flex items-center justify-center gap-2 transition disabled:opacity-50 mt-2"
                >
                  {submitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Database className="w-3.5 h-3.5" />}
                  {submitting ? 'Persisting to Cloud SQL...' : 'Save Configuration to SQL'}
                </button>
              </form>
            </div>

            {/* List */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-neutral-200">Registered Guilds ({guilds.length})</h3>
                <span className="text-xs text-neutral-400 font-mono">Table: public.guild_configs</span>
              </div>

              {guilds.length === 0 ? (
                <div className="p-8 rounded-xl border border-neutral-800 bg-neutral-950 text-center text-xs text-neutral-400">
                  No guild configurations saved yet. Use the form on the left to add one!
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {guilds.map((g) => (
                    <div
                      key={g.id}
                      className="p-4 rounded-lg border border-neutral-800 bg-neutral-950 hover:border-neutral-700 transition space-y-3"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="text-sm font-semibold text-neutral-100">{g.name}</h4>
                          <span className="text-xs text-neutral-400 font-mono">ID: {g.guildId}</span>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-neutral-900 border border-neutral-700 text-emerald-400">
                          prefix: {g.prefix}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs text-neutral-400 pt-1 border-t border-neutral-900">
                        <div>
                          <span className="block text-[10px] text-neutral-400 uppercase">Mod Log</span>
                          <span className="text-neutral-200 font-mono">#{g.modLogChannel || 'none'}</span>
                        </div>
                        <div>
                          <span className="block text-[10px] text-neutral-400 uppercase">Welcome</span>
                          <span className="text-neutral-200 font-mono">#{g.welcomeChannel || 'none'}</span>
                        </div>
                        <div>
                          <span className="block text-[10px] text-neutral-400 uppercase">AutoMod</span>
                          <span className={g.automodEnabled ? 'text-emerald-400' : 'text-neutral-400'}>
                            {g.automodEnabled ? 'Active' : 'Disabled'}
                          </span>
                        </div>
                        <div>
                          <span className="block text-[10px] text-neutral-400 uppercase">XP Rate</span>
                          <span className="text-neutral-200">{g.xpRate}x</span>
                        </div>
                      </div>

                      <div className="text-[10px] text-neutral-400 pt-1">
                        Added: {new Date(g.createdAt).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Activity Logs */}
        {user && activeTab === 'logs' && (
          <div className="p-5 rounded-xl border border-neutral-800 bg-neutral-950 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-neutral-100">PostgreSQL Audit &amp; Activity Log</h3>
                <p className="text-xs text-neutral-400 mt-0.5">Persisted in <code className="text-emerald-400">activity_logs</code> table</p>
              </div>
              <span className="text-xs text-neutral-400 font-mono">{logs.length} events logged</span>
            </div>

            {logs.length === 0 ? (
              <div className="p-8 text-center text-xs text-neutral-400">
                No activity logs yet. When you configure guilds, activities are recorded here.
              </div>
            ) : (
              <div className="space-y-2">
                {logs.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 rounded-lg bg-neutral-900/90 border border-neutral-800/80 flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-3">
                      <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-neutral-800 text-emerald-400 border border-neutral-700">
                        {item.action}
                      </span>
                      <span className="text-neutral-200">{item.details}</span>
                    </div>
                    <span className="text-neutral-400 text-[11px] font-mono whitespace-nowrap ml-4">
                      {new Date(item.createdAt).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Database & Schema Info */}
        {activeTab === 'database' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 rounded-xl border border-neutral-800 bg-neutral-950 space-y-3">
              <h3 className="text-sm font-semibold text-neutral-100 flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-400" />
                Applied Drizzle Schema
              </h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                The database schema has been verified using <code className="text-neutral-300">information_schema.columns</code> in Cloud SQL PostgreSQL.
              </p>
              <div className="bg-neutral-900 p-3 rounded-lg border border-neutral-800 font-mono text-xs text-neutral-300 space-y-2 overflow-x-auto">
                <div><strong className="text-emerald-400">users</strong>: id, uid, email, display_name, photo_url, created_at</div>
                <div><strong className="text-emerald-400">guild_configs</strong>: id, user_id, guild_id, name, prefix, mod_log_channel, server_log_channel, welcome_channel, ticket_category, automod_enabled, xp_rate, created_at</div>
                <div><strong className="text-emerald-400">activity_logs</strong>: id, user_id, guild_id, action, details, created_at</div>
              </div>
            </div>

            <div className="p-5 rounded-xl border border-neutral-800 bg-neutral-950 space-y-3">
              <h3 className="text-sm font-semibold text-neutral-100 flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-400" />
                Connection Pooling &amp; Best Practices
              </h3>
              <ul className="text-xs text-neutral-400 space-y-2 leading-relaxed list-disc list-inside">
                <li><strong className="text-neutral-200">Pooled Clients</strong>: Uses singleton <code className="text-neutral-300">pg.Pool</code> method with max 10 connections and 15-second timeouts.</li>
                <li><strong className="text-neutral-200">No Infinite Loops</strong>: Zero blocking startup health loops or crash-prone reconnect loops.</li>
                <li><strong className="text-neutral-200">Firebase Auth Token Guard</strong>: Bearer ID token decoded via Firebase Admin SDK with UID foreign key relationships.</li>
                <li><strong className="text-neutral-200">Developer Edition Scale-To-Zero</strong>: Region <code className="text-emerald-400">asia-southeast1</code> ensures optimal latency for Southeast Asia workloads.</li>
              </ul>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer id="footer" className="border-t border-neutral-800 bg-neutral-950 px-6 py-4 mt-auto text-center text-xs text-neutral-400">
        Google Cloud SQL (PostgreSQL) • Instance: ai-studio-ca7be320 • Region: asia-southeast1
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  );
}
