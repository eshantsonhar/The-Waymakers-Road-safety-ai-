import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from './store/useStore';
import { useWebSocket } from './hooks/useWebSocket';
import { useApi } from './hooks/useApi';
import { CommandCenter } from './views/CommandCenter';
import { CitizenInterface } from './views/CitizenInterface';
import { AdminDashboard } from './views/AdminDashboard';
import { NavBar } from './components/NavBar';
import { NotificationPanel } from './components/NotificationPanel';
import { ConnectionStatus } from './components/ConnectionStatus';

export default function App() {
  const { activeView } = useStore();
  useWebSocket();
  useApi();

  return (
    <div className="h-screen w-screen overflow-hidden bg-sos-bg bg-grid flex flex-col">
      {/* Navigation */}
      <NavBar />

      {/* Connection Status */}
      <ConnectionStatus />

      {/* Main Content */}
      <div className="flex-1 overflow-hidden relative">
        <AnimatePresence mode="wait">
          {activeView === 'command' && (
            <motion.div
              key="command"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0"
            >
              <CommandCenter />
            </motion.div>
          )}
          {activeView === 'citizen' && (
            <motion.div
              key="citizen"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0"
            >
              <CitizenInterface />
            </motion.div>
          )}
          {activeView === 'admin' && (
            <motion.div
              key="admin"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0"
            >
              <AdminDashboard />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Notification Panel */}
      <NotificationPanel />
    </div>
  );
}
