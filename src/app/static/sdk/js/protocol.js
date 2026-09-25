// Chalkin Sense - SDK JS - capa de protocolo
// Licencia: GPL-3.0
//
// Única fuente de verdad del protocolo BLE de Chalkin Sense. No usa Web
// Bluetooth ni toca el DOM: solo parsea/construye bytes.

/**
 * Versión del protocolo BLE (congelada).
 *
 * A partir de 1.0.0 los UUIDs y el formato de las tramas no cambian sin subir
 * de versión major. Los consumidores pueden comprobarla y fallar de forma
 * explícita si no les encaja.
 */
export const PROTOCOL_VERSION = '1.0.0';

/** Nombre anunciado por el dispositivo (filtro de emparejamiento). */
export const DEVICE_NAME = 'ChalkinSense';

/** UUIDs del servicio y sus características. */
export const SERVICE_UUID = '8f3a2b1e-5c4a-4d6e-9f20-4a1b2c3d4e5f';
export const FORCE_CHAR_UUID = '8f3a2b1e-5c4a-4d6e-9f20-4a1b2c3d4e60';
export const CTRL_CHAR_UUID = '8f3a2b1e-5c4a-4d6e-9f20-4a1b2c3d4e61';

/** Muestras máximas por notificación (coincide con SAMPLES_PER_BATCH). */
export const SAMPLES_PER_BATCH = 8;
/** Cabecera del frame de fuerza: uint16 seq + uint8 count. */
export const FRAME_HEADER_BYTES = 3;
/** Tamaño de cada muestra: uint32 ts_ms + float32 kg. */
export const SAMPLE_BYTES = 8;

/** Comandos de control aceptados por el firmware. */
export const COMMANDS = Object.freeze({
  TARA: 'TARA',
  CAL: 'CAL',
  GETCAL: 'GETCAL',
  STATS: 'STATS',
  RESET: 'RESET',
  SIM_PULL: 'SIM_PULL',
  SIM_AUTO: 'SIM_AUTO',
});

/** Error de protocolo (trama mal formada, etc.). */
export class ProtocolError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ProtocolError';
  }
}

function toDataView(data) {
  if (data instanceof DataView) return data;
  if (data instanceof ArrayBuffer) return new DataView(data);
  if (ArrayBuffer.isView(data)) {
    return new DataView(data.buffer, data.byteOffset, data.byteLength);
  }
  throw new ProtocolError('Se esperaba DataView, Uint8Array o ArrayBuffer');
}

function toUint8Array(data) {
  if (data instanceof Uint8Array) return data;
  const dv = toDataView(data);
  return new Uint8Array(dv.buffer, dv.byteOffset, dv.byteLength);
}

/**
 * Parsea una notificación de la característica de fuerza.
 *
 * Formato (little-endian):
 *   uint16 seq · uint8 count · count × (uint32 ts_ms · float32 kg)
 *
 * @param {DataView|Uint8Array|ArrayBuffer} data
 * @returns {{seq:number, count:number, samples:Array<{ts:number, kg:number}>}}
 * @throws {ProtocolError} si la trama está truncada o `count` es imposible.
 */
export function parseForceFrame(data) {
  const dv = toDataView(data);

  if (dv.byteLength < FRAME_HEADER_BYTES) {
    throw new ProtocolError(
      `Trama demasiado corta: ${dv.byteLength} bytes (mínimo ${FRAME_HEADER_BYTES})`);
  }

  const seq = dv.getUint16(0, true);
  const count = dv.getUint8(2);

  if (count > SAMPLES_PER_BATCH) {
    throw new ProtocolError(
      `count=${count} supera SAMPLES_PER_BATCH=${SAMPLES_PER_BATCH}`);
  }

  const needed = FRAME_HEADER_BYTES + count * SAMPLE_BYTES;
  if (dv.byteLength < needed) {
    throw new ProtocolError(
      `Trama truncada: ${dv.byteLength} bytes, se esperaban ${needed} para count=${count}`);
  }

  const samples = new Array(count);
  for (let i = 0; i < count; i++) {
    const o = FRAME_HEADER_BYTES + i * SAMPLE_BYTES;
    samples[i] = { ts: dv.getUint32(o, true), kg: dv.getFloat32(o + 4, true) };
  }

  return { seq, count, samples };
}

/**
 * Construye una trama de fuerza. Útil para tests y para simuladores.
 *
 * @param {{seq?:number, samples?:Array<{ts:number, kg:number}>}} frame
 * @returns {Uint8Array}
 */
export function encodeForceFrame({ seq = 0, samples = [] } = {}) {
  if (samples.length > SAMPLES_PER_BATCH) {
    throw new ProtocolError(
      `${samples.length} muestras superan SAMPLES_PER_BATCH=${SAMPLES_PER_BATCH}`);
  }
  const bytes = new Uint8Array(FRAME_HEADER_BYTES + samples.length * SAMPLE_BYTES);
  const dv = new DataView(bytes.buffer);
  dv.setUint16(0, seq & 0xffff, true);
  dv.setUint8(2, samples.length);
  samples.forEach((s, i) => {
    const o = FRAME_HEADER_BYTES + i * SAMPLE_BYTES;
    dv.setUint32(o, s.ts >>> 0, true);
    dv.setFloat32(o + 4, s.kg, true);
  });
  return bytes;
}

/**
 * Nº de frames perdidos entre `prevSeq` y `seq` (asumiendo frames consecutivos).
 * Devuelve 0 si `prevSeq` es nulo (primera trama) o si son consecutivos.
 */
export function sequenceGap(prevSeq, seq) {
  if (prevSeq === null || prevSeq === undefined) return 0;
  const expected = (prevSeq + 1) & 0xffff;
  return (seq - expected) & 0xffff;
}

/**
 * Codifica un comando de control añadiendo el terminador `\n`.
 * @param {string} cmd
 * @returns {Uint8Array}
 */
export function encodeCommand(cmd) {
  const text = String(cmd).replace(/\r?\n$/, '');
  return new TextEncoder().encode(text + '\n');
}

/**
 * Decodifica la respuesta de texto de la característica de control.
 * @param {DataView|Uint8Array|ArrayBuffer} data
 * @returns {string}
 */
export function decodeResponse(data) {
  return new TextDecoder().decode(toUint8Array(data)).trim();
}

/** Constantes agrupadas, cómodas para exportar a otros proyectos. */
export const PROTOCOL = Object.freeze({
  version: PROTOCOL_VERSION,
  deviceName: DEVICE_NAME,
  serviceUuid: SERVICE_UUID,
  forceCharUuid: FORCE_CHAR_UUID,
  ctrlCharUuid: CTRL_CHAR_UUID,
  samplesPerBatch: SAMPLES_PER_BATCH,
  frameHeaderBytes: FRAME_HEADER_BYTES,
  sampleBytes: SAMPLE_BYTES,
  commands: COMMANDS,
});
