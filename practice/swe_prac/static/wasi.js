// A minimal WASI (preview 1) for running a compiled C++ program in a Web Worker: stdin from a
// buffer, stdout and stderr to callbacks, clocks and random numbers. No files: a program that
// opens one gets an error, as if it didn't exist.

const ESUCCESS = 0;
const EBADF = 8;
const ENOENT = 44;
const ENOSYS = 52;
const ESPIPE = 70;
const CHARACTER_DEVICE = 2;

/** Thrown by proc_exit: the program called exit() (or returned from main). */
export class WasiExit extends Error {
  constructor(code) {
    super(`exit(${code})`);
    this.code = code;
  }
}

/**
 * The wasi_snapshot_preview1 functions. `stdin` is the program's whole input (a Uint8Array, or
 * a function returning more bytes or null); stdout and stderr get each write's bytes.
 */
export function createWasi({ stdin = new Uint8Array(0), stdout = () => {}, stderr = () => {}, args = ["main"] } = {}) {
  let memory = null;
  const view = () => new DataView(memory.buffer);
  const bytes = () => new Uint8Array(memory.buffer);
  const encoder = new TextEncoder();
  const argBytes = args.map((a) => encoder.encode(`${a}\0`));
  let input = typeof stdin === "function" ? null : stdin;
  let inputPos = 0;

  const nextInput = () => {
    if (input && inputPos < input.length) return true;
    if (typeof stdin !== "function") return false;
    const more = stdin();
    if (!more || !more.length) return false;
    input = more;
    inputPos = 0;
    return true;
  };

  const fns = {
    args_sizes_get(argc, size) {
      view().setUint32(argc, argBytes.length, true);
      view().setUint32(size, argBytes.reduce((n, b) => n + b.length, 0), true);
      return ESUCCESS;
    },
    args_get(argv, buf) {
      let at = buf;
      argBytes.forEach((b, i) => {
        view().setUint32(argv + 4 * i, at, true);
        bytes().set(b, at);
        at += b.length;
      });
      return ESUCCESS;
    },
    environ_sizes_get(count, size) {
      view().setUint32(count, 0, true);
      view().setUint32(size, 0, true);
      return ESUCCESS;
    },
    environ_get() {
      return ESUCCESS;
    },
    clock_res_get(_id, out) {
      view().setBigUint64(out, 1000n, true);
      return ESUCCESS;
    },
    clock_time_get(id, _precision, out) {
      // 0 is the wall clock; the others (monotonic, CPU time) count from the page's start.
      const ns = id === 0 ? BigInt(Date.now()) * 1000000n : BigInt(Math.round(performance.now() * 1e6));
      view().setBigUint64(out, ns, true);
      return ESUCCESS;
    },
    fd_write(fd, iovs, count, written) {
      if (fd !== 1 && fd !== 2) return EBADF;
      const v = view();
      let total = 0;
      for (let i = 0; i < count; i++) {
        const ptr = v.getUint32(iovs + 8 * i, true);
        const len = v.getUint32(iovs + 8 * i + 4, true);
        if (!len) continue;
        const chunk = bytes().slice(ptr, ptr + len);
        (fd === 1 ? stdout : stderr)(chunk);
        total += len;
      }
      view().setUint32(written, total, true);
      return ESUCCESS;
    },
    fd_read(fd, iovs, count, read) {
      if (fd !== 0) return EBADF;
      const v = view();
      let total = 0;
      for (let i = 0; i < count; i++) {
        const ptr = v.getUint32(iovs + 8 * i, true);
        const len = v.getUint32(iovs + 8 * i + 4, true);
        if (!len || !nextInput()) break;
        const n = Math.min(len, input.length - inputPos);
        bytes().set(input.subarray(inputPos, inputPos + n), ptr);
        inputPos += n;
        total += n;
        if (n < len) break;
      }
      view().setUint32(read, total, true);
      return ESUCCESS;
    },
    fd_fdstat_get(fd, out) {
      if (fd > 2) return EBADF;
      const v = view();
      v.setUint8(out, CHARACTER_DEVICE); // line-buffered stdout, so output arrives as printed
      v.setUint16(out + 2, 0, true);
      v.setBigUint64(out + 8, 0xffffffffn, true);
      v.setBigUint64(out + 16, 0xffffffffn, true);
      return ESUCCESS;
    },
    fd_fdstat_set_flags() {
      return ESUCCESS;
    },
    fd_filestat_get(fd, out) {
      if (fd > 2) return EBADF;
      bytes().fill(0, out, out + 64);
      view().setUint8(out + 16, CHARACTER_DEVICE);
      return ESUCCESS;
    },
    fd_prestat_get() {
      return EBADF;
    },
    fd_prestat_dir_name() {
      return EBADF;
    },
    fd_close() {
      return ESUCCESS;
    },
    fd_seek(fd) {
      return fd <= 2 ? ESPIPE : EBADF;
    },
    fd_sync() {
      return ESUCCESS;
    },
    path_open() {
      return ENOENT;
    },
    path_filestat_get() {
      return ENOENT;
    },
    proc_exit(code) {
      throw new WasiExit(code);
    },
    random_get(buf, len) {
      for (let at = 0; at < len; at += 65536) {
        crypto.getRandomValues(bytes().subarray(buf + at, buf + Math.min(len, at + 65536)));
      }
      return ESUCCESS;
    },
    sched_yield() {
      return ESUCCESS;
    },
    poll_oneoff() {
      return ENOSYS;
    },
  };

  return {
    /** The import object for `module`; `extra` adds other import modules ({swe: {emit}}). */
    imports(module, extra = {}) {
      const out = { wasi_snapshot_preview1: {}, ...extra };
      for (const imp of WebAssembly.Module.imports(module)) {
        if (imp.kind !== "function") continue;
        if (imp.module === "wasi_snapshot_preview1") {
          out.wasi_snapshot_preview1[imp.name] = fns[imp.name] ?? (() => ENOSYS);
        } else if (!out[imp.module]?.[imp.name]) {
          out[imp.module] ??= {};
          out[imp.module][imp.name] = () => {
            throw new Error(`The program needs ${imp.module}.${imp.name}, which isn't available here.`);
          };
        }
      }
      return out;
    },
    /** Call once the module is instantiated: the program's memory. */
    setMemory(m) {
      memory = m;
    },
  };
}
