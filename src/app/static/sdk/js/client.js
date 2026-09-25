// Chalkin Sense - SDK JS - cliente BLE
// Licencia: GPL-3.0
//
// Orquestación de Web Bluetooth: conectar/desconectar, suscripción a la
// característica de fuerza, parseo de frames y envío de comandos. No toca el
// DOM y no guarda estado persistente.

import {
  DEVICE_NAME,
  SERVICE_UUID,
  FORCE_CHAR_UUID,
  CTRL_CHAR_UUID,
  COMMANDS,
  decodeResponse,
  encodeCommand,
  parseForceFrame,
  sequenceGap,
} from './protocol.js';
import { Metrics } from './metrics.js';

/** Nombres de los eventos emitidos por el cliente. */
export const SenseEvent = Object.freeze({
  SAMPLE: 'sample',   // { ts, kg, seq }
  PULL_END: 'pullEnd', // métricas del pull terminado
  METRICS: 'metrics', // snapshot acumulado
  COMMAND: 'command', // { text } respuesta del dispositivo
  STATUS: 'status',   // { connected, name?, mtu? }
  ERROR: 'error',     // { error, fatal? }
});

function makeEvent(type, detail) {
  if (typeof CustomEvent === 'function') return new CustomEvent(type, { detail });
  const ev = new Event(type);
  ev.detail = detail;
  return ev;
}

/**
 * Cliente del protocolo BLE de Chalkin Sense.
 *
 * Emite eventos (addEventListener): `sample`, `pullEnd`, `metrics`,
 * `command`, `status`, `error`.
 *
 * @example
 *   const client = new SenseClient();
 *   client.addEventListener('metrics', e => console.log(e.detail.peakKg));
 *   await client.connect();
 */
export class SenseClient extends EventTarget {
  /** ¿Hay Web Bluetooth en este entorno? */
  static isSupported(bluetooth) {
    const nav = globalThis.navigator;
    return !!(bluetooth || (nav && nav.bluetooth));
  }

  /**
   * @param {object} [options]
   * @param {object} [options.bluetooth] Inyección de Web Bluetooth (por defecto
   *   `navigator.bluetooth`). Permite testear en Node con un mock.
   * @param {string} [options.deviceName]
   * @param {string} [options.serviceUuid]
   * @param {string} [options.forceCharUuid]
   * @param {string} [options.ctrlCharUuid]
   * @param {object} [options.metrics] Opciones para {@link Metrics}
   */
  constructor(options = {}) {
    super();
    const nav = globalThis.navigator;
    this.bluetooth = options.bluetooth ?? (nav && nav.bluetooth) ?? null;
    this.deviceName = options.deviceName ?? DEVICE_NAME;
    this.serviceUuid = options.serviceUuid ?? SERVICE_UUID;
    this.forceCharUuid = options.forceCharUuid ?? FORCE_CHAR_UUID;
    this.ctrlCharUuid = options.ctrlCharUuid ?? CTRL_CHAR_UUID;

    this.metrics = new Metrics(options.metrics ?? {});

    this._device = null;
    this._server = null;
    this._forceChar = null;
    this._ctrlChar = null;
    this._connected = false;
    this._lastSeq = null;
    this._forceListener = null;
    this._ctrlListener = null;
  }

  /** ¿Está conectado ahora mismo? */
  get isConnected() {
    return this._connected;
  }

  /** Frames perdidos acumulados (por huecos de `seq`). */
  get lostPackets() {
    return this.metrics.get().lostPackets;
  }

  /** Muestras de la ventana actual (para gráficas, etc.). */
  get samples() {
    return this.metrics.samples;
  }

  /**
   * Pide un dispositivo, conecta y se suscribe a las notificaciones.
   * @throws {Error} si no hay Web Bluetooth o si falla la conexión.
   */
  async connect() {
    if (!this.bluetooth) {
      const error = new Error(
        'Web Bluetooth no disponible. Usa Chrome/Edge/Android sobre un ' +
        'contexto seguro (https o http://localhost).');
      this._emit(SenseEvent.ERROR, { error, fatal: true });
      throw error;
    }

    try {
      this._device = await this.bluetooth.requestDevice({
        filters: [{ name: this.deviceName }],
        optionalServices: [this.serviceUuid],
      });
      this._device.addEventListener('gattserverdisconnected', this._onGattDisconnected);

      this._server = await this._device.gatt.connect();
      const service = await this._server.getPrimaryService(this.serviceUuid);
      this._forceChar = await service.getCharacteristic(this.forceCharUuid);
      this._ctrlChar = await service.getCharacteristic(this.ctrlCharUuid);

      this._forceListener = (e) => this._onForce(e.target.value);
      this._ctrlListener = (e) => this._onCtrl(e.target.value);
      this._forceChar.addEventListener('characteristicvaluechanged', this._forceListener);
      this._ctrlChar.addEventListener('characteristicvaluechanged', this._ctrlListener);

      await this._ctrlChar.startNotifications();
      await this._forceChar.startNotifications();

      this._lastSeq = null;
      this.metrics.reset();
      this._connected = true;
      this._emit(SenseEvent.STATUS, {
        connected: true,
        name: this._device.name ?? null,
        mtu: this._server.mtu ?? null,
      });
    } catch (error) {
      this._teardown();
      this._emit(SenseEvent.ERROR, { error, fatal: true });
      throw error;
    }
  }

