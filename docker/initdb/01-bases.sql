-- 02-separacion: una base por servicio (y su copia para pruebas) en la misma instancia.
-- Ningún servicio conoce la base de otro: cada uno recibe solo su URL.
CREATE DATABASE users_playlists OWNER fldsmdfr;
CREATE DATABASE users_playlists_test OWNER fldsmdfr;
CREATE DATABASE catalog OWNER fldsmdfr;
CREATE DATABASE catalog_test OWNER fldsmdfr;
CREATE DATABASE playback OWNER fldsmdfr;
CREATE DATABASE playback_test OWNER fldsmdfr;
