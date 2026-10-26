// Test-only guard: fail any Node network attempt during offline H-MEM checks.
const net = require('node:net');
const http = require('node:http');
const https = require('node:https');
const dns = require('node:dns');
const dgram = require('node:dgram');
function denied() { throw new Error('Node network access forbidden by H-MEM offline check'); }
net.Socket.prototype.connect = denied;
net.createConnection = denied;
http.request = denied;
https.request = denied;
dns.lookup = denied;
dgram.createSocket = denied;
globalThis.fetch = denied;
