import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { Dna, Loader2, Eye, EyeOff } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

const registerSchema = loginSchema
  .extend({
    full_name: z.string().min(2, "Name must be at least 2 characters"),
    confirm_password: z.string(),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

type LoginForm = z.infer<typeof loginSchema>;
type RegisterForm = z.infer<typeof registerSchema>;

const inp = cn(
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition",
  "focus:ring-2 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
);

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [showPass, setShowPass] = useState(false);
  const { login, register: registerUser } = useAuthStore();
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<LoginForm | RegisterForm>({
    resolver: zodResolver(mode === "login" ? loginSchema : registerSchema) as ReturnType<typeof zodResolver>,
  });

  const switchMode = () => {
    setMode((m) => (m === "login" ? "register" : "login"));
    reset();
  };

  const onSubmit = async (data: LoginForm | RegisterForm) => {
    try {
      if (mode === "login") {
        const d = data as LoginForm;
        await login(d.email, d.password);
      } else {
        const d = data as RegisterForm;
        await registerUser(d.email, d.full_name, d.password);
      }
      toast.success(mode === "login" ? "Welcome back!" : "Account created!");
      navigate("/cases");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Authentication failed";
      toast.error(msg);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="card p-8 space-y-6">
          {/* Logo */}
          <div className="text-center space-y-2">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg">
              <Dna className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
              {mode === "login" ? "Sign in to RareDx" : "Create account"}
            </h1>
            <p className="text-sm text-slate-500">AI-powered rare disease diagnostics</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {mode === "register" && (
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Full Name
                </label>
                <input
                  {...register("full_name" as keyof (LoginForm | RegisterForm))}
                  className={inp}
                  placeholder="Dr. Jane Smith"
                />
                {(errors as { full_name?: { message?: string } }).full_name && (
                  <p className="text-xs text-red-500">
                    {(errors as { full_name?: { message?: string } }).full_name?.message}
                  </p>
                )}
              </div>
            )}

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Email</label>
              <input
                {...register("email")}
                type="email"
                className={inp}
                placeholder="doctor@hospital.org"
              />
              {errors.email && <p className="text-xs text-red-500">{errors.email.message}</p>}
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Password</label>
              <div className="relative">
                <input
                  {...register("password")}
                  type={showPass ? "text" : "password"}
                  className={cn(inp, "pr-10")}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPass((v) => !v)}
                  className="absolute right-3 top-2.5 text-slate-400"
                >
                  {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && <p className="text-xs text-red-500">{errors.password.message}</p>}
            </div>

            {mode === "register" && (
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Confirm Password
                </label>
                <input
                  {...register("confirm_password" as keyof (LoginForm | RegisterForm))}
                  type="password"
                  className={inp}
                  placeholder="••••••••"
                />
                {(errors as { confirm_password?: { message?: string } }).confirm_password && (
                  <p className="text-xs text-red-500">
                    {(errors as { confirm_password?: { message?: string } }).confirm_password?.message}
                  </p>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="gradient-brand w-full rounded-xl py-2.5 text-sm font-semibold text-white disabled:opacity-70 flex items-center justify-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {mode === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <div className="text-center text-sm">
            <span className="text-slate-500">
              {mode === "login" ? "Don't have an account? " : "Already have an account? "}
            </span>
            <button
              onClick={switchMode}
              className="font-semibold text-indigo-600 hover:underline dark:text-indigo-400"
            >
              {mode === "login" ? "Register" : "Sign in"}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
