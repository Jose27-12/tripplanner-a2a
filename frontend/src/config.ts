// Configuración pública del frontend (no contiene secretos ni credenciales AWS).
function required(name: string): string {
  const value = import.meta.env[name] as string | undefined;
  if (!value) throw new Error(`Falta la variable de entorno ${name} (ver .env.example)`);
  return value;
}

export const config = {
  region: required("VITE_AWS_REGION"),
  apiUrl: required("VITE_API_URL").replace(/\/$/, ""),
  userPoolId: required("VITE_COGNITO_USER_POOL_ID"),
  clientId: required("VITE_COGNITO_CLIENT_ID"),
  orchestratorArn: required("VITE_ORCHESTRATOR_ARN"),
};

/** Endpoint de invocación HTTP streaming del OrchestratorAgent (canal 2, sin API Gateway). */
export const agentInvocationUrl =
  `https://bedrock-agentcore.${config.region}.amazonaws.com/runtimes/` +
  `${encodeURIComponent(config.orchestratorArn)}/invocations?qualifier=DEFAULT`;