  /** Desconecta del dispositivo. */
  async disconnect() {
    if (this._device && this._device.gatt && this._device.gatt.connected) {
      this._device.gatt.disconnect();
    }
    this._handleDisconnected();
  }

  /**
   * Envía un comando de control en crudo (se añade `\n`).
   * @param {string} cmd
   */
  async sendCommand(cmd) {
    if (!this._ctrlChar) {
      const error = new Error('No conectado');
      this._emit(SenseEvent.ERROR, { error });
      throw error;
    }
    const bytes = encodeCommand(cmd);
    if (typeof this._ctrlChar.writeValueWithResponse === 'function') {
      await this._ctrlChar.writeValueWithResponse(bytes);
    } else {
      await this._ctrlChar.writeValue(bytes);
    }
    return true;
  }

  /** Fija el cero con la carga actual. */
  tare() { return this.sendCommand(COMMANDS.TARA); }

  /**
   * Calibra la escala con una masa conocida (kg).
   * @param {number} kg
   */
  calibrate(kg) {
    const value = Number(kg);
    if (!Number.isFinite(value) || value <= 0) {
      const error = new RangeError('La masa de calibración debe ser un número > 0 kg');
      this._emit(SenseEvent.ERROR, { error });
      return Promise.reject(error);
    }
    return this.sendCommand(`${COMMANDS.CAL} ${value}`);
  }

  /** Pide los parámetros de calibración actuales. */
  getCalibration() { return this.sendCommand(COMMANDS.GETCAL); }

  /** Pide las métricas del pull en curso. */
  requestStats() { return this.sendCommand(COMMANDS.STATS); }

  /** Reinicia el dispositivo. */
  reset() { return this.sendCommand(COMMANDS.RESET); }

  /** Dispara un pull sintético (solo modo simulación). */
  simPull() { return this.sendCommand(COMMANDS.SIM_PULL); }

  /** Activa/desactiva pulls automáticos (solo modo simulación). */
  setSimAuto(on) { return this.sendCommand(`${COMMANDS.SIM_AUTO} ${on ? 1 : 0}`); }

  // ---- interno ----

  _onGattDisconnected = () => {
    this._handleDisconnected();
  };

  _handleDisconnected() {
    const wasConnected = this._connected;
    this._teardown();
    if (wasConnected) this._emit(SenseEvent.STATUS, { connected: false });
  }

  _teardown() {
    if (this._forceChar && this._forceListener) {
      this._forceChar.removeEventListener('characteristicvaluechanged', this._forceListener);
    }
    if (this._ctrlChar && this._ctrlListener) {
      this._ctrlChar.removeEventListener('characteristicvaluechanged', this._ctrlListener);
    }
    this._forceChar = null;
    this._ctrlChar = null;
    this._server = null;
    this._device = null;
    this._forceListener = null;
    this._ctrlListener = null;
    this._connected = false;
  }

  _onForce(value) {
    let frame;
    try {
      frame = parseForceFrame(value);
    } catch (error) {
      this._emit(SenseEvent.ERROR, { error, fatal: false });
      return;
    }

    const gap = sequenceGap(this._lastSeq, frame.seq);
    if (gap > 0) this.metrics.addLostPackets(gap);
    this._lastSeq = frame.seq;

    for (const sample of frame.samples) {
      this._emit(SenseEvent.SAMPLE, { ts: sample.ts, kg: sample.kg, seq: frame.seq });
      const snapshot = this.metrics.addSample(sample.ts, sample.kg);
      if (snapshot.pullEnded) this._emit(SenseEvent.PULL_END, snapshot.pullEnded);
    }
    this._emit(SenseEvent.METRICS, this.metrics.get());
  }

  _onCtrl(value) {
    let text;
    try {
      text = decodeResponse(value);
    } catch (error) {
      this._emit(SenseEvent.ERROR, { error, fatal: false });
      return;
    }
    this._emit(SenseEvent.COMMAND, { text });
  }

  _emit(type, detail) {
    this.dispatchEvent(makeEvent(type, detail));
  }
}
