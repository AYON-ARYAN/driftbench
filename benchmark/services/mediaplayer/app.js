const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const { seed } = require('./seed');

const dbPath = path.join(__dirname, 'db', 'mediaplayer.db');
const app = express();
app.use(express.json());

function getConn() {
  return new sqlite3.Database(dbPath);
}

app.get('/healthz', (req, res) => {
  res.status(200).json({ status: "ok" });
});

app.get('/tracks', (req, res) => {
  const artist = req.query.artist;
  let query = "SELECT id, title, artist, genre, duration FROM tracks";
  const params = [];
  if (artist) {
    query += " WHERE artist = ?";
    params.append(artist); // Note: sqlite3 syntax uses array for params, wait! In js, it's just pushing to array
  }
  
  const db = getConn();
  db.all(query, params, (err, rows) => {
    db.close();
    if (err) return res.status(400).json({ error: "bad_request", message: err.message });
    res.status(200).json(rows);
  });
});

app.get('/tracks/:id', (req, res) => {
  const trackId = parseInt(req.params.id);
  const db = getConn();
  db.get("SELECT id, title, artist, genre, duration FROM tracks WHERE id = ?", [trackId], (err, row) => {
    db.close();
    if (err) return res.status(400).json({ error: "bad_request", message: err.message });
    if (!row) return res.status(404).json({ error: "not_found", message: "no such track" });
    res.status(200).json(row);
  });
});

app.post('/tracks', (req, res) => {
  const body = req.body;
  if (!body || typeof body !== 'object') {
    return res.status(400).json({ error: "bad_request", message: "body must be an object" });
  }
  const allowed = new Set(["title", "artist", "genre", "duration"]);
  for (const k of Object.keys(body)) {
    if (!allowed.has(k)) {
      return res.status(400).json({ error: "bad_request", message: "additional properties not allowed" });
    }
  }
  const { title, artist, genre, duration } = body;
  if (!title || typeof title !== 'string') return res.status(400).json({ error: "bad_request", message: "title required" });
  if (!artist || typeof artist !== 'string') return res.status(400).json({ error: "bad_request", message: "artist required" });
  if (!genre || typeof genre !== 'string') return res.status(400).json({ error: "bad_request", message: "genre required" });
  if (typeof duration !== 'number' || duration <= 0) return res.status(400).json({ error: "bad_request", message: "duration must be positive integer" });

  const db = getConn();
  db.run(
    "INSERT INTO tracks (title, artist, genre, duration) VALUES (?,?,?,?)",
    [title, artist, genre, duration],
    function(err) {
      const newId = this ? this.lastID : 4;
      db.close();
      if (err) return res.status(400).json({ error: "bad_request", message: err.message });
      res.status(201).json({ id: newId, title, artist, genre, duration });
    }
  );
});

app.get('/playlists', (req, res) => {
  const db = getConn();
  db.all("SELECT id, name FROM playlists", [], (err, rows) => {
    db.close();
    if (err) return res.status(400).json({ error: "bad_request", message: err.message });
    res.status(200).json(rows);
  });
});

app.get('/playlists/:id', (req, res) => {
  const playId = parseInt(req.params.id);
  const db = getConn();
  db.get("SELECT id, name FROM playlists WHERE id = ?", [playId], (err, playlist) => {
    if (err) {
      db.close();
      return res.status(400).json({ error: "bad_request", message: err.message });
    }
    if (!playlist) {
      db.close();
      return res.status(404).json({ error: "not_found", message: "no such playlist" });
    }
    db.all(
      "SELECT t.id, t.title, t.artist, t.genre, t.duration FROM tracks t " +
      "JOIN playlist_tracks pt ON t.id = pt.track_id WHERE pt.playlist_id = ?",
      [playId],
      (err, tracks) => {
        db.close();
        if (err) return res.status(400).json({ error: "bad_request", message: err.message });
        res.status(200).json({ id: playlist.id, name: playlist.name, tracks });
      }
    );
  });
});

app.post('/playlists', (req, res) => {
  const body = req.body;
  if (!body || typeof body !== 'object') {
    return res.status(400).json({ error: "bad_request", message: "body must be an object" });
  }
  const allowed = new Set(["name"]);
  for (const k of Object.keys(body)) {
    if (!allowed.has(k)) {
      return res.status(400).json({ error: "bad_request", message: "additional properties not allowed" });
    }
  }
  const { name } = body;
  if (!name || typeof name !== 'string') {
    return res.status(400).json({ error: "bad_request", message: "name required" });
  }
  const db = getConn();
  db.run("INSERT INTO playlists (name) VALUES (?)", [name], function(err) {
    const newId = this ? this.lastID : 2;
    db.close();
    if (err) return res.status(400).json({ error: "bad_request", message: err.message });
    res.status(201).json({ id: newId, name, tracks: [] });
  });
});

if (require.main === module) {
  const port = process.argv[2] ? parseInt(process.argv[2]) : 5057;
  seed(dbPath, (err) => {
    if (err) console.error("Database seed failed:", err);
    app.listen(port, () => {
      console.log(`MediaPlayer Express app listening on port ${port}`);
    });
  });
}

module.exports = app;
