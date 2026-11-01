<script setup lang="ts">
import { computed } from 'vue'
import ResumenMetricas from '../components/ResumenMetricas.vue'
import VentanaCarretes from '../components/VentanaCarretes.vue'
import { formatTime } from '../composables/formatTime'
import { bitrateKbps, formatoLegible, porcentajeDescargado, tamanoLegible } from '../composables/streaming'
import { usePlayer } from '../composables/usePlayer'
import { useSession } from '../composables/useSession'

// Panel técnico: cómo llega la canción por HTTP Range (DESIGN.md §8).
const { current, buffered, duration, currentTime, isPlaying } = usePlayer()
const { isAdmin } = useSession()

const segundos = computed(() => duration.value || current.value?.duration_seconds || 0)
const bitrate = computed(() => bitrateKbps(current.value?.size_bytes ?? 0, segundos.value))
const descargado = computed(() => porcentajeDescargado(buffered.value, segundos.value))
const fragmentos = computed(() =>
  buffered.value.map(([inicio, fin]) => ({
    left: segundos.value ? (inicio / segundos.value) * 100 : 0,
    width: segundos.value ? (Math.max(fin - inicio, 0) / segundos.value) * 100 : 0,
  })),
)
const posicion = computed(() =>
  segundos.value ? Math.min((currentTime.value / segundos.value) * 100, 100) : 0,
)
</script>

<template>
  <section class="streaming" aria-labelledby="titulo-streaming">
    <header>
      <p class="antetitulo">CÓMO LLEGA TU MÚSICA</p>
      <h1 id="titulo-streaming">Streaming</h1>
    </header>

    <p v-if="!current" class="texto-secundario">Pon una canción para ver cómo llega a tu casetera.</p>

    <template v-else>
      <div class="streaming__cabecera">
        <VentanaCarretes :girando="isPlaying" class="streaming__carretes" />
        <div>
          <p class="streaming__titulo">{{ current.title }}</p>
          <p class="texto-secundario">{{ current.artist }} · {{ formatTime(currentTime) }} de {{ formatTime(segundos) }}</p>
        </div>
      </div>

      <dl class="streaming__tarjetas">
        <div class="tarjeta"><dt>Formato</dt><dd>{{ formatoLegible(current.mime_type) }}</dd></div>
        <div class="tarjeta"><dt>Tamaño</dt><dd>{{ tamanoLegible(current.size_bytes ?? 0) }}</dd></div>
        <div class="tarjeta">
          <dt>Bitrate estimado</dt>
          <dd>{{ bitrate === null ? '—' : `${bitrate} kbps` }}</dd>
        </div>
        <div class="tarjeta"><dt>Descargado</dt><dd>{{ descargado }} %</dd></div>
        <div class="tarjeta"><dt>Fragmentos</dt><dd>{{ buffered.length }}</dd></div>
      </dl>

      <figure class="streaming__figura">
        <div
          class="streaming__barra"
          role="img"
          :aria-label="`${buffered.length} fragmentos descargados, ${descargado} % de la canción`"
        >
          <span
            v-for="(f, i) in fragmentos"
            :key="i"
            class="streaming__fragmento"
            :style="{ left: `${f.left}%`, width: `${f.width}%` }"
          />
          <span class="streaming__cabezal" :style="{ left: `${posicion}%` }" />
        </div>
        <figcaption class="texto-secundario">
          Cada bloque mostaza es un fragmento ya descargado; la línea clara es donde vas.
        </figcaption>
      </figure>
    </template>

    <section class="tarjeta streaming__explicacion" aria-labelledby="titulo-range">
      <h2 id="titulo-range" class="streaming__subtitulo">¿Por qué en fragmentos?</h2>
      <p>
        El navegador no baja la canción entera: pide trozos con la cabecera HTTP
        <code>Range: bytes=inicio-fin</code> y el servidor responde <code>206 Partial Content</code>.
        Así empieza a sonar enseguida y, si saltas a otro punto, solo pide el trozo que falta.
      </p>
    </section>

    <ResumenMetricas v-if="isAdmin" />
  </section>
</template>

<style scoped>
.streaming {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-5);
}

.streaming__cabecera {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-5);
}

.streaming__carretes {
  width: min(320px, 100%);
}

.streaming__titulo {
  font-family: var(--font-display);
  font-size: 24px;
}

.streaming__tarjetas {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-3);
  margin: 0;
}

.streaming__tarjetas dt {
  color: var(--ink-muted);
  font-size: 11px;
}

.streaming__tarjetas dd {
  margin: var(--space-1) 0 0;
  font-family: var(--font-display);
  font-size: 22px;
  font-variant-numeric: tabular-nums;
}

.streaming__figura {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.streaming__barra {
  position: relative;
  height: 18px;
  overflow: hidden;
  border-radius: var(--radius-s);
  background: var(--surface);
}

.streaming__fragmento {
  position: absolute;
  top: 0;
  bottom: 0;
  background: var(--accent);
}

.streaming__cabezal {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--focus);
}

.streaming__explicacion {
  display: grid;
  gap: var(--space-2);
}

.streaming__subtitulo {
  font-size: 20px;
}

.streaming__explicacion code {
  color: var(--ink-on-active);
}

@media (max-width: 700px) {
  .streaming {
    padding: var(--space-4);
  }
}
</style>
