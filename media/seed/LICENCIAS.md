# Licencias de la música semilla

Solo se incluye música con licencia libre (dominio público o Creative Commons) que permita su redistribución.

## Cómo agregar una pista

1. Copia el archivo `.mp3`, `.ogg` o `.wav` (máximo 20 MB) en `media/seed/`.
2. Agrega una entrada en `songs` de `media/seed/seed.json`:

   ```json
   {"file": "nombre.mp3", "title": "Título", "artist": "Artista", "album": "Álbum"}
   ```

3. Si quieres que aparezca en el casete demo "No CopyRight Songs", agrega el nombre del archivo en `demo_playlist.files`.
4. Registra la fuente y la licencia en la tabla de abajo.

La semilla es idempotente: una canción con el mismo título y artista no se vuelve a importar.

| Archivo | Título | Artista | Fuente (URL) | Licencia |
| --- | --- | --- | --- | --- |
