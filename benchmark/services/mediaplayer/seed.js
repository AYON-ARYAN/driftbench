const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

const dbPath = path.join(__dirname, 'db', 'mediaplayer.db');

const TRACKS = [
  [1, "So What", "Miles Davis", "Jazz", 562],
  [2, "Time", "Pink Floyd", "Rock", 421],
  [3, "Stairway to Heaven", "Led Zeppelin", "Rock", 482]
];

const PLAYLISTS = [
  [1, "My Favorites"]
];

const PLAYLIST_TRACKS = [
  [1, 1],
  [1, 2]
];

function seed(dbFile, callback) {
  const dbDir = path.dirname(dbFile);
  if (!fs.existsSync(dbDir)) {
    fs.mkdirSync(dbDir, { recursive: true });
  }
  if (fs.existsSync(dbFile)) {
    fs.unlinkSync(dbFile);
  }

  const db = new sqlite3.Database(dbFile, (err) => {
    if (err) return console.error(err.message);
    
    db.serialize(() => {
      db.run("CREATE TABLE tracks (id INTEGER PRIMARY KEY, title TEXT, artist TEXT, genre TEXT, duration INTEGER)");
      db.run("CREATE TABLE playlists (id INTEGER PRIMARY KEY, name TEXT)");
      db.run("CREATE TABLE playlist_tracks (playlist_id INTEGER, track_id INTEGER)");

      const stmtTrack = db.prepare("INSERT INTO tracks VALUES (?,?,?,?,?)");
      TRACKS.forEach(row => stmtTrack.run(row));
      stmtTrack.finalize();

      const stmtPlay = db.prepare("INSERT INTO playlists VALUES (?,?)");
      PLAYLISTS.forEach(row => stmtPlay.run(row));
      stmtPlay.finalize();

      const stmtPT = db.prepare("INSERT INTO playlist_tracks VALUES (?,?)");
      PLAYLIST_TRACKS.forEach(row => stmtPT.run(row));
      stmtPT.finalize();
    });

    db.close((err) => {
      if (callback) callback(err);
    });
  });
}

if (require.main === module) {
  seed(dbPath, (err) => {
    if (err) console.error("Seeding failed:", err);
    else console.log("Seeding completed successfully.");
  });
}

module.exports = { seed };
