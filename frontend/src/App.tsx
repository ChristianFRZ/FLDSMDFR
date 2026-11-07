import { Route, Routes } from "react-router-dom";
import { RequireAuth } from "./auth/RequireAuth";
import { RequireRole } from "./auth/RequireRole";
import { AddSongProvider } from "./components/AddSong";
import { AppShell } from "./components/AppShell";
import { NoticesBell } from "./components/NoticesBell";
import { SearchBox } from "./components/SearchBox";
import { Sidebar } from "./components/Sidebar";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { Audit } from "./pages/admin/Audit";
import { Catalog } from "./pages/admin/Catalog";
import { Dashboard } from "./pages/admin/Dashboard";
import { Health } from "./pages/admin/Health";
import { Requests } from "./pages/admin/Requests";
import { Users } from "./pages/admin/Users";
import { Artist } from "./pages/Artist";
import { Albums } from "./pages/composer/Albums";
import { ComposerProfile } from "./pages/composer/Profile";
import { ComposerStats } from "./pages/composer/Stats";
import { TrackEdit } from "./pages/composer/TrackEdit";
import { TrackForm } from "./pages/composer/TrackForm";
import { Tracks } from "./pages/composer/Tracks";
import { Stats } from "./pages/Stats";
import { Favorites } from "./pages/Favorites";
import { History } from "./pages/History";
import { Home } from "./pages/Home";
import { Library } from "./pages/Library";
import { Login } from "./pages/Login";
import { NotFound } from "./pages/NotFound";
import { Playlist } from "./pages/Playlist";
import { Profile } from "./pages/Profile";
import { Register } from "./pages/Register";
import { Search } from "./pages/Search";
import { TapeCreate } from "./pages/TapeCreate";
import { TapeDetail } from "./pages/TapeDetail";
import { TapeInvite } from "./pages/TapeInvite";
import { NowPanel } from "./player/NowPanel";
import { PlayerBar } from "./player/PlayerBar";

function Shell() {
  return (
    <AddSongProvider>
      <AppShell
        library={<Sidebar />}
        nowPlaying={<NowPanel />}
        player={<PlayerBar />}
        topActions={<><SearchBox /><NoticesBell /></>}
      />
    </AddSongProvider>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<RequireAuth />}>
        <Route element={<Shell />}>
          <Route index element={<Home />} />
          <Route path="search" element={<Search />} />
          <Route path="library" element={<Library />} />
          <Route path="favorites" element={<Favorites />} />
          <Route path="history" element={<History />} />
          <Route path="profile" element={<Profile />} />
          <Route path="playlists/:id" element={<Playlist />} />
          <Route path="artists/:id" element={<Artist />} />
          <Route path="tapes/new" element={<TapeCreate />} />
          <Route path="tapes/:id" element={<TapeDetail />} />
          <Route path="invite/:token" element={<TapeInvite />} />
          <Route element={<RequireRole roles={["composer"]} />}>
            <Route path="composer" element={<Tracks />} />
            <Route path="composer/new" element={<TrackForm />} />
            <Route path="composer/tracks/:id" element={<TrackEdit />} />
            <Route path="composer/albums" element={<Albums />} />
            <Route path="composer/profile" element={<ComposerProfile />} />
            <Route path="composer/stats" element={<ComposerStats />} />
          </Route>
          <Route element={<RequireRole roles={["admin"]} />}>
            <Route path="admin" element={<AdminLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="users" element={<Users />} />
              <Route path="requests" element={<Requests />} />
              <Route path="catalog" element={<Catalog />} />
              <Route path="audit" element={<Audit />} />
              <Route path="health" element={<Health />} />
            </Route>
          </Route>
          <Route path="stats" element={<Stats />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
}
