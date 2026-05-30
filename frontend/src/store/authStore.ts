import { create } from "zustand";
import { persist } from "zustand/middleware";
import axios from "axios";

interface AuthUser {
  id: string;
  email: string;
  full_name: string;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, fullName: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,

      login: async (email, password) => {
        const form = new FormData();
        form.append("username", email);
        form.append("password", password);
        const { data } = await axios.post("/api/auth/token", form);
        set({
          token: data.access_token,
          user: { id: data.user_id, email: data.email, full_name: data.full_name },
        });
        axios.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
      },

      register: async (email, fullName, password) => {
        const { data } = await axios.post("/api/auth/register", {
          email,
          full_name: fullName,
          password,
        });
        set({
          token: data.access_token,
          user: { id: data.user_id, email: data.email, full_name: data.full_name },
        });
        axios.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
      },

      logout: () => {
        set({ token: null, user: null });
        delete axios.defaults.headers.common["Authorization"];
      },
    }),
    {
      name: "raredx-auth",
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          axios.defaults.headers.common["Authorization"] = `Bearer ${state.token}`;
        }
      },
    }
  )
);
