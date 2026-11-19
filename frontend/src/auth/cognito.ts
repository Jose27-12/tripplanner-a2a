// Autenticación con Amazon Cognito (flujo SRP: la contraseña nunca viaja en claro).
// El navegador solo guarda tokens JWT de Cognito; jamás credenciales de AWS.
import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserAttribute,
  CognitoUserPool,
  CognitoUserSession,
} from "amazon-cognito-identity-js";
import { config } from "../config";

const pool = new CognitoUserPool({ UserPoolId: config.userPoolId, ClientId: config.clientId });

export interface SessionInfo {
  email: string;
  sub: string;
  name?: string;
  idToken: string;
  accessToken: string;
}

function toInfo(session: CognitoUserSession): SessionInfo {
  const payload = session.getIdToken().decodePayload();
  return {
    email: payload.email,
    sub: payload.sub,
    name: payload.name,
    idToken: session.getIdToken().getJwtToken(),
    accessToken: session.getAccessToken().getJwtToken(),
  };
}

function userFor(email: string) {
  return new CognitoUser({ Username: email.trim().toLowerCase(), Pool: pool });
}

/** Mensajes de error de Cognito traducidos para el usuario. */
export function authErrorMessage(err: unknown): string {
  const code = (err as { code?: string; name?: string })?.code ?? (err as { name?: string })?.name;
  switch (code) {
    case "NotAuthorizedException":
      return "Correo o contraseña incorrectos.";
    case "UserNotFoundException":
      return "Correo o contraseña incorrectos.";
    case "UserNotConfirmedException":
      return "Debes confirmar tu correo antes de iniciar sesión.";
    case "UsernameExistsException":
      return "Ya existe una cuenta con ese correo.";
    case "InvalidPasswordException":
      return "La contraseña debe tener al menos 8 caracteres, con mayúsculas, minúsculas y números.";
    case "CodeMismatchException":
      return "El código no es correcto.";
    case "ExpiredCodeException":
      return "El código expiró. Solicita uno nuevo.";
    case "LimitExceededException":
    case "TooManyRequestsException":
      return "Demasiados intentos. Espera unos minutos e inténtalo de nuevo.";
    case "InvalidParameterException":
      return "Revisa los datos ingresados.";
    default:
      return "No fue posible completar la operación. Inténtalo de nuevo.";
  }
}

export function signUp(email: string, password: string, name: string): Promise<void> {
  const attrs = [
    new CognitoUserAttribute({ Name: "email", Value: email.trim().toLowerCase() }),
    ...(name.trim() ? [new CognitoUserAttribute({ Name: "name", Value: name.trim() })] : []),
  ];
  return new Promise((resolve, reject) =>
    pool.signUp(email.trim().toLowerCase(), password, attrs, [], (err) => (err ? reject(err) : resolve())),
  );
}

export function confirmSignUp(email: string, code: string): Promise<void> {
  return new Promise((resolve, reject) =>
    userFor(email).confirmRegistration(code.trim(), true, (err) => (err ? reject(err) : resolve())),
  );
}

export function resendCode(email: string): Promise<void> {
  return new Promise((resolve, reject) =>
    userFor(email).resendConfirmationCode((err) => (err ? reject(err) : resolve())),
  );
}

export function signIn(email: string, password: string): Promise<SessionInfo> {
  const user = userFor(email);
  const details = new AuthenticationDetails({ Username: email.trim().toLowerCase(), Password: password });
  return new Promise((resolve, reject) =>
    user.authenticateUser(details, {
      onSuccess: (session) => resolve(toInfo(session)),
      onFailure: reject,
      newPasswordRequired: () => reject({ code: "NotAuthorizedException" }),
    }),
  );
}

export function forgotPassword(email: string): Promise<void> {
  return new Promise((resolve, reject) =>
    userFor(email).forgotPassword({ onSuccess: () => resolve(), onFailure: reject }),
  );
}

export function confirmNewPassword(email: string, code: string, password: string): Promise<void> {
  return new Promise((resolve, reject) =>
    userFor(email).confirmPassword(code.trim(), password, {
      onSuccess: () => resolve(),
      onFailure: reject,
    }),
  );
}

/** Sesión actual; renueva los tokens con el refresh token si expiraron. */
export function currentSession(): Promise<SessionInfo | null> {
  const user = pool.getCurrentUser();
  if (!user) return Promise.resolve(null);
  return new Promise((resolve) =>
    user.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session || !session.isValid()) resolve(null);
      else resolve(toInfo(session));
    }),
  );
}

export function signOut(): void {
  pool.getCurrentUser()?.signOut();
}
