const test = require('node:test');
const assert = require('node:assert');
const path = require('path');
const http = require('http');
const app = require('./app');
const { seed } = require('./seed');

const dbPath = path.join(__dirname, 'db', 'mediaplayer.db');

function bootServer(port, callback) {
  seed(dbPath, (err) => {
    if (err) return callback(err);
    const server = http.createServer(app);
    server.listen(port, () => {
      callback(null, server);
    });
  });
}

test('MediaPlayer baseline test suite', (t, done) => {
  const port = 51234;
  bootServer(port, (err, server) => {
    if (err) {
      assert.fail("Server boot failed: " + err.message);
      return done();
    }

    const base = `http://127.0.0.1:${port}`;

    // Helper to query local server
    function request(path, options = {}) {
      return new Promise((resolve, reject) => {
        const url = base + path;
        const opt = {
          method: options.method || 'GET',
          headers: options.headers || {}
        };
        const req = http.request(url, opt, (res) => {
          let body = '';
          res.setEncoding('utf-8');
          res.on('data', chunk => body += chunk);
          res.on('end', () => {
            resolve({
              statusCode: res.statusCode,
              headers: res.headers,
              body: body ? JSON.parse(body) : null
            });
          });
        });
        req.on('error', reject);
        if (options.body) {
          req.setHeader('Content-Type', 'application/json');
          req.write(JSON.stringify(options.body));
        }
        req.end();
      });
    }

    // Runs tests sequentially
    (async () => {
      try {
        // 1. Healthz
        const r1 = await request('/healthz');
        assert.strictEqual(r1.statusCode, 200);
        assert.strictEqual(r1.body.status, "ok");

        // 2. List tracks
        const r2 = await request('/tracks');
        assert.strictEqual(r2.statusCode, 200);
        assert.strictEqual(r2.body.length, 3);

        // 3. Get track by ID
        const r3 = await request('/tracks/1');
        assert.strictEqual(r3.statusCode, 200);
        assert.strictEqual(r3.body.title, "So What");

        // 4. Post track (success)
        const r4 = await request('/tracks', {
          method: 'POST',
          body: { title: "Comfortably Numb", artist: "Pink Floyd", genre: "Rock", duration: 382 }
        });
        assert.strictEqual(r4.statusCode, 201);
        assert.strictEqual(r4.body.id, 4);

        // 5. Post track (invalid extra property)
        const r5 = await request('/tracks', {
          method: 'POST',
          body: { title: "x", artist: "y", genre: "z", duration: 10, extra: "unsupported" }
        });
        assert.strictEqual(r5.statusCode, 400);

        // 6. Get missing playlist
        const r6 = await request('/playlists/999');
        assert.strictEqual(r6.statusCode, 404);

        console.log("All Express MediaPlayer baseline tests passed successfully!");
      } catch (ex) {
        assert.fail("Test failed with exception: " + ex.message);
      } finally {
        server.close(done);
      }
    })();
  });
});
