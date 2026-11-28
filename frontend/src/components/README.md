# Componentes

Piezas que se usan en más de una pantalla.

El desorden visual de la marca, como el papel rasgado, es solo para el contenido. Los menús, la búsqueda y el reproductor van rectos.

| Componente | Para qué sirve |
| --- | --- |
| [`AppShell`](AppShell.tsx) | Marco de la app: tres paneles y reproductor |
| [`Sidebar`](Sidebar.tsx) | Navegación lateral, que en teléfono se convierte en pestañas |
| [`SearchBox`](SearchBox.tsx) | Buscador de la parte superior |
| [`NoticesBell`](NoticesBell.tsx) | Campana de avisos |
| [`Icon`](Icon.tsx) | Íconos |
| [`Logo`](Logo.tsx) | El logo que se lee sobre el fondo del tema (claro u oscuro) |
| [`LogoAnimation`](LogoAnimation.tsx) | El logo animado a pantalla completa: `intro` (aparece el casete, giran los carretes y se dibuja el wordmark) y `enter` (el casete cruza hacia el reproductor). Se salta con un clic o una tecla |
| [`motion.ts`](motion.ts) | Duraciones de las animaciones del logo, `prefersReducedMotion()` y `useDone`, que avisa una sola vez al terminar (de inmediato si se pidió menos movimiento) |
| [`IntroGate`](IntroGate.tsx) | Muestra la apertura (`LogoAnimation` `intro`) sobre la app cada vez que se carga o recarga la página sin sesión (es decir, la del login) |
| [`Note`](Note.tsx) | Papel rasgado, con cinta adhesiva opcional |
| [`Cover`](Cover.tsx) | Portada. Si la pista no tiene, muestra un degradado propio |
| [`SongRow`](SongRow.tsx) | Fila de una canción |
| [`SongMenu`](SongMenu.tsx) | Menú `⋯` de una canción: reproducir siguiente y agregar a la cola |
| [`AddSong`](AddSong.tsx) | Agregar una canción a un casete o a una playlist |
| [`Attribution`](Attribution.tsx) | Crédito de cada pista: artista y origen (`vía Jamendo`, con enlace a la pista, o `vía MELOXO`). La licencia no se muestra aquí |
| [`FileDrop`](FileDrop.tsx) | Zona para soltar o elegir un archivo, con nombre, tamaño y duración. La usan las subidas del Compositor |
| [`ArtistLinks`](ArtistLinks.tsx) | Enlaces de un artista |
| [`Tape`](Tape.tsx) | Dibujo del casete |
| [`TapePile`](TapePile.tsx) | Pila de casetes, con los fijados al frente |
| [`PinButton`](PinButton.tsx), [`LibrarySortSelect`](LibrarySortSelect.tsx) | Fijar un elemento de la biblioteca y elegir cómo se ordena |
| [`libraryOrder.ts`](libraryOrder.ts), [`libraryPrefs.ts`](libraryPrefs.ts) | El orden (fijados primero, y por nombre o como llegan) y su almacén en `localStorage`, compartido por la barra lateral, la biblioteca y las pilas |
| [`TapeSide`](TapeSide.tsx) | Un lado del casete con sus pistas |
| [`DedicationEditor`](DedicationEditor.tsx) | Escribir una dedicatoria |
| [`InvitePanel`](InvitePanel.tsx) | Crear y compartir enlaces de invitación |
