export interface ServiceConnectivity {
  status: 'connected' | 'unavailable';
  details?: string;
  latency_ms?: number | null;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  environment: string;
  timestamp: string;
  postgres: ServiceConnectivity;
  mongodb: ServiceConnectivity;
}
