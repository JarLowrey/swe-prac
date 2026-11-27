// Adds one file to a zip in the browser, so the job-search.zip you download carries the profile you
// typed without it going anywhere. The entries already in the zip are copied byte for byte; the new
// one goes after them, stored uncompressed, and the central directory is rewritten to list it.

const CRC_TABLE = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

export function crc32(bytes) {
  let c = 0xffffffff;
  for (const b of bytes) c = CRC_TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

// MS-DOS date and time, which zip entries use.
function dosTime(d) {
  return {
    time: (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1),
    date: ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate(),
  };
}

// zip: the archive's bytes. Returns a new Uint8Array with `name` (a path inside the zip) holding `text`.
export function addFile(zip, name, text, when = new Date()) {
  const view = new DataView(zip.buffer, zip.byteOffset, zip.byteLength);
  let end = zip.length - 22; // the end-of-central-directory record, which may be followed by a comment
  while (end >= 0 && view.getUint32(end, true) !== 0x06054b50) end--;
  if (end < 0) throw new Error("The kit download isn't a zip file.");
  const count = view.getUint16(end + 10, true);
  const dirSize = view.getUint32(end + 12, true);
  const dirStart = view.getUint32(end + 16, true);
  if (count === 0xffff || dirStart === 0xffffffff) throw new Error("The kit download is too big to add to.");

  const enc = new TextEncoder();
  const path = enc.encode(name);
  const data = enc.encode(text);
  const crc = crc32(data);
  const { time, date } = dosTime(when);

  const local = new Uint8Array(30 + path.length + data.length);
  const lv = new DataView(local.buffer);
  lv.setUint32(0, 0x04034b50, true);
  lv.setUint16(4, 20, true); // version needed: 2.0
  lv.setUint16(6, 0x0800, true); // UTF-8 name
  lv.setUint16(8, 0, true); // stored
  lv.setUint16(10, time, true);
  lv.setUint16(12, date, true);
  lv.setUint32(14, crc, true);
  lv.setUint32(18, data.length, true);
  lv.setUint32(22, data.length, true);
  lv.setUint16(26, path.length, true);
  local.set(path, 30);
  local.set(data, 30 + path.length);

  const entry = new Uint8Array(46 + path.length);
  const cv = new DataView(entry.buffer);
  cv.setUint32(0, 0x02014b50, true);
  cv.setUint16(4, 0x0314, true); // made by: Unix, 2.0 (so the permissions below count)
  cv.setUint16(6, 20, true);
  cv.setUint16(8, 0x0800, true);
  cv.setUint16(10, 0, true);
  cv.setUint16(12, time, true);
  cv.setUint16(14, date, true);
  cv.setUint32(16, crc, true);
  cv.setUint32(20, data.length, true);
  cv.setUint32(24, data.length, true);
  cv.setUint16(28, path.length, true);
  cv.setUint32(38, (0o100644 << 16) >>> 0, true); // a regular file, rw-r--r--
  cv.setUint32(42, dirStart, true); // the new file starts where the old directory did
  entry.set(path, 46);

  const tail = new Uint8Array(22);
  const tv = new DataView(tail.buffer);
  tv.setUint32(0, 0x06054b50, true);
  tv.setUint16(8, count + 1, true);
  tv.setUint16(10, count + 1, true);
  tv.setUint32(12, dirSize + entry.length, true);
  tv.setUint32(16, dirStart + local.length, true);

  const out = new Uint8Array(dirStart + local.length + dirSize + entry.length + tail.length);
  out.set(zip.subarray(0, dirStart), 0);
  out.set(local, dirStart);
  out.set(zip.subarray(dirStart, dirStart + dirSize), dirStart + local.length);
  out.set(entry, dirStart + local.length + dirSize);
  out.set(tail, dirStart + local.length + dirSize + entry.length);
  return out;
}
