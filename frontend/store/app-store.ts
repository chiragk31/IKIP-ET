/**
 * Zustand Global State Store
 *
 * Global client-side state for the IKIP platform.
 *
 * Rules:
 * - Server state (API data) belongs in TanStack Query, not here.
 * - Zustand manages UI state, user preferences, and cross-feature state.
 * - Never store large datasets in Zustand — use React Query.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { User, ChatMessage } from '@/types';

// -----------------------------------------------
// App Store Interface
// -----------------------------------------------

interface AppStore {
  // User state
  user: User | null;
  setUser: (user: User | null) => void;

  // UI state
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // Active document
  activeDocumentId: string | null;
  setActiveDocumentId: (id: string | null) => void;

  // Chat history (current session)
  chatMessages: ChatMessage[];
  addChatMessage: (message: ChatMessage) => void;
  clearChatHistory: () => void;

  // Upload state
  uploadInProgress: boolean;
  setUploadInProgress: (inProgress: boolean) => void;

  // Notifications
  notifications: Notification[];
  addNotification: (notification: Notification) => void;
  dismissNotification: (id: string) => void;
  clearNotifications: () => void;
}

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
}

// -----------------------------------------------
// Store Implementation
// -----------------------------------------------

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      // User state
      user: null,
      setUser: (user) => set({ user }),

      // UI state
      sidebarOpen: true,
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      // Active document
      activeDocumentId: null,
      setActiveDocumentId: (activeDocumentId) => set({ activeDocumentId }),

      // Chat history
      chatMessages: [],
      addChatMessage: (message) =>
        set((state) => ({
          chatMessages: [...state.chatMessages, message],
        })),
      clearChatHistory: () => set({ chatMessages: [] }),

      // Upload state
      uploadInProgress: false,
      setUploadInProgress: (uploadInProgress) => set({ uploadInProgress }),

      // Notifications
      notifications: [],
      addNotification: (notification) =>
        set((state) => ({
          notifications: [...state.notifications, notification],
        })),
      dismissNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),
      clearNotifications: () => set({ notifications: [] }),
    }),
    {
      name: 'ikip-app-store',
      storage: createJSONStorage(() => localStorage),
      // Only persist user preferences, not transient state
      partialize: (state) => ({
        sidebarOpen: state.sidebarOpen,
        user: state.user,
      }),
    }
  )
);
