// Chalkin Sense - SDK JS - capa de métricas
// Licencia: GPL-3.0
//
// Cálculo puro de métricas a partir de muestras {ts, kg}. Sin DOM ni BLE.
// Reproduce las reglas del cliente de prueba original (app/index.html):
//   - umbral de pull: 2.0 kg
//   - umbral de suelta: 1.0 kg
//   - ventana deslizante: 6 s
//   - RFD medido en los primeros 200 ms del pull
// No asume una tasa de muestreo fija: usa el timestamp de cada muestra.

/** Fuerza (kg) a partir de la cual empieza a contar un pull. */
export const PULL_THRESHOLD_KG = 2.0;
/** Fuerza (kg) por debajo de la cual se considera que el pull ha terminado. */
export const RELEASE_THRESHOLD_KG = 1.0;
/** Ventana deslizante de la gráfica y del pico, en milisegundos. */
export const WINDOW_MS = 6000;
/** Ventana de cálculo del RFD (rate of force development), en milisegundos. */
export const RFD_WINDOW_MS = 200;

/**
 * Acumulador de métricas. Alimentar con `addSample(tsMs, kg)` según llegan
 * las muestras; `addSample` devuelve una foto (`snapshot`) del estado.
 */
export class Metrics {
  constructor({
    pullThresholdKg = PULL_THRESHOLD_KG,
    releaseThresholdKg = RELEASE_THRESHOLD_KG,
    windowMs = WINDOW_MS,
    rfdWindowMs = RFD_WINDOW_MS,
  } = {}) {
    this.pullThresholdKg = pullThresholdKg;
    this.releaseThresholdKg = releaseThresholdKg;
    this.windowMs = windowMs;
    this.rfdWindowMs = rfdWindowMs;
    this.reset();
  }

  /** Reinicia todo el estado (nueva sesión). */
  reset() {
    this._samples = [];
    this._baseTs = null;
    this._lastTs = null;
    this._lostPackets = 0;

    this._active = false;
    this._pullStart = null;
    this._pullLastKg = null;
    this._pullLastT = null;
    this._pullRfd = 0;
    this._pullPeak = 0;
    this._tut = 0;
    this._rfdMax = 0;
  }

  /** Suma frames perdidos (detección por `seq` en el cliente). */
  addLostPackets(n) {
    if (Number.isFinite(n) && n > 0) this._lostPackets += n;
  }

  /**
   * Añade una muestra.
   * @param {number} tsMs timestamp del dispositivo en ms
   * @param {number} kg fuerza en kg
   * @returns {object} snapshot de métricas (incluye `pullEnded` si acaba de soltar)
   */
  addSample(tsMs, kg) {
    // Primera muestra de la sesión/época.
    if (this._baseTs === null) {
      this._baseTs = tsMs;
      this._lastTs = tsMs;
    }

    // El timestamp del dispositivo es monotónico: si retrocede, empezamos una
    // época nueva (descarta base) y no actualizamos métricas de pull con esta.
    if (tsMs < this._lastTs) {
      this._samples = [];
      this._baseTs = tsMs;
      this._lastTs = tsMs;
      this._samples.push({ t: 0, kg, ts: tsMs });
      return this._snapshot(null);
    }

    const t = tsMs - this._baseTs;
    this._samples.push({ t, kg, ts: tsMs });
    this._lastTs = tsMs;

    // Ventana deslizante.
    const lastT = this._samples[this._samples.length - 1].t;
    if (lastT > this.windowMs) {
      const cutoff = lastT - this.windowMs;
      while (this._samples.length && this._samples[0].t < cutoff) this._samples.shift();
    }

    let pullEnded = null;

    if (kg > this.pullThresholdKg) {
      if (!this._active) {
        this._active = true;
        this._pullStart = t;
        this._pullRfd = 0;
        this._pullPeak = kg;
        this._pullLastKg = kg;
        this._pullLastT = t;
      } else {
        const dt = (t - this._pullLastT) / 1000;
        if (t - this._pullStart <= this.rfdWindowMs && dt > 0) {
          const slope = (kg - this._pullLastKg) / dt;
          if (slope > this._pullRfd) this._pullRfd = slope;
        }
        this._tut = (t - this._pullStart) / 1000;
        this._pullLastKg = kg;
        this._pullLastT = t;
        if (kg > this._pullPeak) this._pullPeak = kg;
      }
    } else if (this._active && kg < this.releaseThresholdKg) {
      pullEnded = {
        peakKg: this._pullPeak,
        rfdKgS: this._pullRfd,
        tutS: this._tut,
        durationS: (t - this._pullStart) / 1000,
      };
      this._active = false;
      this._pullStart = null;
      this._pullLastKg = null;
      this._pullLastT = null;
      this._pullRfd = 0;
      this._pullPeak = 0;
      this._tut = 0;
    }

    if (this._pullRfd > this._rfdMax) this._rfdMax = this._pullRfd;

    return this._snapshot(pullEnded);
  }

  /** Foto actual de las métricas. */
  get() {
    return this._snapshot(null);
  }

  /** Muestras de la ventana actual: [{t, kg, ts}]. */
  get samples() {
    return this._samples;
  }

  _snapshot(pullEnded) {
    const samples = this._samples;
    let peak = 0;
    let sum = 0;
    for (const s of samples) {
      if (s.kg > peak) peak = s.kg;
      sum += s.kg;
    }
    const n = samples.length;
    const durationS = n ? (samples[n - 1].t - samples[0].t) / 1000 : 0;
    return {
      active: this._active,
      peakKg: peak,
      meanKg: n ? sum / n : 0,
      rfdKgS: this._active ? this._pullRfd : this._rfdMax,
      rfdMaxKgS: this._rfdMax,
      tutS: this._tut,
      durationS,
      // Tasa efectiva de muestreo medida en la ventana (Hz). No se asume fija.
      rateHz: durationS > 0 ? (n - 1) / durationS : 0,
      sampleCount: n,
      lostPackets: this._lostPackets,
      pullEnded: pullEnded || null,
    };
  }
}
