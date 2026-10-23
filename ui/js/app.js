// FLDSMDFR Client Application - Fase 01 Monolito
// Interfaz de usuario interactiva para el sistema de streaming musical

const App = {
  state: {
    users: [],
    currentUserId: null,
    songs: [],
    playlists: [],
    selectedPlaylistId: null,
    currentSong: null,
    playbackSessionId: null,
    playbackReported: false,
    listenedSeconds: 0,
    lastPlayTime: 0,
    activeView: 'catalog'
  },

  elements: {
    userSelect: document.getElementById('userSelect'),
    songsTableBody: document.getElementById('songsTableBody'),
    searchInput: document.getElementById('searchInput'),
    playlistsContainer: document.getElementById('playlistsContainer'),
    playlistDetailCard: document.getElementById('playlistDetailCard'),
    metricsContainer: document.getElementById('metricsContainer'),
    audioElement: document.getElementById('audioElement'),
    btnPlayPause: document.getElementById('btnPlayPause'),
    seekSlider: document.getElementById('seekSlider'),
    currentTime: document.getElementById('currentTime'),
    totalDuration: document.getElementById('totalDuration'),
    playerTitle: document.getElementById('playerTitle'),
    playerArtist: document.getElementById('playerArtist'),
    telemetryBadge: document.getElementById('telemetryBadge'),
    telemetryText: document.getElementById('telemetryText'),
    btnRetryIdempotency: document.getElementById('btnRetryIdempotency'),
    toastContainer: document.getElementById('toastContainer'),
    modalPlaylist: document.getElementById('modalPlaylist'),
    modalAddToPlaylist: document.getElementById('modalAddToPlaylist'),
    modalNewSong: document.getElementById('modalNewSong'),
  },

  init() {
    this.bindEvents();
    this.loadInitialData();
  },

  bindEvents() {
    // Navegación entre vistas
    document.querySelectorAll('.nav-item[data-view]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-item[data-view]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.switchView(btn.dataset.view);
      });
    });

    // Selector de usuario
    this.elements.userSelect.addEventListener('change', (e) => {
      this.state.currentUserId = parseInt(e.target.value, 10);
      this.showToast(`Usuario activo: ${e.target.options[e.target.selectedIndex].text}`, 'info');
      this.loadPlaylists();
    });

    // Búsqueda en catálogo
    this.elements.searchInput.addEventListener('input', (e) => {
      this.filterSongs(e.target.value);
    });

    // Controles del reproductor
    this.elements.btnPlayPause.addEventListener('click', () => this.togglePlayPause());
    this.elements.seekSlider.addEventListener('input', (e) => this.onSeek(e));

    // Eventos de audio nativo
    this.elements.audioElement.addEventListener('timeupdate', () => this.onTimeUpdate());
    this.elements.audioElement.addEventListener('loadedmetadata', () => this.onMetadataLoaded());
    this.elements.audioElement.addEventListener('ended', () => this.onTrackEnded());

    // Botón de reintento de idempotencia
    this.elements.btnRetryIdempotency.addEventListener('click', () => this.testIdempotencyRetry());

    // Modales y botones de acción
    document.getElementById('btnNewPlaylistModal').addEventListener('click', () => {
      this.elements.modalPlaylist.classList.add('open');
    });

    document.getElementById('btnSavePlaylist').addEventListener('click', () => this.saveNewPlaylist());

    document.getElementById('btnNewSongModal').addEventListener('click', () => {
      this.elements.modalNewSong.classList.add('open');
    });

    document.getElementById('btnSaveNewSong').addEventListener('click', () => this.saveNewSong());

    document.getElementById('btnConfirmAddToPlaylist').addEventListener('click', () => this.confirmAddSongToPlaylist());

    document.getElementById('btnRefreshMetrics').addEventListener('click', () => this.loadMetrics());

    // Cerrar modales
    document.querySelectorAll('[data-close]').forEach(btn => {
      btn.addEventListener('click', () => {
        const modalId = btn.dataset.close;
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('open');
      });
    });
  },

  async loadInitialData() {
    try {
      await this.loadUsers();
      await this.loadSongs();
      await this.loadPlaylists();
      await this.loadMetrics();
    } catch (err) {
      console.error('Error al inicializar datos:', err);
      this.showToast('Error conectando con el servidor API.', 'error');
    }
  },

  switchView(viewName) {
    this.state.activeView = viewName;
    document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
    const target = document.getElementById(`view-${viewName}`);
    if (target) target.classList.add('active');

    if (viewName === 'metrics') {
      this.loadMetrics();
    } else if (viewName === 'playlists') {
      this.loadPlaylists();
    }
  },

  // ===================== USUARIOS =====================
  async loadUsers() {
    const res = await fetch('/api/users');
    if (!res.ok) throw new Error('Error al obtener usuarios');
    this.state.users = await res.json();
    this.elements.userSelect.innerHTML = '';
    this.state.users.forEach(u => {
      const opt = document.createElement('option');
      opt.value = u.id;
      opt.textContent = `${u.full_name} (@${u.username})`;
      this.elements.userSelect.appendChild(opt);
    });
    if (this.state.users.length > 0) {
      this.state.currentUserId = this.state.users[0].id;
    }
  },

  // ===================== CATÁLOGO =====================
  async loadSongs(query = '') {
    const url = query ? `/api/songs?q=${encodeURIComponent(query)}` : '/api/songs';
    const res = await fetch(url);
    if (!res.ok) throw new Error('Error al cargar canciones');
    this.state.songs = await res.json();
    this.renderSongsTable(this.state.songs);
  },

  filterSongs(q) {
    if (!q || q.trim() === '') {
      this.renderSongsTable(this.state.songs);
      return;
    }
    const term = q.toLowerCase();
    const filtered = this.state.songs.filter(s =>
      s.title.toLowerCase().includes(term) ||
      s.artist.toLowerCase().includes(term) ||
      s.album.toLowerCase().includes(term)
    );
    this.renderSongsTable(filtered);
  },

  renderSongsTable(songs) {
    this.elements.songsTableBody.innerHTML = '';
    if (songs.length === 0) {
      this.elements.songsTableBody.innerHTML = `
        <tr><td colspan="7" style="text-align:center; color: var(--text-muted); padding: 24px;">
          No se encontraron canciones disponibles.
        </td></tr>`;
      return;
    }

    songs.forEach((song, idx) => {
      const tr = document.createElement('tr');
      const isPlaying = this.state.currentSong && this.state.currentSong.id === song.id;

      tr.innerHTML = `
        <td style="color: var(--text-muted);">${idx + 1}</td>
        <td class="song-title-cell">${song.title} ${isPlaying ? '🔊' : ''}</td>
        <td>${song.artist}</td>
        <td style="color: var(--text-muted);">${song.album}</td>
        <td>${this.formatTime(song.duration_seconds)}</td>
        <td><span class="play-counter-badge" id="song-count-${song.id}">-</span></td>
        <td style="text-align: right;">
          <div class="song-actions">
            <button class="btn-sm btn-primary" onclick="App.playSong(${song.id})">▶ Reproducir</button>
            <button class="btn-sm btn-secondary" onclick="App.openAddToPlaylistModal(${song.id})">+ Playlist</button>
          </div>
        </td>
      `;
      this.elements.songsTableBody.appendChild(tr);

      // Cargar contador individual de métrica
      this.loadSongMetricBadge(song.id);
    });
  },

  async loadSongMetricBadge(songId) {
    try {
      const res = await fetch(`/api/metrics/songs/${songId}`);
      if (res.ok) {
        const data = await res.json();
        const badge = document.getElementById(`song-count-${songId}`);
        if (badge) badge.textContent = `${data.play_count} plays`;
      }
    } catch {
      // Ignorar fallback
    }
  },

  // ===================== STREAMING & REPRODUCTOR =====================
  playSong(songId) {
    const song = this.state.songs.find(s => s.id === songId);
    if (!song) return;

    this.state.currentSong = song;
    // Generar un nuevo UUID para la sesión de escucha (clave de idempotencia)
    this.state.playbackSessionId = (crypto && crypto.randomUUID) ? crypto.randomUUID() : `fldsmdfr-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    this.state.playbackReported = false;
    this.state.listenedSeconds = 0;
    this.state.lastPlayTime = 0;

    // Actualizar UI del reproductor
    this.elements.playerTitle.textContent = song.title;
    this.elements.playerArtist.textContent = `${song.artist} • ${song.album}`;
    this.elements.btnPlayPause.disabled = false;
    this.elements.seekSlider.disabled = false;
    this.elements.btnRetryIdempotency.style.display = 'none';

    this.updateTelemetryBadge('listening', 'Escuchando (0s / 10s para contar)');

    // El endpoint de streaming soporta cabeceras HTTP Range Requests
    const streamUrl = `/api/songs/${song.id}/stream`;
    this.elements.audioElement.src = streamUrl;
    this.elements.audioElement.play().catch(err => {
      console.warn('Reproducción diferida por política de autoplay del navegador:', err);
    });
    this.elements.btnPlayPause.textContent = '⏸';

    this.renderSongsTable(this.state.songs);
    this.showToast(`Streaming iniciado: ${song.title} (${song.mime_type})`, 'info');
  },

  togglePlayPause() {
    if (!this.state.currentSong) return;
    const audio = this.elements.audioElement;
    if (audio.paused) {
      audio.play();
      this.elements.btnPlayPause.textContent = '⏸';
    } else {
      audio.pause();
      this.elements.btnPlayPause.textContent = '▶';
    }
  },

  onMetadataLoaded() {
    const audio = this.elements.audioElement;
    this.elements.totalDuration.textContent = this.formatTime(audio.duration || 0);
    this.elements.seekSlider.max = Math.floor(audio.duration || 100);
  },

  onTimeUpdate() {
    const audio = this.elements.audioElement;
    const current = audio.currentTime;
    this.elements.currentTime.textContent = this.formatTime(current);
    this.elements.seekSlider.value = Math.floor(current);

    if (audio.paused) return;

    // Acumular tiempo de escucha efectiva
    this.state.listenedSeconds = current;

    // Verificar si se alcanzó el umbral del PRD (10 segundos) y aún no se reportó
    if (this.state.listenedSeconds >= 10.0 && !this.state.playbackReported) {
      this.reportPlaybackTelemetry();
    } else if (!this.state.playbackReported) {
      this.updateTelemetryBadge('listening', `Escuchando: ${current.toFixed(1)}s / 10.0s`);
    }
  },

  onSeek(e) {
    const targetSeconds = parseFloat(e.target.value);
    this.elements.audioElement.currentTime = targetSeconds;
    this.showToast(`Búsqueda instantánea con Range Request a ${this.formatTime(targetSeconds)}`, 'info');
  },

  onTrackEnded() {
    this.elements.btnPlayPause.textContent = '▶';
    this.updateTelemetryBadge('ended', 'Pista finalizada');
  },

  async reportPlaybackTelemetry() {
    if (this.state.playbackReported) return;
    this.state.playbackReported = true;

    const payload = {
      playback_id: this.state.playbackSessionId,
      song_id: this.state.currentSong.id,
      user_id: this.state.currentUserId,
      played_duration: parseFloat(this.elements.audioElement.currentTime.toFixed(2))
    };

    try {
      this.updateTelemetryBadge('sending', 'Enviando evento POST /api/playbacks...');
      const res = await fetch('/api/playbacks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (res.ok) {
        this.updateTelemetryBadge('sent', `✓ Contado (+1) | UUID: ${this.state.playbackSessionId.slice(0, 8)}...`);
        this.elements.btnRetryIdempotency.style.display = 'inline-block';
        this.showToast(`[TELEMETRÍA] Reproducción registrada: ${this.state.currentSong.title} (Total: ${data.current_play_count})`, 'success');
        this.loadSongMetricBadge(this.state.currentSong.id);
        if (this.state.activeView === 'metrics') {
          this.loadMetrics();
        }
      } else {
        this.updateTelemetryBadge('error', 'Error en telemetría');
        this.showToast(`Fallo de telemetría: ${data.detail || 'Error'}`, 'error');
      }
    } catch (err) {
      console.error('Error enviando evento de reproducción:', err);
      this.updateTelemetryBadge('error', 'Error de red');
    }
  },

  async testIdempotencyRetry() {
    if (!this.state.playbackSessionId || !this.state.currentSong) return;

    this.showToast(`Reenviando exactamente el mismo UUID: ${this.state.playbackSessionId.slice(0, 8)}...`, 'info');
    const payload = {
      playback_id: this.state.playbackSessionId,
      song_id: this.state.currentSong.id,
      user_id: this.state.currentUserId,
      played_duration: parseFloat(this.elements.audioElement.currentTime.toFixed(2))
    };

    try {
      const res = await fetch('/api/playbacks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        if (!data.counted) {
          this.showToast(`[IDEMPOTENCIA VERIFICADA] El servidor detectó duplicado: contador intacto (${data.current_play_count} plays).`, 'warning');
        } else {
          this.showToast(`Error inesperado: se volvió a contar.`, 'error');
        }
      }
    } catch (err) {
      this.showToast('Error al conectar para prueba de idempotencia', 'error');
    }
  },

  updateTelemetryBadge(status, text) {
    const badge = this.elements.telemetryBadge;
    badge.className = 'telemetry-badge';
    if (status === 'listening') badge.classList.add('active');
    if (status === 'sent') badge.classList.add('sent');
    this.elements.telemetryText.textContent = text;
  },

  // ===================== PLAYLISTS =====================
  async loadPlaylists() {
    if (!this.state.currentUserId) return;
    try {
      const res = await fetch(`/api/playlists?user_id=${this.state.currentUserId}`);
      if (!res.ok) throw new Error('Error al cargar playlists');
      this.state.playlists = await res.json();
      this.renderPlaylistsList(this.state.playlists);
    } catch (err) {
      console.error(err);
    }
  },

  renderPlaylistsList(playlists) {
    this.elements.playlistsContainer.innerHTML = '';
    if (playlists.length === 0) {
      this.elements.playlistsContainer.innerHTML = `
        <div style="color: var(--text-muted); font-size: 13px; padding: 12px;">
          No tienes playlists creadas. ¡Crea una con el botón de arriba!
        </div>`;
      this.elements.playlistDetailCard.innerHTML = '<div class="placeholder-msg">Sin playlists seleccionadas.</div>';
      return;
    }

    playlists.forEach(p => {
      const div = document.createElement('div');
      div.className = `playlist-card ${this.state.selectedPlaylistId === p.id ? 'active' : ''}`;
      div.innerHTML = `
        <h3>📁 ${p.name}</h3>
        <p>${p.description || 'Sin descripción'}</p>
      `;
      div.addEventListener('click', () => this.selectPlaylist(p.id));
      this.elements.playlistsContainer.appendChild(div);
    });

    if (!this.state.selectedPlaylistId && playlists.length > 0) {
      this.selectPlaylist(playlists[0].id);
    }
  },

  async selectPlaylist(playlistId) {
    this.state.selectedPlaylistId = playlistId;
    document.querySelectorAll('.playlist-card').forEach(c => c.classList.remove('active'));

    try {
      const startT = performance.now();
      const res = await fetch(`/api/playlists/${playlistId}`);
      const latency = (performance.now() - startT).toFixed(1);

      if (!res.ok) throw new Error('Error al consultar playlist');
      const data = await res.json();

      let songsHtml = '';
      if (!data.songs || data.songs.length === 0) {
        songsHtml = '<p style="color: var(--text-muted); margin-top: 15px;">Esta lista aún no contiene canciones. Agrégalas desde el catálogo.</p>';
      } else {
        songsHtml = `
          <table class="data-table" style="margin-top: 15px;">
            <thead>
              <tr>
                <th>Título</th>
                <th>Artista</th>
                <th>Duración</th>
                <th style="text-align: right;">Acción</th>
              </tr>
            </thead>
            <tbody>
              ${data.songs.map(s => `
                <tr>
                  <td class="song-title-cell">${s.title}</td>
                  <td>${s.artist}</td>
                  <td>${this.formatTime(s.duration_seconds)}</td>
                  <td style="text-align: right;">
                    <button class="btn-sm btn-primary" onclick="App.playSong(${s.id})">▶ Escuchar</button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      }

      this.elements.playlistDetailCard.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <h2>${data.name}</h2>
            <p style="color: var(--text-muted); margin-top: 4px;">${data.description || ''}</p>
          </div>
          <span style="font-size: 11px; color: var(--accent); background: var(--accent-subtle); padding: 4px 8px; border-radius: 4px;">
            ⚡ Latencia JSON: ${latency} ms (&lt; 200 ms)
          </span>
        </div>
        ${songsHtml}
      `;
    } catch (err) {
      console.error(err);
      this.showToast('Error al consultar detalles de playlist', 'error');
    }
  },

  async saveNewPlaylist() {
    const name = document.getElementById('playlistName').value.trim();
    const desc = document.getElementById('playlistDesc').value.trim();

    if (!name) {
      this.showToast('El nombre de la playlist es requerido.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/playlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: this.state.currentUserId,
          name: name,
          description: desc
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Error al crear');
      }

      const created = await res.json();
      this.showToast(`Playlist "${created.name}" creada exitosamente.`, 'success');
      this.elements.modalPlaylist.classList.remove('open');
      document.getElementById('playlistName').value = '';
      document.getElementById('playlistDesc').value = '';
      await this.loadPlaylists();
      this.selectPlaylist(created.id);
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  openAddToPlaylistModal(songId) {
    const song = this.state.songs.find(s => s.id === songId);
    if (!song) return;

    this.state.songToAdd = songId;
    document.getElementById('addToPlaylistSongTitle').textContent = `Canción: "${song.title}" de ${song.artist}`;

    const select = document.getElementById('selectPlaylistToAdd');
    select.innerHTML = '';
    if (this.state.playlists.length === 0) {
      select.innerHTML = '<option value="">No tienes playlists creadas</option>';
    } else {
      this.state.playlists.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        select.appendChild(opt);
      });
    }

    this.elements.modalAddToPlaylist.classList.add('open');
  },

  async confirmAddSongToPlaylist() {
    const playlistId = parseInt(document.getElementById('selectPlaylistToAdd').value, 10);
    if (!playlistId || !this.state.songToAdd) {
      this.showToast('Selecciona una playlist válida.', 'warning');
      return;
    }

    try {
      const res = await fetch(`/api/playlists/${playlistId}/songs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ song_id: this.state.songToAdd })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Error al agregar');
      }

      this.showToast('Canción agregada a la playlist.', 'success');
      this.elements.modalAddToPlaylist.classList.remove('open');
      if (this.state.selectedPlaylistId === playlistId) {
        this.selectPlaylist(playlistId);
      }
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  // ===================== REGISTRO DE CANCIONES =====================
  async saveNewSong() {
    const title = document.getElementById('newSongTitle').value.trim();
    const artist = document.getElementById('newSongArtist').value.trim();
    const album = document.getElementById('newSongAlbum').value.trim() || 'Single';
    const duration = parseInt(document.getElementById('newSongDuration').value, 10) || 20;
    const filePath = document.getElementById('newSongFile').value.trim();

    if (!title || !artist || !filePath) {
      this.showToast('Completa título, artista y ruta de archivo.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/songs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title, artist, album, duration_seconds: duration, file_path: filePath, mime_type: 'audio/wav'
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Error al registrar canción');
      }

      const created = await res.json();
      this.showToast(`Canción "${created.title}" registrada exitosamente.`, 'success');
      this.elements.modalNewSong.classList.remove('open');
      await this.loadSongs();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  // ===================== MÉTRICAS Y POPULARIDAD =====================
  async loadMetrics() {
    try {
      const res = await fetch('/api/metrics/top?limit=8');
      if (!res.ok) throw new Error('Error al obtener métricas');
      const metrics = await res.json();
      this.renderMetricsGrid(metrics);
    } catch (err) {
      console.error(err);
      this.showToast('Error al actualizar ranking de popularidad', 'error');
    }
  },

  renderMetricsGrid(metrics) {
    this.elements.metricsContainer.innerHTML = '';
    if (metrics.length === 0) {
      this.elements.metricsContainer.innerHTML = '<div class="placeholder-msg">Sin datos de reproducciones aún.</div>';
      return;
    }

    metrics.forEach((item, index) => {
      const card = document.createElement('div');
      card.className = 'metric-card';
      const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${index + 1}`;

      card.innerHTML = `
        <div class="metric-rank">${medal}</div>
        <h3>${item.title}</h3>
        <p class="artist">${item.artist} • ${item.album}</p>
        <div class="metric-stats">
          <span style="color: var(--text-muted);">Total escuchas:</span>
          <span class="play-counter-badge">${item.play_count} plays</span>
        </div>
        <div style="margin-top: 14px; text-align: right;">
          <button class="btn-sm btn-outline" onclick="App.playSong(${item.song_id})">▶ Escuchar</button>
        </div>
      `;
      this.elements.metricsContainer.appendChild(card);
    });
  },

  // ===================== UTILIDADES =====================
  formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  },

  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✓' : type === 'error' ? '✖' : type === 'warning' ? '⚠' : 'ℹ';
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    this.elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
};

window.addEventListener('DOMContentLoaded', () => {
  App.init();
});
