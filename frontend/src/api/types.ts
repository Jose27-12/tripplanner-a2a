// Tipos del contrato REST (ver docs/api-contrato.md y docs/modelo-datos.md).

export type TripEstado = "PLANIFICANDO" | "CONFIRMADO" | "CANCELADO";
export type Moneda = "COP" | "USD";

export interface Trip {
  tripId: string;
  origen: string;
  destino: string;
  fecha_inicio: string;
  fecha_fin: string;
  viajeros: number;
  presupuesto?: number | null;
  moneda: Moneda;
  estado: TripEstado;
  createdAt: string;
  updatedAt: string;
}

export type TripInput = Pick<Trip, "origen" | "destino" | "fecha_inicio" | "fecha_fin" | "viajeros"> & {
  presupuesto?: number | null;
  moneda?: Moneda;
  estado?: TripEstado;
};

export interface ItineraryDay {
  dia: number;
  fecha?: string;
  actividades: string[];
}

export interface Itinerary {
  tripId: string;
  dias: ItineraryDay[];
  updatedAt: string;
}

export type ReservaTipo = "VUELO" | "HOTEL" | "ACTIVIDAD";
export type ReservaEstado = "SIMULADA" | "PENDIENTE" | "CONFIRMADA";

export interface Reservation {
  resId: string;
  tripId: string;
  tipo: ReservaTipo;
  estado: ReservaEstado;
  detalle: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface Preferences {
  actividades?: string[];
  presupuesto_tipo?: "ECONOMICO" | "MODERADO" | "PREMIUM";
  restricciones?: string[];
  aerolineas_preferidas?: string[];
  asiento_preferido?: string;
  updatedAt?: string;
}
