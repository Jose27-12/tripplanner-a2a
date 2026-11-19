// Login, registro (con confirmación por correo) y recuperación de contraseña.
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import * as cognito from "../auth/cognito";
import { Logo } from "../components/Layout";
import { Alert, Button, Field, Input } from "../components/ui";

function AuthShell({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="flex min-h-full items-center justify-center bg-gradient-to-br from-brand-50 via-white to-sky-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
      </div>
    </div>
  );
}

export function LoginPage() {
  const { status, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState((location.state as { email?: string })?.email ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const notice = (location.state as { notice?: string })?.notice;

  if (status === "authenticated") return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signIn(email, password);
      const from = (location.state as { from?: string })?.from ?? "/";
      navigate(from, { replace: true });
    } catch (err) {
      const code = (err as { code?: string }).code;
      if (code === "UserNotConfirmedException") {
        navigate("/registro", { state: { email, step: "confirm" } });
        return;
      }
      setError(cognito.authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Inicia sesión" subtitle="Planifica, organiza y gestiona tus viajes con IA.">
      <form onSubmit={onSubmit} className="space-y-4">
        {notice && <Alert kind="success">{notice}</Alert>}
        {error && <Alert>{error}</Alert>}
        <Field label="Correo electrónico">
          <Input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Contraseña">
          <Input type="password" autoComplete="current-password" required value={password}
            onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <Button type="submit" loading={loading} className="w-full">Entrar</Button>
      </form>
      <div className="mt-6 flex justify-between text-sm">
        <Link to="/recuperar" className="text-slate-500 hover:text-slate-700">¿Olvidaste tu contraseña?</Link>
        <Link to="/registro" className="font-medium text-brand-700 hover:text-brand-600">Crear cuenta</Link>
      </div>
    </AuthShell>
  );
}

export function RegisterPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const initial = location.state as { email?: string; step?: "confirm" } | null;
  const [step, setStep] = useState<"form" | "confirm">(initial?.step ?? "form");
  const [name, setName] = useState("");
  const [email, setEmail] = useState(initial?.email ?? "");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);

  async function onRegister(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await cognito.signUp(email, password, name);
      setStep("confirm");
      setInfo(`Te enviamos un código de verificación a ${email}.`);
    } catch (err) {
      setError(cognito.authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function onConfirm(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await cognito.confirmSignUp(email, code);
      navigate("/login", { state: { email, notice: "Cuenta confirmada. Ya puedes iniciar sesión." } });
    } catch (err) {
      setError(cognito.authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function onResend() {
    setError("");
    try {
      await cognito.resendCode(email);
      setInfo("Te enviamos un nuevo código.");
    } catch (err) {
      setError(cognito.authErrorMessage(err));
    }
  }

  if (step === "confirm") {
    return (
      <AuthShell title="Confirma tu correo" subtitle="Ingresa el código de 6 dígitos que recibiste.">
        <form onSubmit={onConfirm} className="space-y-4">
          {info && <Alert kind="info">{info}</Alert>}
          {error && <Alert>{error}</Alert>}
          <Field label="Correo electrónico">
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Código de verificación">
            <Input inputMode="numeric" autoComplete="one-time-code" required value={code}
              onChange={(e) => setCode(e.target.value)} />
          </Field>
          <Button type="submit" loading={loading} className="w-full">Confirmar</Button>
        </form>
        <button onClick={onResend} className="mt-4 text-sm text-brand-700 hover:text-brand-600">
          Reenviar código
        </button>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Crea tu cuenta" subtitle="Tus viajes y reservas quedan guardados de forma segura.">
      <form onSubmit={onRegister} className="space-y-4">
        {error && <Alert>{error}</Alert>}
        <Field label="Nombre">
          <Input autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Correo electrónico">
          <Input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Contraseña" hint="Mínimo 8 caracteres, con mayúsculas, minúsculas y números.">
          <Input type="password" autoComplete="new-password" required minLength={8} value={password}
            onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <Button type="submit" loading={loading} className="w-full">Crear cuenta</Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">
        ¿Ya tienes cuenta? <Link to="/login" className="font-medium text-brand-700">Inicia sesión</Link>
      </p>
    </AuthShell>
  );
}

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<"email" | "reset">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onRequest(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await cognito.forgotPassword(email);
      setStep("reset");
    } catch (err) {
      setError(cognito.authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function onReset(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await cognito.confirmNewPassword(email, code, password);
      navigate("/login", { state: { email, notice: "Contraseña actualizada. Inicia sesión." } });
    } catch (err) {
      setError(cognito.authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Recupera tu contraseña">
      {step === "email" ? (
        <form onSubmit={onRequest} className="space-y-4">
          {error && <Alert>{error}</Alert>}
          <Field label="Correo electrónico">
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Button type="submit" loading={loading} className="w-full">Enviar código</Button>
        </form>
      ) : (
        <form onSubmit={onReset} className="space-y-4">
          <Alert kind="info">Si la cuenta existe, enviamos un código a {email}.</Alert>
          {error && <Alert>{error}</Alert>}
          <Field label="Código">
            <Input inputMode="numeric" required value={code} onChange={(e) => setCode(e.target.value)} />
          </Field>
          <Field label="Nueva contraseña" hint="Mínimo 8 caracteres, con mayúsculas, minúsculas y números.">
            <Input type="password" autoComplete="new-password" required minLength={8} value={password}
              onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <Button type="submit" loading={loading} className="w-full">Cambiar contraseña</Button>
        </form>
      )}
      <p className="mt-6 text-center text-sm">
        <Link to="/login" className="text-slate-500 hover:text-slate-700">Volver al inicio de sesión</Link>
      </p>
    </AuthShell>
  );
}
