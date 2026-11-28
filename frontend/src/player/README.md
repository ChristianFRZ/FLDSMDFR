# Reproductor

Usa un solo elemento `<audio>`, montado fuera del enrutador, para que la música no se corte al navegar.

| Archivo | Para qué sirve |
| --- | --- |
| [`PlayerProvider.tsx`](PlayerProvider.tsx) | Estado del reproductor y `usePlayer()` |
| [`queue.ts`](queue.ts) | Cola, modo aleatorio, repetición y edición (agregar, quitar y reordenar lo que sigue), con funciones puras |
| [`usePlaybackReporter.ts`](usePlaybackReporter.ts) | Cuenta el tiempo realmente escuchado y envía los eventos |
| [`recovery.ts`](recovery.ts) | Decide qué hacer cuando falla el audio |
| [`PlayerBar.tsx`](PlayerBar.tsx), [`NowPanel.tsx`](NowPanel.tsx), [`Reels.tsx`](Reels.tsx) | Controles, panel "Sonando" y carretes |
| [`useCompact.ts`](useCompact.ts) | Avisa si la pantalla es de teléfono, porque ahí el reproductor cambia de forma |
| [`format.ts`](format.ts) | Muestra los segundos como `3:07` |

## Teclado y controles del sistema

Con el foco fuera de un campo: Espacio pausa o reanuda, ← y → retroceden o adelantan 5 s y `M` silencia o devuelve el volumen. Las combinaciones con Alt, Ctrl o Cmd se dejan al navegador.

El reproductor también habla con Media Session: teclas multimedia y pantalla de bloqueo pueden pausar, saltar de pista, adelantar, retroceder o ir a un punto de la pista, y ven la posición y si suena o está en pausa.

## Cola y temporizador

La cola se edita desde el menú de cada canción (reproducir siguiente, agregar al final) y desde el botón Cola (subir, bajar, quitar). Con la cola vacía, agregar una pista la reproduce.

El temporizador de sueño pausa la música a los 15, 30 o 60 minutos, o al terminar la pista que suena. Un temporizador nuevo reemplaza al anterior.

## Eventos

A los 10 s de escucha real se envía `POST /api/playbacks`; adelantar la pista no cuenta. Al pausar y al terminar se envía el progreso.

Si el envío falla, el evento se guarda en `localStorage` y se reintenta con esperas cada vez más largas. El `playback_id` evita que un reenvío cuente doble. Un fallo aquí nunca interrumpe el audio.

## Errores de audio

El elemento `<audio>` no dice por qué falló. Por eso `recoverStream` pide un ticket nuevo y prueba a descargar un byte:

| Resultado | Acción |
| --- | --- |
| El byte llega | El ticket había vencido: retoma en la misma posición |
| `503` | Avisa que Jamendo no responde y pasa a la siguiente pista |
| Sin red | Se detiene, para no saltarse toda la cola |
| Otro error al probar el byte | Avisa que no pudo reproducir la pista y pasa a la siguiente |
| Error al pedir el ticket, con red | Avisa que la pista ya no está disponible y pasa a la siguiente |

## Crédito

[`Attribution`](../components/Attribution.tsx) muestra el artista y el origen de la pista: `vía Jamendo`, con enlace a su página, o `vía MELOXO`. La licencia no se muestra, pero se conserva en los datos de la pista.
