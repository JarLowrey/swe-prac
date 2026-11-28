// The recorder's tap on the microphone, an AudioWorklet module (recorder.js loads it): it hands
// the page the raw samples, mixed to mono, in blocks of 4096 (about a tenth of a second), so
// recordings can be transcribed as they're made.

class PcmTap extends AudioWorkletProcessor {
  constructor() {
    super();
    this.block = new Float32Array(4096);
    this.n = 0;
  }

  process([input]) {
    const channels = input ?? [];
    const frames = channels[0]?.length ?? 0;
    for (let i = 0; i < frames; i++) {
      let sum = 0;
      for (const channel of channels) sum += channel[i];
      this.block[this.n++] = sum / channels.length;
      if (this.n === this.block.length) {
        this.port.postMessage(this.block, [this.block.buffer]);
        this.block = new Float32Array(4096);
        this.n = 0;
      }
    }
    return true; // keep running while the recording does
  }
}

registerProcessor("pcm-tap", PcmTap);
